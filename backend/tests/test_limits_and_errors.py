"""Unit tests for stats endpoint, health check, security response headers, and request tracing."""

import pytest


def test_stats_valid_dataset_id(client, make_csv):
    """Test retrieving statistics for a valid dataset_id."""
    upload_res = client.post(
        "/upload",
        files={"file": ("stats.csv", make_csv("num1,num2\n10,20\n30,40"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    response = client.get(f"/stats/{dataset_id}")
    assert response.status_code == 200
    data = response.json()
    assert "numeric_summary" in data
    assert "num1" in data["numeric_summary"]


def test_stats_invalid_dataset_id(client):
    """Test stats endpoint with an invalid dataset_id returns 404."""
    response = client.get("/stats/unknown-uuid-00000")
    assert response.status_code == 404
    assert "not found" in str(response.json()).lower()


def test_health_endpoint(client):
    """Test /health probe returns 200 and expected status dict."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "datasets_loaded" in data


def test_security_headers_and_request_id(client):
    """Test that all responses include X-Request-ID and security headers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-Ms" in response.headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
