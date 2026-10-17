"""Regression tests for PERF-01: Bounded and paginated filter responses.

Verifies:
1. Small filtered datasets return correct results, total, and metadata.
2. Bounded pagination with `limit` and `offset` via JSON body and query params.
3. Deterministic pagination across page boundaries without records shifting.
4. Out-of-range offset returns empty records with accurate total and has_more=False.
5. Strict validation on invalid limit/offset values (422 response).
6. Safety ceiling capping when records exceed max limit without limit specified.
7. Dataset isolation during filtering.
"""

import pytest
import pandas as pd


def test_filter_small_dataset_pagination_metadata(client, make_csv):
    """Verify small filtered dataset returns complete records with pagination metadata."""
    upload_res = client.post(
        "/upload",
        files={"file": ("small.csv", make_csv("item,price\nA,10\nB,20\nC,30"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post("/filter", json={"dataset_id": dataset_id, "filters": {}})
    assert res.status_code == 200
    data = res.json()

    assert data["row_count"] == 3
    assert data["total"] == 3
    assert len(data["filtered_data"]) == 3
    assert data["has_more"] is False
    assert data["offset"] == 0
    assert data["limit"] == 3
    assert data["page"] == 1
    assert data["total_pages"] == 1


def test_filter_explicit_limit_and_offset_json_body(client, make_csv):
    """Verify pagination with limit and offset slices correctly."""
    rows = "\n".join([f"{i},cat_{i % 3}" for i in range(25)])
    upload_res = client.post(
        "/upload",
        files={"file": ("items.csv", make_csv(f"id,cat\n{rows}"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    # Page 1: limit 10, offset 0
    res_p1 = client.post(
        "/filter",
        json={"dataset_id": dataset_id, "filters": {}, "limit": 10, "offset": 0},
    )
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["total"] == 25
    assert data_p1["row_count"] == 25
    assert len(data_p1["filtered_data"]) == 10
    assert data_p1["has_more"] is True
    assert data_p1["page"] == 1
    assert data_p1["total_pages"] == 3
    p1_ids = [r["id"] for r in data_p1["filtered_data"]]
    assert p1_ids == list(range(10))

    # Page 2: limit 10, offset 10
    res_p2 = client.post(
        "/filter",
        json={"dataset_id": dataset_id, "filters": {}, "limit": 10, "offset": 10},
    )
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["filtered_data"]) == 10
    assert data_p2["has_more"] is True
    assert data_p2["page"] == 2
    p2_ids = [r["id"] for r in data_p2["filtered_data"]]
    assert p2_ids == list(range(10, 20))

    # Page 3: limit 10, offset 20
    res_p3 = client.post(
        "/filter",
        json={"dataset_id": dataset_id, "filters": {}, "limit": 10, "offset": 20},
    )
    assert res_p3.status_code == 200
    data_p3 = res_p3.json()
    assert len(data_p3["filtered_data"]) == 5
    assert data_p3["has_more"] is False
    assert data_p3["page"] == 3
    p3_ids = [r["id"] for r in data_p3["filtered_data"]]
    assert p3_ids == list(range(20, 25))

    # Verify no records shifted or duplicated
    all_retrieved = p1_ids + p2_ids + p3_ids
    assert all_retrieved == list(range(25))


def test_filter_pagination_via_query_parameters(client, make_csv):
    """Verify limit and offset can also be passed via URL query parameters."""
    rows = "\n".join([f"{i}" for i in range(15)])
    upload_res = client.post(
        "/upload",
        files={"file": ("nums.csv", make_csv(f"num\n{rows}"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post(
        f"/filter?limit=5&offset=5",
        json={"dataset_id": dataset_id, "filters": {}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 15
    assert len(data["filtered_data"]) == 5
    assert data["offset"] == 5
    assert data["limit"] == 5
    assert data["page"] == 2
    assert [r["num"] for r in data["filtered_data"]] == list(range(5, 10))


def test_filter_out_of_range_offset(client, make_csv):
    """Verify out-of-range offset returns empty records array with accurate total and has_more=False."""
    upload_res = client.post(
        "/upload",
        files={"file": ("test.csv", make_csv("val\n1\n2\n3"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post(
        "/filter",
        json={"dataset_id": dataset_id, "filters": {}, "limit": 10, "offset": 100},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert data["row_count"] == 3
    assert data["filtered_data"] == []
    assert data["has_more"] is False
    assert data["offset"] == 100


def test_filter_validation_invalid_limit_and_offset(client, make_csv):
    """Verify invalid limit (<1 or >50000) or negative offset triggers 422 Unprocessable Entity."""
    upload_res = client.post(
        "/upload",
        files={"file": ("test.csv", make_csv("val\n1\n2"), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    # limit = 0
    res_zero = client.post("/filter", json={"dataset_id": dataset_id, "filters": {}, "limit": 0})
    assert res_zero.status_code == 422

    # limit < 0
    res_neg = client.post("/filter", json={"dataset_id": dataset_id, "filters": {}, "limit": -5})
    assert res_neg.status_code == 422

    # limit > 50000
    res_huge = client.post("/filter", json={"dataset_id": dataset_id, "filters": {}, "limit": 50001})
    assert res_huge.status_code == 422

    # offset < 0
    res_neg_off = client.post("/filter", json={"dataset_id": dataset_id, "filters": {}, "offset": -1})
    assert res_neg_off.status_code == 422


def test_filter_semantics_preserved_with_pagination(client, make_csv):
    """Verify that filtering semantics (numeric range + categorical) apply before pagination."""
    csv_data = "score,category\n" + "\n".join([f"{i},{'Alpha' if i % 2 == 0 else 'Beta'}" for i in range(100)])
    upload_res = client.post(
        "/upload",
        files={"file": ("data.csv", make_csv(csv_data), "text/csv")},
    )
    dataset_id = upload_res.json()["dataset_id"]

    # Filter: score >= 50 and category == 'Alpha'
    # Scores 50..99 with even numbers -> 25 matches: 50, 52, 54, ..., 98
    filters = {
        "score": {">=": 50},
        "category": ["Alpha"],
    }

    res = client.post(
        "/filter",
        json={"dataset_id": dataset_id, "filters": filters, "limit": 10, "offset": 0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 25
    assert len(data["filtered_data"]) == 10
    assert all(r["category"] == "Alpha" and r["score"] >= 50 for r in data["filtered_data"])
    assert data["filtered_data"][0]["score"] == 50
    assert data["filtered_data"][9]["score"] == 68


def test_filter_dataset_isolation(client, make_csv):
    """Verify dataset isolation is strictly maintained across filter requests."""
    res1 = client.post("/upload", files={"file": ("ds1.csv", make_csv("name\nAlice"), "text/csv")})
    res2 = client.post("/upload", files={"file": ("ds2.csv", make_csv("name\nBob"), "text/csv")})
    id1 = res1.json()["dataset_id"]
    id2 = res2.json()["dataset_id"]

    f1 = client.post("/filter", json={"dataset_id": id1, "filters": {}, "limit": 10}).json()
    f2 = client.post("/filter", json={"dataset_id": id2, "filters": {}, "limit": 10}).json()

    assert len(f1["filtered_data"]) == 1
    assert f1["filtered_data"][0]["name"] == "Alice"
    assert len(f2["filtered_data"]) == 1
    assert f2["filtered_data"][0]["name"] == "Bob"


def test_filter_safety_ceiling_truncation_when_unspecified():
    """Verify that when matching records exceed max_filter_limit without explicit limit,
    the response bounds to max_filter_limit, sets has_more=True and is_truncated=True,
    and accurately reports total matching count without silently dropping records.
    """
    from api_helpers import apply_filters

    df = pd.DataFrame({"id": range(55000), "val": ["x"] * 55000})
    result = apply_filters(df, filters={})

    assert result["total"] == 55000
    assert result["row_count"] == 55000
    assert len(result["filtered_data"]) == 50000
    assert result["has_more"] is True
    assert result["is_truncated"] is True
    assert result["limit"] == 50000
    assert result["offset"] == 0


def test_filter_never_silently_drops_records(client, make_csv):
    """Verify that paginated retrieval across all pages returns 100% of matching records
    with exact sequence preservation and zero silent record loss.
    """
    total_records = 32
    rows = "\n".join([f"{i},value_{i}" for i in range(total_records)])
    upload_res = client.post(
        "/upload",
        files={"file": ("all_items.csv", make_csv(f"id,val\n{rows}"), "text/csv")},
    )
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    page_size = 7
    offset = 0
    collected_ids = []

    while True:
        res = client.post(
            "/filter",
            json={"dataset_id": dataset_id, "filters": {}, "limit": page_size, "offset": offset},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == total_records

        records = data["filtered_data"]
        collected_ids.extend([r["id"] for r in records])

        if not data["has_more"]:
            break
        offset += page_size

    assert collected_ids == list(range(total_records))
    assert len(collected_ids) == total_records
