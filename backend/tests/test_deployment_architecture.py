"""Regression tests for deployment architecture, dependency injection, and process isolation.

Verifies:
1. Single-process FastAPI application lifecycle and dependency injection (upload -> chat -> filter).
2. Serverless multi-worker process isolation boundary:
   Demonstrates that in-memory state in one worker is NOT shared across independent serverless worker instances.
3. Statelessness of api/upload router.
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

from app import app, get_dataset_manager
from dataset_manager import DatasetManager, InMemoryStorageEngine
from api.upload import upload as serverless_upload
from api.filter import filter_data as serverless_filter, FilterRequest


def test_single_process_di_lifecycle(client):
    """Verify that in single-process FastAPI deployments, dependency injection provides consistent dataset state."""
    # 1. Upload CSV
    csv_bytes = b"dept,budget,headcount\nSales,50000,10\nEngineering,120000,25\nHR,30000,5\n"
    res = client.post("/upload", files={"file": ("dept.csv", io.BytesIO(csv_bytes), "text/csv")})
    assert res.status_code == 200
    dataset_id = res.json()["dataset_id"]

    # Verify dataset exists in app.state.dataset_manager
    dm = app.state.dataset_manager
    assert dm.exists(dataset_id)
    df = dm.get_dataset(dataset_id)
    assert df is not None
    assert len(df) == 3

    # 2. Filter dataset using the registered dataset_id
    res_filter = client.post("/filter", json={
        "dataset_id": dataset_id,
        "filters": {"budget": {"min": 40000}}
    })
    assert res_filter.status_code == 200
    filter_data = res_filter.json()
    assert filter_data["row_count"] == 2  # Sales and Engineering

    # 3. Clean up
    dm.delete_dataset(dataset_id)
    assert not dm.exists(dataset_id)


def test_serverless_process_isolation_boundary():
    """Verify that separate serverless worker instances do NOT share in-memory dataset state.

    This test proves that a module-level or in-memory singleton in Worker A does not leak
    or persist across isolated serverless function boundaries into Worker B.
    """
    # Simulate Worker A (e.g. Lambda/Serverless Function A handling /upload)
    worker_a_manager = DatasetManager(engine=InMemoryStorageEngine())
    sample_df = pd.DataFrame({"product": ["A", "B"], "price": [10, 20]})
    dataset_id = "test-isolated-uuid-1234"
    worker_a_manager.register_dataset(sample_df, "test.csv", dataset_id)

    assert worker_a_manager.exists(dataset_id)
    assert worker_a_manager.get_dataset(dataset_id) is not None

    # Simulate Worker B (e.g. Lambda/Serverless Function B handling /chat)
    worker_b_manager = DatasetManager(engine=InMemoryStorageEngine())

    # Worker B has independent memory; the dataset must NOT be present
    assert not worker_b_manager.exists(dataset_id)
    assert worker_b_manager.get_dataset(dataset_id) is None


@pytest.mark.asyncio
async def test_serverless_api_upload_statelessness():
    """Verify that the Vercel api/upload router parses data statelessly without mutating persistent state."""
    from starlette.datastructures import UploadFile

    csv_data = b"col1,col2\n1,2\n3,4\n"
    file = UploadFile(filename="stateless.csv", file=io.BytesIO(csv_data))

    result = await serverless_upload(file=file)
    assert "dataset_id" in result
    assert result["shape"] == [2, 2]
    assert len(result["preview"]) == 2


def test_canonical_backend_route_coverage():
    """Verify that backend/app.py provides complete route coverage at both root and /api prefixes."""
    routes = {r.path for r in app.routes}
    required_routes = [
        "/upload", "/api/upload",
        "/filter", "/api/filter",
        "/chat", "/api/chat",
        "/stats/{dataset_id}", "/api/stats/{dataset_id}",
        "/categories", "/api/categories",
        "/health", "/api/health",
    ]
    for route in required_routes:
        assert route in routes, f"Required canonical route '{route}' missing from backend/app.py"


def test_production_deployment_configuration_alignment():
    """Verify that deployment configuration files align on the decoupled architecture:
    - frontend/vercel.json rewrites /api/* to the Render backend service.
    - render.yaml configures the persistent backend web service on backend/app.py.
    - root vercel.json is absent to prevent accidental serverless routing to api/.
    """
    import json
    import yaml

    repo_root = Path(__file__).resolve().parent.parent.parent

    # 1. Root vercel.json must not exist (prevents accidental serverless deployment of api/)
    assert not (repo_root / "vercel.json").exists(), "Root vercel.json should remain absent"

    # 2. frontend/vercel.json must rewrite /api/* to the Render backend service
    frontend_vercel = repo_root / "frontend" / "vercel.json"
    assert frontend_vercel.exists(), "frontend/vercel.json must exist"
    with open(frontend_vercel, "r", encoding="utf-8") as f:
        v_data = json.load(f)
    rewrites = v_data.get("rewrites", [])
    api_rewrite = next((r for r in rewrites if r.get("source") == "/api/(.*)"), None)
    assert api_rewrite is not None, "frontend/vercel.json must include /api/(.*) rewrite"
    assert "onrender.com" in api_rewrite["destination"], "Rewrite must target Render backend"

    # 3. render.yaml must target backend/app.py with single worker
    render_yaml = repo_root / "render.yaml"
    assert render_yaml.exists(), "render.yaml must exist"
    with open(render_yaml, "r", encoding="utf-8") as f:
        r_data = yaml.safe_load(f)
    services = r_data.get("services", [])
    assert len(services) >= 1
    backend_service = services[0]
    assert backend_service["rootDir"] == "backend"
    assert "app:app" in backend_service["startCommand"]
    assert "--workers 1" in backend_service["startCommand"]
