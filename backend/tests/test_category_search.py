"""Regression tests for Approach A: Dedicated Categorical Search Endpoint (/categories & /api/categories)."""

import pytest
import pandas as pd


def test_category_search_discovers_values_outside_top_50(client, make_csv):
    """Verify that a category outside the original top 50 can be searched, discovered,

    and then used to filter the full dataset correctly.
    """
    rows = ["id,category,amount"]
    # 60 distinct categories:
    # Cat_01 to Cat_50 have 10 occurrences each (top 50)
    for i in range(1, 51):
        cat_name = f"CommonCat_{i:02d}"
        for _ in range(10):
            rows.append(f"0,{cat_name},100")

    # Cat_51 to Cat_60 have 1 occurrence each (outside top 50)
    for i in range(51, 61):
        cat_name = f"RareCat_{i:02d}"
        rows.append(f"{i},{cat_name},500")

    # Specifically target RareCat_55
    csv_content = "\n".join(rows)
    response = client.post(
        "/upload",
        files={"file": ("dataset_search_test.csv", make_csv(csv_content), "text/csv")},
    )
    assert response.status_code == 200
    upload_data = response.json()
    dataset_id = upload_data["dataset_id"]

    # In top_values returned by /upload, RareCat_55 is NOT present because top 50 are CommonCat_01..50
    initial_top = [x["value"] for x in upload_data["filter_options"]["category"]["top_values"]]
    assert len(initial_top) == 50
    assert "RareCat_55" not in initial_top

    # 1. Search for 'RareCat' via /api/categories
    search_resp = client.get(
        "/api/categories",
        params={
            "dataset_id": dataset_id,
            "column": "category",
            "query": "RareCat",
            "limit": 50,
        },
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()

    assert search_data["column"] == "category"
    assert search_data["query"] == "RareCat"
    assert search_data["total_matches"] == 10
    assert search_data["truncated"] is False
    found_values = [item["value"] for item in search_data["values"]]
    assert "RareCat_55" in found_values

    # 2. Case-insensitive substring search for 'rarecat_55'
    search_ci = client.get(
        "/categories",
        params={
            "dataset_id": dataset_id,
            "column": "category",
            "query": "rarecat_55",
            "limit": 10,
        },
    )
    assert search_ci.status_code == 200
    ci_data = search_ci.json()
    assert len(ci_data["values"]) == 1
    assert ci_data["values"][0]["value"] == "RareCat_55"
    assert ci_data["values"][0]["count"] == 1

    # 3. Filter using the discovered category and verify result
    filter_resp = client.post(
        "/filter",
        json={
            "dataset_id": dataset_id,
            "filters": {"category": ["RareCat_55"]},
        },
    )
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    assert filter_data["row_count"] == 1
    assert filter_data["filtered_data"][0]["id"] == 55
    assert filter_data["filtered_data"][0]["category"] == "RareCat_55"


def test_category_search_dataset_isolation(client, make_csv):
    """Verify that results from one dataset NEVER leak into another dataset's search."""
    # Dataset 1
    csv1 = "item,tag\nA1,TagOnlyInDatasetOne\nA2,CommonTag"
    resp1 = client.post("/upload", files={"file": ("ds1.csv", make_csv(csv1), "text/csv")})
    assert resp1.status_code == 200
    ds1_id = resp1.json()["dataset_id"]

    # Dataset 2
    csv2 = "item,tag\nB1,TagOnlyInDatasetTwo\nB2,CommonTag"
    resp2 = client.post("/upload", files={"file": ("ds2.csv", make_csv(csv2), "text/csv")})
    assert resp2.status_code == 200
    ds2_id = resp2.json()["dataset_id"]

    # Query DS2 for DS1's unique tag -> must find 0 matches
    res_iso = client.get(
        "/api/categories",
        params={
            "dataset_id": ds2_id,
            "column": "tag",
            "query": "TagOnlyInDatasetOne",
        },
    )
    assert res_iso.status_code == 200
    data_iso = res_iso.json()
    assert data_iso["total_matches"] == 0
    assert len(data_iso["values"]) == 0

    # Query DS1 for DS1's unique tag -> must find 1 match
    res_ds1 = client.get(
        "/api/categories",
        params={
            "dataset_id": ds1_id,
            "column": "tag",
            "query": "TagOnlyInDatasetOne",
        },
    )
    assert res_ds1.status_code == 200
    assert res_ds1.json()["total_matches"] == 1
    assert res_ds1.json()["values"][0]["value"] == "TagOnlyInDatasetOne"


def test_category_search_nulls_and_mixed_types(client, make_csv):
    """Verify safe handling of nulls, booleans, and mixed types without crashing."""
    csv_content = (
        "id,mixed_col\n"
        "1,100\n"
        "2,\n"
        "3,True\n"
        "4,100\n"
        "5,Hello World\n"
        "6,\n"
        "7,hello again\n"
    )
    resp = client.post("/upload", files={"file": ("mixed.csv", make_csv(csv_content), "text/csv")})
    assert resp.status_code == 200
    ds_id = resp.json()["dataset_id"]

    # Search for "hello" -> matches "Hello World" and "hello again", ignores nulls
    res = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "mixed_col", "query": "hello"},
    )
    assert res.status_code == 200
    data = res.json()
    vals = {item["value"]: item["count"] for item in data["values"]}
    assert "Hello World" in vals
    assert "hello again" in vals
    assert None not in vals
    assert "nan" not in vals

    # Search numeric string "100"
    res_num = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "mixed_col", "query": "100"},
    )
    assert res_num.status_code == 200
    assert res_num.json()["values"][0]["value"] == "100"
    assert res_num.json()["values"][0]["count"] == 2

    # Empty query should return all non-null values up to limit
    res_empty = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "mixed_col", "query": ""},
    )
    assert res_empty.status_code == 200
    all_vals = [x["value"] for x in res_empty.json()["values"]]
    assert "nan" not in all_vals
    assert "None" not in all_vals
    assert len(all_vals) == 4  # '100', 'True', 'Hello World', 'hello again'


def test_category_search_literal_matching_special_chars(client, make_csv):
    """Verify that regex special characters (.*+?[]^${}()) are matched literally, not evaluated as regex."""
    csv_content = (
        "id,code\n"
        "1,C++\n"
        "2,C#\n"
        "3,C.*[test]\n"
        "4,Java (SE)\n"
    )
    resp = client.post("/upload", files={"file": ("codes.csv", make_csv(csv_content), "text/csv")})
    assert resp.status_code == 200
    ds_id = resp.json()["dataset_id"]

    # Search literal ".*" -> should ONLY match "C.*[test]", not everything
    res = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "code", "query": ".*"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_matches"] == 1
    assert data["values"][0]["value"] == "C.*[test]"

    # Search literal "C++" -> '+' should not cause regex syntax error
    res_plus = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "code", "query": "C++"},
    )
    assert res_plus.status_code == 200
    assert res_plus.json()["total_matches"] == 1
    assert res_plus.json()["values"][0]["value"] == "C++"

    # Search literal "(SE)"
    res_paren = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "code", "query": "(SE)"},
    )
    assert res_paren.status_code == 200
    assert res_paren.json()["total_matches"] == 1
    assert res_paren.json()["values"][0]["value"] == "Java (SE)"


def test_category_search_limits_and_truncation(client, make_csv):
    """Verify that result limits are clamped (max 100) and truncation metadata is accurately reported."""
    rows = ["id,color"]
    for i in range(150):
        rows.append(f"{i},Color_{i:03d}")
    csv_content = "\n".join(rows)

    resp = client.post("/upload", files={"file": ("colors.csv", make_csv(csv_content), "text/csv")})
    assert resp.status_code == 200
    ds_id = resp.json()["dataset_id"]

    # Request default limit (50) for "Color_"
    res_50 = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "color", "query": "Color_"},
    )
    assert res_50.status_code == 200
    data_50 = res_50.json()
    assert len(data_50["values"]) == 50
    assert data_50["total_matches"] == 150
    assert data_50["truncated"] is True

    # Request limit=20
    res_20 = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "color", "query": "Color_", "limit": 20},
    )
    assert res_20.status_code == 200
    assert len(res_20.json()["values"]) == 20
    assert res_20.json()["truncated"] is True

    # Request limit > 100 (e.g. 200) -> FastAPI Query validation clamps/errors or bounds it
    # Notice our FastAPI Query validator specifies le=100
    res_over = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "color", "query": "Color_", "limit": 200},
    )
    assert res_over.status_code == 422  # RequestValidationError


def test_category_search_validation_errors(client, make_csv):
    """Verify error handling: missing dataset, invalid column, empty dataset_id, query too long."""
    csv_content = "id,status\n1,active\n2,pending"
    resp = client.post("/upload", files={"file": ("status.csv", make_csv(csv_content), "text/csv")})
    assert resp.status_code == 200
    ds_id = resp.json()["dataset_id"]

    # 1. Non-existent dataset
    res_no_ds = client.get(
        "/api/categories",
        params={"dataset_id": "non_existent_dataset_id", "column": "status"},
    )
    assert res_no_ds.status_code == 404

    # 2. Non-existent column
    res_no_col = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "non_existent_column"},
    )
    assert res_no_col.status_code == 400
    assert "not found" in res_no_col.json()["detail"]

    # 3. Missing/blank dataset_id
    res_blank_ds = client.get(
        "/api/categories",
        params={"dataset_id": "   ", "column": "status"},
    )
    assert res_blank_ds.status_code == 400

    # 4. Overly long query (> 100 chars)
    long_query = "x" * 101
    res_long_q = client.get(
        "/api/categories",
        params={"dataset_id": ds_id, "column": "status", "query": long_query},
    )
    assert res_long_q.status_code == 422
