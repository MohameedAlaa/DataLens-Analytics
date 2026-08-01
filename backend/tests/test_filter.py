"""Unit tests for dataset filtering endpoint and criteria validation."""

import pytest


def test_filter_by_dataset_id(client, make_csv):
    """Test filtering an uploaded dataset using its dataset_id."""
    upload_res = client.post(
        "/upload",
        files={"file": ("test.csv", make_csv("name,age\nAlice,30\nBob,25\nCharlie,35"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    filter_req = {
        "dataset_id": dataset_id,
        "filters": {"age": {"min": 28}},
    }
    response = client.post("/filter", json=filter_req)
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 2


def test_filter_by_legacy_filename(client, make_csv):
    """Test filtering an uploaded dataset using backward-compatible filename alias."""
    upload_res = client.post(
        "/upload",
        files={"file": ("legacy.csv", make_csv("val\n10\n20\n30"), "text/csv")},
    )
    assert upload_res.status_code == 200

    filter_req = {
        "filename": "legacy.csv",
        "filters": {"val": {"max": 15}},
    }
    response = client.post("/filter", json=filter_req)
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 1


def test_filter_by_inline_data(client):
    """Test filtering dataset rows provided directly in request body."""
    inline_data = [
        {"city": "Paris", "temp": 22},
        {"city": "Berlin", "temp": 18},
        {"city": "Madrid", "temp": 30},
    ]
    filter_req = {
        "data": inline_data,
        "filters": {"temp": {"min": 20}},
    }
    response = client.post("/filter", json=filter_req)
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 2


def test_filter_invalid_dataset_id(client):
    """Test filter request with a non-existent dataset_id (404 error)."""
    filter_req = {
        "dataset_id": "non-existent-uuid-12345",
        "filters": {"col": "val"},
    }
    response = client.post("/filter", json=filter_req)
    assert response.status_code == 404
    assert "not found" in str(response.json()).lower()


def test_filter_missing_all_data_sources(client):
    """Test filter request without dataset_id, filename, or inline data (400 error)."""
    filter_req = {"filters": {"col": "val"}}
    response = client.post("/filter", json=filter_req)
    assert response.status_code == 400


def test_filter_too_many_keys(client):
    """Test input sanitization rejecting request with >20 filter keys."""
    too_many_filters = {f"key_{i}": i for i in range(25)}
    filter_req = {"data": [{"x": 1}], "filters": too_many_filters}
    response = client.post("/filter", json=filter_req)
    # Validation error from Pydantic validator returns 422
    assert response.status_code == 422
