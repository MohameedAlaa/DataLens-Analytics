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

    dataset_id = upload_res.json()["dataset_id"]
    filter_req = {
        "filename": dataset_id,
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


def test_filter_non_finite_numeric_and_missing_values(client, make_csv):
    """Test filtering a dataset containing NaN, inf, -inf, 0, and missing values.

    Exercises the actual endpoint response and verifies:
    1. Filter response returns HTTP 200 instead of HTTP 400 serialization error.
    2. Response text is strictly valid RFC 8259 JSON without raw NaN/Infinity tokens.
    3. Non-finite values and missing values are serialized as JSON null.
    4. Valid numeric values (including 0 and 0.0) are accurately preserved.
    """
    import json

    csv_data = (
        "id,val,score,rate\n"
        "1,0,10.5,0.0\n"
        "2,0.0,,1.5\n"
        "3,-5,inf,-inf\n"
    )
    upload_res = client.post(
        "/upload",
        files={"file": ("non_finite.csv", make_csv(csv_data), "text/csv")},
    )
    assert upload_res.status_code == 200
    upload_json = upload_res.json()
    preview = upload_json["preview"]

    # Verify preview preserves 0 and 0.0, and maps missing/inf to null
    assert preview[0]["val"] == 0
    assert preview[0]["rate"] == 0.0
    assert preview[1]["score"] is None
    assert preview[2]["score"] is None
    assert preview[2]["rate"] is None

    # Strict JSON validation of preview (reject non-standard NaN / Infinity)
    strict_upload = json.loads(
        upload_res.text,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {x}")),
    )
    assert strict_upload["preview"][1]["score"] is None

    dataset_id = upload_json["dataset_id"]
    filter_req = {
        "dataset_id": dataset_id,
        "filters": {},
    }
    filter_res = client.post("/filter", json=filter_req)
    # This must return 200 and not fail with 'Failed to apply filter criteria' (ValueError: Out of range float)
    assert filter_res.status_code == 200

    # Verify strict RFC 8259 JSON parse on the raw text
    strict_filter = json.loads(
        filter_res.text,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Invalid JSON constant: {x}")),
    )
    assert strict_filter["row_count"] == 3
    rows = strict_filter["filtered_data"]

    # Check row 0: valid integers and floats (including zeros) preserved
    assert rows[0]["id"] == 1
    assert type(rows[0]["id"]) is int
    assert rows[0]["val"] == 0
    assert rows[0]["rate"] == 0.0
    assert type(rows[0]["rate"]) is float
    assert rows[0]["score"] == 10.5

    # Check row 1: empty score is None (JSON null)
    assert rows[1]["val"] == 0.0
    assert rows[1]["score"] is None
    assert rows[1]["rate"] == 1.5

    # Check row 2: inf and -inf are None (JSON null)
    assert rows[2]["val"] == -5
    assert rows[2]["score"] is None
    assert rows[2]["rate"] is None


def test_filter_inline_data_with_non_finite_values(client):
    """Test filtering inline data array containing non-finite floats and nulls."""
    import json

    inline_data = [
        {"item": "A", "price": 0.0, "qty": 0, "active": True},
        {"item": "B", "price": float("nan"), "qty": None, "active": False},
        {"item": "C", "price": float("inf"), "qty": -10, "active": True},
        {"item": "D", "price": float("-inf"), "qty": 5, "active": False},
    ]

    filter_req = {
        "data": inline_data,
        "filters": {"qty": {"min": -20}},
    }
    response = client.post("/filter", json=filter_req)
    assert response.status_code == 200

    # Ensure response strictly conforms to RFC 8259 without raw NaN / Infinity tokens
    strict_data = json.loads(
        response.text,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Disallowed constant: {x}")),
    )
    rows = strict_data["filtered_data"]
    assert len(rows) == 3  # items A, C, D (B has qty=None so filtered out by min=-20)

    # Item A: price=0.0 (float), qty=0 (int), active=True (bool)
    assert rows[0]["item"] == "A"
    assert rows[0]["price"] == 0.0
    assert type(rows[0]["price"]) is float
    assert rows[0]["qty"] == 0
    assert rows[0]["active"] is True
    assert type(rows[0]["active"]) is bool

    # Item C: price inf -> null
    assert rows[1]["item"] == "C"
    assert rows[1]["price"] is None
    assert rows[1]["qty"] == -10

    # Item D: price -inf -> null
    assert rows[2]["item"] == "D"
    assert rows[2]["price"] is None
    assert rows[2]["qty"] == 5


def test_upload_excel_with_nat_and_non_finite_preview(client):
    """Test uploading an Excel file containing NaT and missing values.

    Verifies that preview serializes cleanly to JSON, converts NaT to null,
    and preserves valid date strings and numeric values.
    """
    import io
    import json
    import pandas as pd

    df = pd.DataFrame({
        "id": [1, 2],
        "created_at": [pd.Timestamp("2026-05-16 10:30:00"), pd.NaT],
        "balance": [0.0, float("nan")],
    })
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_bytes = excel_buffer.getvalue()

    upload_res = client.post(
        "/upload",
        files={"file": ("dates.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_res.status_code == 200

    # Strict JSON validation
    parsed = json.loads(
        upload_res.text,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Disallowed constant: {x}")),
    )
    preview = parsed["preview"]
    assert len(preview) == 2

    # Row 0: valid timestamp and 0.0 float preserved
    assert "2026-05-16" in preview[0]["created_at"]
    assert preview[0]["balance"] == 0.0
    assert type(preview[0]["balance"]) is float

    # Row 1: NaT and NaN converted to null
    assert preview[1]["created_at"] is None
    assert preview[1]["balance"] is None

