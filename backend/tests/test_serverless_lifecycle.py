"""Regression test for serverless api/ endpoint lifecycle: upload -> chat -> filter.

Tests the actual endpoint flow through the serverless FastAPI app (api.index:app).
Demonstrates:
1. upload followed by chat and filter lifecycle once READY.
2. Lifecycle state enforcement (PENDING/PROCESSING returns 409, FAILED returns 400).
3. Security: filename-only lookup rejection in filter endpoint.
4. Process isolation: Worker A and Worker B with independent in-memory state do not share datasets.
5. Persistent disk storage: Worker A writes to DiskStorageEngine, Worker B reads after Worker A terminates.
"""

import io
import sys
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient

root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from api.index import app as serverless_app
try:
    from backend.dataset_manager import (
        DatasetManager,
        DiskStorageEngine,
        InMemoryStorageEngine,
        create_default_dataset_manager,
        dataset_manager as default_dm,
    )
except ImportError:
    from dataset_manager import (
        DatasetManager,
        DiskStorageEngine,
        InMemoryStorageEngine,
        create_default_dataset_manager,
        dataset_manager as default_dm,
    )


def test_serverless_app_upload_chat_filter_lifecycle():
    """Verify that uploading via /upload makes the dataset accessible to /chat and /filter once indexed."""
    client = TestClient(serverless_app)

    # 1. Upload CSV
    csv_bytes = b"dept,budget\nEngineering,100000\nMarketing,50000\n"
    res_upload = client.post("/upload/", files={"file": ("dept.csv", io.BytesIO(csv_bytes), "text/csv")})
    assert res_upload.status_code == 200
    dataset_id = res_upload.json()["dataset_id"]

    # In TestClient, BackgroundTasks executes run_ingestion synchronously, transitioning PENDING -> READY
    meta = default_dm.get_metadata(dataset_id)
    assert meta is not None
    assert meta["indexing_status"] == "READY"

    # 2. Query Chat using the returned dataset_id
    res_chat = client.post("/chat/", json={
        "question": "What is the total budget?",
        "dataset_id": dataset_id,
        "history": [],
    })
    assert res_chat.status_code == 200, f"Chat failed with {res_chat.status_code}: {res_chat.text}"
    assert "answer" in res_chat.json()

    # 3. Filter using the returned dataset_id
    res_filter = client.post("/filter/", json={
        "dataset_id": dataset_id,
        "filters": {"budget": {"min": 60000}},
    })
    assert res_filter.status_code == 200, f"Filter failed with {res_filter.status_code}: {res_filter.text}"
    assert res_filter.json()["row_count"] == 1


def test_serverless_indexing_lifecycle_status_enforcement():
    """Verify that /chat and /filter strictly enforce PENDING -> 409 and FAILED -> 400."""
    client = TestClient(serverless_app)
    df = pd.DataFrame({"item": ["pen", "pencil"], "cost": [1.5, 0.75]})
    ds_id = "lifecycle-enforcement-id"

    # 1. Dataset is PENDING
    default_dm.register_dataset(df, "items.csv", ds_id)
    assert default_dm.get_metadata(ds_id)["indexing_status"] == "PENDING"

    # Chat must return 409 Conflict
    res_chat_pending = client.post("/chat/", json={"question": "Cost?", "dataset_id": ds_id})
    assert res_chat_pending.status_code == 409
    assert "in progress" in res_chat_pending.json()["detail"].lower()

    # Filter must return 409 Conflict
    res_filter_pending = client.post("/filter/", json={"dataset_id": ds_id, "filters": {}})
    assert res_filter_pending.status_code == 409

    # 2. Dataset is PROCESSING
    default_dm.update_indexing_status(ds_id, "PROCESSING")
    res_chat_proc = client.post("/chat/", json={"question": "Cost?", "dataset_id": ds_id})
    assert res_chat_proc.status_code == 409

    # 3. Dataset is FAILED
    default_dm.update_indexing_status(ds_id, "FAILED")
    res_chat_failed = client.post("/chat/", json={"question": "Cost?", "dataset_id": ds_id})
    assert res_chat_failed.status_code == 400
    assert "failed" in res_chat_failed.json()["detail"].lower()

    res_filter_failed = client.post("/filter/", json={"dataset_id": ds_id, "filters": {}})
    assert res_filter_failed.status_code == 400

    # 4. Dataset is READY
    default_dm.update_indexing_status(ds_id, "READY")
    res_filter_ready = client.post("/filter/", json={"dataset_id": ds_id, "filters": {}})
    assert res_filter_ready.status_code == 200

    default_dm.delete_dataset(ds_id)


def test_filter_rejects_filename_only_lookup():
    """Verify that filename-only lookup is rejected to preserve UUID-based dataset isolation."""
    client = TestClient(serverless_app)
    # Request without dataset_id and without inline data must fail with 400
    res = client.post("/filter/", json={"filename": "sample.csv", "filters": {}})
    assert res.status_code == 400
    assert "dataset_id" in res.json()["detail"].lower()


def test_serverless_cross_worker_process_isolation():
    """Verify that separate serverless worker process instances do not share in-memory datasets."""
    # Worker A receives upload
    worker_a_manager = DatasetManager(engine=InMemoryStorageEngine())
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    worker_a_manager.register_dataset(df, "data.csv", "worker-a-id")

    assert worker_a_manager.exists("worker-a-id")

    # Worker B receives chat in a fresh process / lambda container
    worker_b_manager = DatasetManager(engine=InMemoryStorageEngine())
    assert not worker_b_manager.exists("worker-a-id")
    assert worker_b_manager.get_dataset("worker-a-id") is None


def test_persistent_disk_storage_across_process_restart(tmp_path):
    """Verify that DiskStorageEngine preserves datasets across separate worker instances and restarts."""
    storage_dir = tmp_path / "datasets"

    # Worker Instance 1: registers dataset and updates status to READY
    worker_1 = DatasetManager(engine=DiskStorageEngine(storage_dir=storage_dir))
    df = pd.DataFrame({"country": ["USA", "Egypt", "Germany"], "users": [500, 350, 200]})
    dataset_id = worker_1.register_dataset(df, "users.csv", "persistent-uuid-456")
    worker_1.update_indexing_status(dataset_id, "READY")

    # Terminate / garbage collect Worker Instance 1
    del worker_1

    # Worker Instance 2 (simulating cold start or process restart pointing to same storage)
    worker_2 = DatasetManager(engine=DiskStorageEngine(storage_dir=storage_dir))

    assert worker_2.exists("persistent-uuid-456")
    retrieved_df = worker_2.get_dataset("persistent-uuid-456")
    assert retrieved_df is not None
    assert len(retrieved_df) == 3
    assert list(retrieved_df["country"]) == ["USA", "Egypt", "Germany"]

    meta = worker_2.get_metadata("persistent-uuid-456")
    assert meta is not None
    assert meta["indexing_status"] == "READY"
    assert meta["rows"] == 3

    # Verify deletion and disk cleanup
    assert worker_2.delete_dataset("persistent-uuid-456") is True
    assert worker_2.exists("persistent-uuid-456") is False
    assert worker_2.get_dataset("persistent-uuid-456") is None


def test_disk_storage_engine_fails_fast_on_unwritable_path(monkeypatch, tmp_path):
    """Verify that DiskStorageEngine raises RuntimeError if storage directory cannot be written."""
    def fail_touch(*args, **kwargs):
        raise PermissionError("Access denied: simulated read-only filesystem")

    from pathlib import Path
    monkeypatch.setattr(Path, "touch", fail_touch)

    with pytest.raises(RuntimeError, match="failed to initialize writable directory"):
        DiskStorageEngine(storage_dir=tmp_path / "readonly_dir")


def test_production_warning_on_inmemory_engine(caplog, monkeypatch):
    """Verify that create_default_dataset_manager logs a warning if running in-memory in production."""
    import logging
    try:
        import backend.config as cfg
    except ImportError:
        import config as cfg

    monkeypatch.setattr(cfg.settings, "storage_engine", "memory")
    monkeypatch.setattr(cfg.settings, "app_env", "production")

    with caplog.at_level(logging.WARNING):
        dm = create_default_dataset_manager()
        assert isinstance(dm._engine, InMemoryStorageEngine)

    assert any("PRODUCTION WARNING" in record.message for record in caplog.records)

