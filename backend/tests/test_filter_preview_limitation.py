"""Regression tests for P1: Dataset-wide filter options derived from full dataset."""

import pytest
import pandas as pd


def test_upload_returns_dataset_wide_filter_options(client, make_csv):
    """Verify that /upload returns filter_options covering the entire dataset,

    including rows outside the first 100 preview rows.
    """
    rows = ["id,score,category"]
    # Rows 0 to 99: score in [20, 49], category in {"Alpha", "Beta"}
    for i in range(100):
        score = 20 + (i % 30)
        cat = "Alpha" if i % 2 == 0 else "Beta"
        rows.append(f"{i},{score},{cat}")

    # Rows 100 to 107: values appearing only after row 100
    rows.append("100,25,Alpha")
    rows.append("101,26,Beta")
    rows.append("102,27,Alpha")
    rows.append("103,28,Beta")
    rows.append("104,29,Alpha")
    rows.append("105,100,Alpha")  # Global maximum: 100
    rows.append("106,5,Beta")    # Global minimum: 5
    rows.append("107,35,Omega")  # New category: Omega

    csv_content = "\n".join(rows)
    response = client.post(
        "/upload",
        files={"file": ("dataset_108.csv", make_csv(csv_content), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["shape"] == [108, 3]
    assert len(data["preview"]) == 100
    assert "filter_options" in data

    filter_opts = data["filter_options"]

    # Numeric bounds for 'score' must be [5, 100] (from rows 106 and 105)
    assert "score" in filter_opts
    assert filter_opts["score"]["bounds"] == [5, 100]

    # Categorical top_values for 'category' must include 'Omega'
    assert "category" in filter_opts
    cat_vals = {item["value"]: item["count"] for item in filter_opts["category"]["top_values"]}
    assert "Omega" in cat_vals
    assert cat_vals["Omega"] == 1
    assert cat_vals["Alpha"] == 54
    assert cat_vals["Beta"] == 53

    # Now verify applying these filters returns the correct records from full dataset
    dataset_id = data["dataset_id"]

    # 1. Filter by category "Omega" (which only exists on row 107)
    res_omega = client.post("/filter", json={"dataset_id": dataset_id, "filters": {"category": ["Omega"]}})
    assert res_omega.status_code == 200
    res_omega_data = res_omega.json()
    assert res_omega_data["row_count"] == 1
    assert res_omega_data["filtered_data"][0]["id"] == 107
    assert res_omega_data["filtered_data"][0]["category"] == "Omega"

    # 2. Filter by score range [95, 105] (row 105, score 100)
    res_max = client.post("/filter", json={"dataset_id": dataset_id, "filters": {"score": {"min": 95}}})
    assert res_max.status_code == 200
    res_max_data = res_max.json()
    assert res_max_data["row_count"] == 1
    assert res_max_data["filtered_data"][0]["id"] == 105
    assert res_max_data["filtered_data"][0]["score"] == 100

    # 3. Filter by score range [0, 10] (row 106, score 5)
    res_min = client.post("/filter", json={"dataset_id": dataset_id, "filters": {"score": {"max": 10}}})
    assert res_min.status_code == 200
    res_min_data = res_min.json()
    assert res_min_data["row_count"] == 1
    assert res_min_data["filtered_data"][0]["id"] == 106
    assert res_min_data["filtered_data"][0]["score"] == 5


def test_filter_options_small_dataset(client, make_csv):
    """Verify filter_options work properly for small datasets (<100 rows)."""
    csv_content = "id,val,type\n1,10,A\n2,20,B\n3,30,A"
    response = client.post(
        "/upload",
        files={"file": ("small.csv", make_csv(csv_content), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    filter_opts = data.get("filter_options", {})

    assert filter_opts["val"]["bounds"] == [10, 30]
    vals = {item["value"]: item["count"] for item in filter_opts["type"]["top_values"]}
    assert vals == {"A": 2, "B": 1}


def test_filter_options_empty_and_null_values(client, make_csv):
    """Verify filter_options handles nulls, NaNs, and all-NaN columns safely."""
    # col_mixed has nulls + numbers [10, 50]
    # col_all_null has only nulls
    # cat_mixed has nulls + "X", "Y"
    # cat_all_null has only nulls
    csv_content = (
        "col_mixed,col_all_null,cat_mixed,cat_all_null\n"
        "10,,X,\n"
        ",,Y,\n"
        "50,,X,\n"
        ",,,\n"
    )
    response = client.post(
        "/upload",
        files={"file": ("nulls.csv", make_csv(csv_content), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    filter_opts = data["filter_options"]

    # col_mixed bounds should ignore NaNs and be [10, 50]
    assert filter_opts["col_mixed"]["bounds"] == [10, 50]

    # cat_mixed should ignore NaNs and count X: 2, Y: 1
    cat_vals = {item["value"]: item["count"] for item in filter_opts["cat_mixed"]["top_values"]}
    assert cat_vals == {"X": 2, "Y": 1}


def test_filter_options_high_cardinality_capping(client, make_csv):
    """Verify categorical top_values is capped (e.g. at 50) for high cardinality columns."""
    rows = ["category,val"]
    for i in range(120):
        rows.append(f"UniqueCat_{i},{i}")
    csv_content = "\n".join(rows)

    response = client.post(
        "/upload",
        files={"file": ("high_card.csv", make_csv(csv_content), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    top_values = data["filter_options"]["category"]["top_values"]

    # Should be capped at 50 to prevent unbounded payload size
    assert len(top_values) == 50
