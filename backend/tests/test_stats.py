"""Regression tests for /stats/{dataset_id} and calculate_dataset_stats().

Root cause (confirmed): boolean columns are reported as numeric by
``pd.api.types.is_numeric_dtype`` but ``DataFrame.describe()`` omits them when
other numeric columns exist, so ``desc[col]`` raised ``KeyError`` -> HTTP 500.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

from api_helpers import calculate_dataset_stats, sanitize_json_value

NUMERIC_KEYS = {"count", "mean", "std", "min", "25%", "50%", "75%", "max"}

# Optional real-data validation: set DATALENS_CALORIX_DIR to a folder containing
# the two CaloriX CSVs. When unset or files are missing, that test is skipped.
CALORIX_DIR = os.environ.get("DATALENS_CALORIX_DIR", "")
WORKING_CSV = os.path.join(CALORIX_DIR, "CaloriX_Nutrition_Dataset.csv")
CLEAN_CSV = os.path.join(CALORIX_DIR, "CaloriX_Nutrition_Dataset_Clean.csv")


def _assert_contract(stats, df):
    assert set(stats) == {
        "row_count", "column_count", "numeric_summary",
        "categorical_summary", "correlation_matrix",
    }
    assert stats["row_count"] == len(df)
    assert stats["column_count"] == len(df.columns)
    for summary in stats["numeric_summary"].values():
        assert set(summary) == NUMERIC_KEYS
    for summary in stats["categorical_summary"].values():
        assert set(summary) == {"unique_count", "top_values"}
    # Strictly RFC 8259: no NaN / Infinity tokens
    json.dumps(stats, allow_nan=False)


def _mixed_df():
    return pd.DataFrame({
        "calories": [100.0, 200.0, np.nan, 400.0],
        "qty": [1, 2, 3, 4],
        "is_vegan": [True, False, True, True],
        "constant": [5, 5, 5, 5],
        "inf_col": [1.0, np.inf, -np.inf, 2.0],
        "all_nan": [np.nan] * 4,
        "label": ["NaT", "<NA>", "x", "x"],
        "same_cat": ["a", "a", "a", "a"],
        "when": pd.to_datetime(["2026-01-01", None, "2026-01-03", "2026-01-04"]),
    })


def test_bool_columns_with_other_numerics_do_not_raise():
    df = _mixed_df()
    stats = calculate_dataset_stats(df)
    _assert_contract(stats, df)
    assert "is_vegan" in stats["numeric_summary"]
    veg = stats["numeric_summary"]["is_vegan"]
    assert veg["count"] == 4
    assert veg["mean"] == pytest.approx(0.75)
    assert veg["min"] == 0.0 and veg["max"] == 1.0
    assert "is_vegan" in stats["correlation_matrix"]


def test_stats_does_not_mutate_source_dataframe_or_drop_columns():
    df = _mixed_df()
    before = df.copy(deep=True)
    stats = calculate_dataset_stats(df)
    pd.testing.assert_frame_equal(df, before)
    assert df["is_vegan"].dtype == bool
    assert stats["column_count"] == 9


def test_all_bool_dataframe_and_nullable_boolean():
    df = pd.DataFrame({
        "a": [True, False, True],
        "b": pd.array([True, None, False], dtype="boolean"),
    })
    stats = calculate_dataset_stats(df)
    _assert_contract(stats, df)
    assert stats["numeric_summary"]["a"]["mean"] == pytest.approx(2 / 3)
    assert stats["numeric_summary"]["b"]["count"] == 2  # missing excluded


def test_constant_nonfinite_and_missing_are_json_safe_and_honest():
    stats = calculate_dataset_stats(_mixed_df())
    assert stats["numeric_summary"]["constant"]["std"] == 0.0
    assert stats["numeric_summary"]["all_nan"]["count"] == 0
    assert stats["numeric_summary"]["all_nan"]["mean"] is None
    assert stats["categorical_summary"]["same_cat"]["unique_count"] == 1
    # Correlation with constant / all-NaN columns is null-safe (0), never NaN
    assert stats["correlation_matrix"]["constant"]["calories"] == 0


def test_literal_nat_and_na_strings_survive_in_stats():
    stats = calculate_dataset_stats(_mixed_df())
    top = stats["categorical_summary"]["label"]["top_values"]
    assert top["NaT"] == 1 and top["<NA>"] == 1
    assert sanitize_json_value("NaT") == "NaT"
    assert sanitize_json_value("<NA>") == "<NA>"
    assert sanitize_json_value(pd.NaT) is None
    assert sanitize_json_value(pd.NA) is None


def test_stats_endpoint_with_bool_columns_via_upload(client):
    csv = (
        "calories,qty,is_vegan,is_halal,name\n"
        "100,1,True,False,NaT\n"
        "200,2,False,False,y\n"
        "300,3,True,True,x\n"
    )
    up = client.post("/upload", files={"file": ("bools.csv", csv.encode(), "text/csv")})
    assert up.status_code == 200
    dataset_id = up.json()["dataset_id"]

    res = client.get(f"/stats/{dataset_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["column_count"] == 5
    assert {"calories", "qty", "is_vegan", "is_halal"} <= set(body["numeric_summary"])
    assert body["numeric_summary"]["is_vegan"]["mean"] == pytest.approx(2 / 3)
    # Literal text 'NaT' is preserved. (pandas read_csv itself treats '<NA>' as a
    # missing token at ingestion; that is separate from stats/serialization.)
    assert body["categorical_summary"]["name"]["top_values"] == {"NaT": 1, "y": 1, "x": 1}


def test_stats_unexpected_failure_is_honest_500(client, monkeypatch):
    """Unexpected calculation errors must surface as an error, not fake stats."""
    import app as app_module

    up = client.post("/upload", files={"file": ("a.csv", b"x,y\n1,2\n3,4\n", "text/csv")})
    dataset_id = up.json()["dataset_id"]

    def boom(_df):
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "calculate_dataset_stats", boom)
    res = client.get(f"/stats/{dataset_id}")
    assert res.status_code == 500
    assert "numeric_summary" not in res.json()


def test_stats_unknown_dataset_id_is_404(client):
    assert client.get("/stats/does-not-exist").status_code == 404


@pytest.mark.skipif(
    not (CALORIX_DIR and os.path.isfile(WORKING_CSV) and os.path.isfile(CLEAN_CSV)),
    reason="DATALENS_CALORIX_DIR not set or CaloriX CSV files not available (optional)",
)
def test_real_calorix_datasets_stats_through_api(client):
    shared = {}
    for path in (WORKING_CSV, CLEAN_CSV):
        with open(path, "rb") as fh:
            up = client.post(
                "/upload",
                files={"file": (os.path.basename(path), fh, "text/csv")},
            )
        assert up.status_code == 200
        df = pd.read_csv(path)
        res = client.get(f"/stats/{up.json()['dataset_id']}")
        assert res.status_code == 200, res.text
        body = res.json()
        _assert_contract(body, df)
        assert body["column_count"] == len(df.columns)
        shared[os.path.basename(path)] = body

    assert shared["CaloriX_Nutrition_Dataset.csv"]["column_count"] == 23
    clean = shared["CaloriX_Nutrition_Dataset_Clean.csv"]
    assert clean["column_count"] == 43
    for flag in ("is_vegan", "is_vegetarian", "is_halal"):
        assert flag in clean["numeric_summary"]

    # Shared columns' stats are unaffected
    base = shared["CaloriX_Nutrition_Dataset.csv"]
    for col, summary in base["numeric_summary"].items():
        if col in clean["numeric_summary"]:
            assert clean["numeric_summary"][col] == summary
