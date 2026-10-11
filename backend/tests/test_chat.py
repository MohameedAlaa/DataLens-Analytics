"""Unit tests for AI chat endpoint, dataset retrieval by dataset_id, and AI exception mapping."""

import pytest
from api_helpers import AIRateLimitError, AIUnavailableError


def test_chat_success(client, make_csv, mock_ai_response):
    """Test successful chat turn using a valid dataset_id."""
    upload_res = client.post(
        "/upload",
        files={"file": ("data.csv", make_csv("product,sales\nApple,100\nBanana,150"), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    chat_req = {
        "dataset_id": dataset_id,
        "question": "Which product has higher sales?",
        "history": [],
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"] == "Mocked AI answer about dataset."


def test_chat_legacy_filename(client, make_csv, mock_ai_response):
    """Test chat turn using legacy filename alias."""
    upload_res = client.post(
        "/upload",
        files={"file": ("sales.csv", make_csv("item,qty\nA,10\nB,20"), "text/csv")},
    )
    assert upload_res.status_code == 200

    dataset_id = upload_res.json()["dataset_id"]
    chat_req = {
        "filename": dataset_id,
        "question": "Summarize quantities.",
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 200


def test_chat_invalid_dataset_id(client):
    """Test chat request with non-existent dataset_id returns 404."""
    chat_req = {
        "dataset_id": "non-existent-uuid-99999",
        "question": "What is the average?",
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 404
    assert "not found" in str(response.json()).lower()


def test_chat_missing_dataset_id_and_filename(client):
    """Test chat request missing both dataset_id and filename returns 400."""
    chat_req = {"question": "Hello?"}
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 400


def test_chat_empty_question(client):
    """Test chat request with empty/whitespace question returns 422 validation error."""
    chat_req = {
        "dataset_id": "some-id",
        "question": "   ",
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 422


def test_chat_oversized_question(client):
    """Test chat request with question exceeding 2000 characters returns 422 validation error."""
    chat_req = {
        "dataset_id": "some-id",
        "question": "a" * 2005,
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 422


def test_chat_ai_rate_limit_error(client, make_csv, monkeypatch):
    """Test that AIRateLimitError maps to HTTP 429 status code."""
    upload_res = client.post(
        "/upload",
        files={"file": ("data.csv", make_csv("a,b\n1,2"), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    async def _mock_rate_limit(*args, **kwargs):
        raise AIRateLimitError("429 Too Many Requests from Gemini API")

    monkeypatch.setattr("app.generate_chat_response_async", _mock_rate_limit)

    chat_req = {
        "dataset_id": dataset_id,
        "question": "Calculate correlation",
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 429
    assert "rate limit" in str(response.json()).lower()


def test_chat_ai_unavailable_error(client, make_csv, monkeypatch):
    """Test that AIUnavailableError maps to HTTP 503 status code when non-deterministic."""
    upload_res = client.post(
        "/upload",
        files={"file": ("data.csv", make_csv("a,b\n1,2"), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    async def _mock_unavailable(*args, **kwargs):
        raise AIUnavailableError("503 Service Unavailable")

    monkeypatch.setattr("app.generate_chat_response_async", _mock_unavailable)

    chat_req = {
        "dataset_id": dataset_id,
        "question": "Calculate correlation",
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 503
    assert "unavailable" in str(response.json()).lower()


def test_deterministic_analytics_fallback_on_llm_failure(client, make_csv, monkeypatch):
    """Verify deterministic query succeeds with exact arithmetic fallback when LLM fails/times out."""
    upload_res = client.post(
        "/upload",
        files={"file": ("sales_fallback.csv", make_csv("country,sales\nUSA,1000\nEgypt,1900"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    # Simulate upstream Gemini timeout/failure in call_ai_async
    async def _failing_ai(*args, **kwargs):
        raise RuntimeError("Gemini API request timed out (simulated 504/timeout)")

    monkeypatch.setattr("services.ai.rag.llm_service.call_ai_async", _failing_ai)
    monkeypatch.setattr("api_helpers.call_ai_async", _failing_ai)

    # Question with deterministic answer: total sales = 2900
    chat_req = {
        "dataset_id": dataset_id,
        "question": "What is the total sales?",
    }
    response = client.post("/chat", json=chat_req)
    assert response.status_code == 200, f"Expected 200 via fallback, got {response.status_code}: {response.text}"
    data = response.json()
    assert "analytics" in data
    assert data["analytics"]["value"] == 2900
    assert "2900" in data["answer"]
    assert "deterministic" in data["answer"].lower()

