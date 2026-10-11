"""Shared pytest fixtures for DataLens Analytics backend test suite.

Includes:
- FastAPI TestClient / AsyncClient
- DatasetManager state reset before each test
- Rate limiter disabled for test speed
- Mock AI API calls
- Helper functions to generate synthetic CSV/Excel bytes
"""

import io
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi.testclient import TestClient

from app import app, limiter
from api_helpers import _context_cache


@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory dataset manager, rate limiter, and chat context cache before every test."""
    if limiter is not None:
        limiter.enabled = False

    dataset_manager = app.state.dataset_manager

    # Clear datasets
    for item in list(dataset_manager.list_datasets()):
        dataset_id = item["dataset_id"] if isinstance(item, dict) else item
        dataset_manager.delete_dataset(dataset_id)

    # Clear context cache
    _context_cache.clear()
    yield

    # Cleanup after test
    for item in list(dataset_manager.list_datasets()):
        dataset_id = item["dataset_id"] if isinstance(item, dict) else item
        dataset_manager.delete_dataset(dataset_id)
    _context_cache.clear()


@pytest.fixture
def client():
    """Synchronous TestClient fixture."""
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous AsyncClient fixture."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
def make_csv():
    """Factory fixture to build CSV bytes."""

    def _make_csv(
        content: str = "name,age,city\nAlice,30,New York\nBob,25,London\nCharlie,35,Paris"
    ) -> bytes:
        return content.encode("utf-8")

    return _make_csv


@pytest.fixture
def mock_ai_response(monkeypatch):
    """Mock `generate_chat_response_async` in app module to return a predictable response by default."""
    async def _mock_generate(*args, **kwargs):
        return {"response": "Mocked AI answer about dataset."}

    monkeypatch.setattr("app.generate_chat_response_async", _mock_generate)
