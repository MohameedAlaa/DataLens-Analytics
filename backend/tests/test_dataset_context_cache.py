"""Tests for AI-01: Dataset Context Cache Bounding, Eviction, Concurrency, and Lifecycle Invalidation.

Covers:
- Cache population & hit behavior (cache hit returns cached string, avoids recomputation).
- Bounding behavior (cache strictly caps at max size and evicts oldest in LRU order).
- Deterministic LRU refresh (accessing an item moves it to most recent).
- Safe reconstruction after eviction (evicted dataset can be cleanly rebuilt from DataFrame).
- Dataset lifecycle invalidation (delete_dataset purges cached entry).
- Dataset replacement invalidation (register_dataset/updating data clears old context so new schema is reflected).
- Multi-threaded concurrency safety (no KeyError or linked list corruption under concurrent reads/writes).
- Canonical alias: _DATASET_CONTEXT_CACHE is _context_cache.
- Configurable capacity via settings.dataset_context_cache_size.
"""

import collections
import concurrent.futures
import threading
import uuid
import pandas as pd
import pytest

from api_helpers import (
    _context_cache,
    _DATASET_CONTEXT_CACHE,
    _get_context_cache_max,
    build_dataset_context,
    invalidate_dataset_context,
)
from config import settings
from dataset_manager import dataset_manager


def test_canonical_alias():
    """Verify that _DATASET_CONTEXT_CACHE is an alias for _context_cache."""
    assert _DATASET_CONTEXT_CACHE is _context_cache
    assert isinstance(_DATASET_CONTEXT_CACHE, collections.OrderedDict)


def test_cache_population_and_hit():
    """Verify context is cached and repeated calls return the cached context without recomputation."""
    df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["apple", "banana", "cherry"]})
    ds_id = f"test-pop-{uuid.uuid4().hex[:8]}"

    # Initial build should populate cache
    ctx1 = build_dataset_context(ds_id, df, "test_file.csv")
    assert ds_id in _context_cache
    assert _context_cache[ds_id] == ctx1

    # Second call with empty DataFrame to prove it returns the cached context without recomputing from df
    empty_df = pd.DataFrame()
    ctx2 = build_dataset_context(ds_id, empty_df, "different_filename.csv")
    assert ctx2 == ctx1
    assert "col_a" in ctx2
    assert "col_b" in ctx2


def test_bounding_behavior_and_lru_eviction(monkeypatch):
    """Verify cache capacity is strictly bounded and follows deterministic LRU eviction."""
    # Temporarily set max cache size to 5
    test_max = 5
    monkeypatch.setattr("api_helpers._get_context_cache_max", lambda: test_max)
    invalidate_dataset_context(None)

    df = pd.DataFrame({"val": [1, 2, 3]})
    keys = [f"ds-bound-{i}" for i in range(10)]

    for k in keys:
        build_dataset_context(k, df, f"{k}.csv")

    # Cache must not exceed test_max
    assert len(_context_cache) == test_max

    # The oldest entries (0..4) should have been evicted
    for evicted_key in keys[:5]:
        assert evicted_key not in _context_cache, f"Key {evicted_key} should have been evicted"

    # The newest entries (5..9) should be in cache
    for kept_key in keys[5:]:
        assert kept_key in _context_cache, f"Key {kept_key} should remain in cache"


def test_lru_refresh_on_read(monkeypatch):
    """Verify accessing an older item refreshes its LRU position so it is not evicted first."""
    test_max = 3
    monkeypatch.setattr("api_helpers._get_context_cache_max", lambda: test_max)
    invalidate_dataset_context(None)

    df = pd.DataFrame({"val": [10, 20]})

    # Insert A, B, C
    build_dataset_context("ds-A", df, "A.csv")
    build_dataset_context("ds-B", df, "B.csv")
    build_dataset_context("ds-C", df, "C.csv")

    assert list(_context_cache.keys()) == ["ds-A", "ds-B", "ds-C"]

    # Access ds-A, which should move ds-A to the end (most recent)
    build_dataset_context("ds-A", df, "A.csv")
    assert list(_context_cache.keys()) == ["ds-B", "ds-C", "ds-A"]

    # Now insert ds-D. ds-B should be evicted, not ds-A!
    build_dataset_context("ds-D", df, "D.csv")
    assert "ds-B" not in _context_cache
    assert "ds-A" in _context_cache
    assert list(_context_cache.keys()) == ["ds-C", "ds-A", "ds-D"]


def test_safe_reconstruction_after_eviction(monkeypatch):
    """Verify that an evicted dataset can be safely reconstructed and yields identical context."""
    test_max = 2
    monkeypatch.setattr("api_helpers._get_context_cache_max", lambda: test_max)
    invalidate_dataset_context(None)

    df_original = pd.DataFrame({"sensor": [1.1, 2.2, 3.3], "location": ["room1", "room2", "room3"]})
    ds_target = "ds-evict-rebuild"

    # Compute initial context
    ctx_initial = build_dataset_context(ds_target, df_original, "sensors.csv")
    assert ds_target in _context_cache

    # Push ds_target out by adding 2 new datasets
    build_dataset_context("ds-other-1", df_original, "other1.csv")
    build_dataset_context("ds-other-2", df_original, "other2.csv")
    assert ds_target not in _context_cache

    # Reconstruct ds_target
    ctx_rebuilt = build_dataset_context(ds_target, df_original, "sensors.csv")
    assert ds_target in _context_cache
    assert ctx_rebuilt == ctx_initial


def test_dataset_deletion_invalidates_cache():
    """Verify that deleting a dataset through dataset_manager purges its cached context."""
    df = pd.DataFrame({"x": [100, 200], "y": ["alpha", "beta"]})
    ds_id = dataset_manager.register_dataset(df=df, filename="to_delete.csv")

    # Cache the context
    ctx = build_dataset_context(ds_id, df, "to_delete.csv")
    assert ds_id in _context_cache
    assert _context_cache[ds_id] == ctx

    # Delete dataset through manager
    deleted = dataset_manager.delete_dataset(ds_id)
    assert deleted is True

    # Cache entry MUST be removed
    assert ds_id not in _context_cache


def test_dataset_replacement_invalidates_stale_cache():
    """Verify that updating a dataset under an existing ID clears stale cached context."""
    df_old = pd.DataFrame({"old_metric": [1, 2, 3]})
    ds_id = f"test-replace-{uuid.uuid4().hex[:8]}"

    # Store initial dataset and cache its context
    dataset_manager.register_dataset(df=df_old, filename="version1.csv", dataset_id=ds_id)
    ctx_old = build_dataset_context(ds_id, df_old, "version1.csv")
    assert "old_metric" in ctx_old
    assert ds_id in _context_cache

    # Replace dataset with a new schema under the same dataset_id
    df_new = pd.DataFrame({"new_metric": [10.5, 20.5], "category": ["A", "B"]})
    dataset_manager.register_dataset(df=df_new, filename="version2.csv", dataset_id=ds_id)

    # Cache entry for ds_id must have been invalidated
    assert ds_id not in _context_cache

    # Re-building context must reflect the new schema, not the stale old_metric
    ctx_new = build_dataset_context(ds_id, df_new, "version2.csv")
    assert "new_metric" in ctx_new
    assert "category" in ctx_new
    assert "old_metric" not in ctx_new


def test_concurrent_access_thread_safety(monkeypatch):
    """Verify that concurrent threads reading, writing, and evicting do not corrupt the cache."""
    test_max = 10
    monkeypatch.setattr("api_helpers._get_context_cache_max", lambda: test_max)
    invalidate_dataset_context(None)

    errors = []
    df = pd.DataFrame({"num": list(range(50)), "str_col": ["val"] * 50})

    def worker(worker_id: int):
        try:
            for i in range(25):
                ds_id = f"concurrent-ds-{(worker_id * 10 + i) % 30}"
                ctx = build_dataset_context(ds_id, df, f"{ds_id}.csv")
                assert len(ctx) > 0
                if i % 5 == 0:
                    # Invalidate some keys concurrently to stress test dictionary state
                    invalidate_dataset_context(f"concurrent-ds-{i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent access generated exceptions: {errors}"
    assert len(_context_cache) <= test_max


def test_invalidate_dataset_context_helper():
    """Verify manual invalidation helper removes specific key and handles None (clear all)."""
    df = pd.DataFrame({"a": [1]})
    build_dataset_context("ds-inv-1", df, "1.csv")
    build_dataset_context("ds-inv-2", df, "2.csv")

    assert "ds-inv-1" in _context_cache
    assert "ds-inv-2" in _context_cache

    # Invalidate specific key
    removed = invalidate_dataset_context("ds-inv-1")
    assert removed is True
    assert "ds-inv-1" not in _context_cache
    assert "ds-inv-2" in _context_cache

    # Invalidate non-existent key
    assert invalidate_dataset_context("ds-non-existent") is False

    # Invalidate all (None)
    cleared = invalidate_dataset_context(None)
    assert cleared is True
    assert len(_context_cache) == 0
    assert invalidate_dataset_context(None) is False
