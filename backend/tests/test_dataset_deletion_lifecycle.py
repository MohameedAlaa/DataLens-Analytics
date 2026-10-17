"""Regression tests for ARCH-02: Dataset deletion and vector lifecycle.

Verifies:
1. Deleting a dataset removes stored data and metadata.
2. Deleting a dataset removes its vector embeddings from ChromaDB.
3. Deleting one dataset leaves other datasets' vectors accessible (isolation).
4. Repeated deletion is handled consistently and idempotently.
5. Missing dataset IDs produce predictable outcomes (returns False, no error).
6. Re-registering a dataset ID does not expose old vectors or stale context.
7. Dataset context cache is invalidated upon deletion.
8. Partial vector cleanup failures are handled and logged safely without crashing callers.
9. Background ingestion race: deleting a dataset mid-flight prevents orphaned vector creation.
10. Security gate: No unauthenticated public HTTP DELETE endpoint is exposed.
"""

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import app
from dataset_manager import DatasetManager, DiskStorageEngine, InMemoryStorageEngine
from services.ai.rag.chunker import Chunk
from services.ai.rag.ingestion_pipeline import IngestionPipeline
from services.data.vector_store import ChromaVectorStore


@pytest.fixture
def isolated_vector_store(tmp_path):
    """Provides a fresh, isolated ChromaVectorStore instance for testing."""
    persist_dir = str(tmp_path / "chroma_lifecycle")
    store = ChromaVectorStore(
        collection_name=f"test_lifecycle_{uuid.uuid4().hex[:8]}",
        persist_directory=persist_dir,
    )
    return store


@pytest.fixture
def disk_dataset_manager(tmp_path, isolated_vector_store):
    """Provides a DatasetManager backed by DiskStorageEngine with isolated vector store."""
    engine = DiskStorageEngine(storage_dir=str(tmp_path / "datasets"))
    manager = DatasetManager(engine=engine, vector_store=isolated_vector_store)
    return manager


@pytest.fixture
def memory_dataset_manager(isolated_vector_store):
    """Provides a DatasetManager backed by InMemoryStorageEngine with isolated vector store."""
    engine = InMemoryStorageEngine()
    manager = DatasetManager(engine=engine, vector_store=isolated_vector_store)
    return manager


def test_delete_dataset_removes_data_and_metadata(disk_dataset_manager, tmp_path):
    """Scenario 1: Deleting a dataset removes its stored Parquet data and metadata."""
    df = pd.DataFrame({"metric": [10, 20, 30], "label": ["a", "b", "c"]})
    ds_id = f"test-del-{uuid.uuid4().hex[:8]}"

    disk_dataset_manager.register_dataset(df=df, filename="sales.csv", dataset_id=ds_id)

    assert disk_dataset_manager.exists(ds_id) is True
    assert disk_dataset_manager.get_dataset(ds_id) is not None
    assert disk_dataset_manager.get_metadata(ds_id) is not None

    # Disk files must exist
    storage_dir = tmp_path / "datasets"
    assert (storage_dir / f"{ds_id}.parquet").is_file()
    assert (storage_dir / f"{ds_id}.meta.json").is_file()

    # Perform deletion
    deleted = disk_dataset_manager.delete_dataset(ds_id)
    assert deleted is True

    # Stored data, metadata, and disk files must be purged
    assert disk_dataset_manager.exists(ds_id) is False
    assert disk_dataset_manager.get_dataset(ds_id) is None
    assert disk_dataset_manager.get_metadata(ds_id) is None
    assert not (storage_dir / f"{ds_id}.parquet").is_file()
    assert not (storage_dir / f"{ds_id}.meta.json").is_file()


def test_delete_dataset_removes_own_vectors_and_preserves_others(memory_dataset_manager, isolated_vector_store):
    """Scenarios 2 & 3: Deleting a dataset purges only its vectors, preserving other datasets' vectors."""
    ds_a = "dataset_alpha"
    ds_b = "dataset_beta"

    df_a = pd.DataFrame({"a": [1, 2]})
    df_b = pd.DataFrame({"b": [3, 4]})

    memory_dataset_manager.register_dataset(df=df_a, filename="a.csv", dataset_id=ds_a)
    memory_dataset_manager.register_dataset(df=df_b, filename="b.csv", dataset_id=ds_b)

    # Insert 2 chunks for dataset A and 2 chunks for dataset B
    chunks_a = [
        Chunk(chunk_id=f"ca_{i}", doc_id=f"da_{i}", text=f"Chunk A {i}", metadata={"dataset_id": ds_a, "row_start": i, "row_end": i + 1})
        for i in range(2)
    ]
    chunks_b = [
        Chunk(chunk_id=f"cb_{i}", doc_id=f"db_{i}", text=f"Chunk B {i}", metadata={"dataset_id": ds_b, "row_start": i, "row_end": i + 1})
        for i in range(2)
    ]

    isolated_vector_store.add_chunks(chunks_a, [[0.1, 0.2, 0.3], [0.11, 0.22, 0.33]])
    isolated_vector_store.add_chunks(chunks_b, [[0.4, 0.5, 0.6], [0.44, 0.55, 0.66]])

    assert isolated_vector_store.count_vectors(ds_a) == 2
    assert isolated_vector_store.count_vectors(ds_b) == 2

    # Delete dataset A
    deleted_a = memory_dataset_manager.delete_dataset(ds_a)
    assert deleted_a is True

    # Dataset A's vectors must be completely purged from ChromaDB
    assert isolated_vector_store.count_vectors(ds_a) == 0
    assert isolated_vector_store.dataset_exists(ds_a) is False

    # Dataset B's vectors must be completely untouched and accessible
    assert isolated_vector_store.count_vectors(ds_b) == 2
    assert isolated_vector_store.dataset_exists(ds_b) is True
    search_b = isolated_vector_store.search([0.4, 0.5, 0.6], dataset_id=ds_b, top_k=2)
    assert len(search_b) == 2


def test_repeated_and_missing_dataset_deletion(memory_dataset_manager):
    """Scenarios 4 & 5: Repeated deletion and missing dataset IDs produce predictable outcomes."""
    ds_id = f"test-repeat-{uuid.uuid4().hex[:8]}"
    df = pd.DataFrame({"x": [1]})
    memory_dataset_manager.register_dataset(df=df, filename="x.csv", dataset_id=ds_id)

    # First deletion: returns True
    assert memory_dataset_manager.delete_dataset(ds_id) is True
    assert memory_dataset_manager.exists(ds_id) is False

    # Second (repeated) deletion: returns False safely
    assert memory_dataset_manager.delete_dataset(ds_id) is False

    # Non-existent dataset ID: returns False safely without error
    assert memory_dataset_manager.delete_dataset("completely-nonexistent-uuid") is False


def test_re_registration_does_not_expose_old_vectors_or_cache(memory_dataset_manager, isolated_vector_store):
    """Scenario 6 & 7: Re-registering a dataset ID purges prior vectors and cached context."""
    from api_helpers import _DATASET_CONTEXT_CACHE, build_dataset_context

    ds_id = f"re-register-{uuid.uuid4().hex[:8]}"
    df_v1 = pd.DataFrame({"metric_v1": [100, 200]})

    memory_dataset_manager.register_dataset(df=df_v1, filename="v1.csv", dataset_id=ds_id)
    ctx_v1 = build_dataset_context(ds_id, df_v1, "v1.csv")
    assert "metric_v1" in ctx_v1
    assert ds_id in _DATASET_CONTEXT_CACHE

    # Insert a vector for v1
    chunk = Chunk(chunk_id=f"c_{ds_id}", doc_id=f"d_{ds_id}", text="Old chunk", metadata={"dataset_id": ds_id, "row_start": 0, "row_end": 1})
    isolated_vector_store.add_chunks([chunk], [[0.1, 0.2, 0.3]])
    assert isolated_vector_store.count_vectors(ds_id) == 1

    # Delete dataset
    memory_dataset_manager.delete_dataset(ds_id)
    assert ds_id not in _DATASET_CONTEXT_CACHE
    assert isolated_vector_store.count_vectors(ds_id) == 0

    # Re-register under the same ID with different data
    df_v2 = pd.DataFrame({"metric_v2": [999]})
    memory_dataset_manager.register_dataset(df=df_v2, filename="v2.csv", dataset_id=ds_id)

    # Vectors must remain 0 until new indexing occurs
    assert isolated_vector_store.count_vectors(ds_id) == 0

    # Cache should be freshly populated with v2 when requested
    ctx_v2 = build_dataset_context(ds_id, df_v2, "v2.csv")
    assert "metric_v2" in ctx_v2
    assert "metric_v1" not in ctx_v2


def test_partial_cleanup_failure_resilience(tmp_path):
    """Scenario 8: Partial vector store failure is logged safely without crashing caller."""
    mock_vector_store = MagicMock()
    mock_vector_store.delete_dataset.side_effect = RuntimeError("ChromaDB connection timeout")

    engine = InMemoryStorageEngine()
    manager = DatasetManager(engine=engine, vector_store=mock_vector_store)

    ds_id = "test-partial-fail"
    df = pd.DataFrame({"val": [1, 2]})
    manager.register_dataset(df=df, filename="test.csv", dataset_id=ds_id)

    # Reset mock after registration to isolate delete_dataset call
    mock_vector_store.reset_mock()

    # Deletion should complete primary storage removal and return True without raising exception
    res = manager.delete_dataset(ds_id)
    assert res is True
    assert manager.exists(ds_id) is False
    mock_vector_store.delete_dataset.assert_called_once_with(ds_id)


def test_background_ingestion_aborts_if_dataset_deleted_mid_flight(tmp_path, isolated_vector_store):
    """Scenario 9: Background ingestion aborts vector insertion if dataset was deleted mid-flight."""
    engine = InMemoryStorageEngine()
    manager = DatasetManager(engine=engine, vector_store=isolated_vector_store)

    pipeline = IngestionPipeline()
    pipeline.vector_store = isolated_vector_store

    mock_embedding = MagicMock()
    mock_embedding.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    pipeline.embedding_service = mock_embedding

    ds_id = f"test-race-{uuid.uuid4().hex[:8]}"
    df = pd.DataFrame({"content": ["Row 1 data for testing ingestion abort"]})

    # Register dataset initially
    manager.register_dataset(df=df, filename="race.csv", dataset_id=ds_id)

    # Delete dataset BEFORE embedding/vector insert completes
    manager.delete_dataset(ds_id)
    assert manager.exists(ds_id) is False

    # Run ingestion - should abort early and NOT insert any vectors
    pipeline.run_ingestion(ds_id, df, "race.csv", manager)

    # Verify no vectors were stored for the deleted dataset
    assert isolated_vector_store.count_vectors(ds_id) == 0


def test_security_gate_no_unauthenticated_http_delete_endpoint():
    """Scenario 10: Security gate verification.

    Verifies that the canonical backend does NOT expose an unauthenticated destructive
    HTTP DELETE endpoint for datasets (e.g. DELETE /datasets/{id} or /dataset/{id}).
    """
    client = TestClient(app)

    random_id = str(uuid.uuid4())
    # Test common REST paths for dataset deletion
    response_1 = client.delete(f"/datasets/{random_id}")
    assert response_1.status_code in (404, 405), f"Unexpected exposure of DELETE /datasets/{random_id}: {response_1.status_code}"

    response_2 = client.delete(f"/dataset/{random_id}")
    assert response_2.status_code in (404, 405), f"Unexpected exposure of DELETE /dataset/{random_id}: {response_2.status_code}"

    response_3 = client.delete(f"/api/datasets/{random_id}")
    assert response_3.status_code in (404, 405), f"Unexpected exposure of DELETE /api/datasets/{random_id}: {response_3.status_code}"
