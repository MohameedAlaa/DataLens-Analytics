import pytest
import pandas as pd
from services.analytics.analytics_engine import get_analytics_engine
from services.ai.rag.query_router import QueryRouter
import math

def test_deterministic_calcs():
    df = pd.DataFrame({"val": [10, 20, 30, 40, 50]})
    engine = get_analytics_engine()
    
    assert engine.analyze("count of val", df)["value"] == 5
    assert engine.analyze("sum of val", df)["value"] == 150
    assert engine.analyze("mean of val", df)["value"] == 30.0
    assert engine.analyze("median of val", df)["value"] == 30.0
    assert engine.analyze("min of val", df)["value"] == 10
    assert engine.analyze("max of val", df)["value"] == 50

def test_routing_boundaries():
    router = QueryRouter()
    assert router.route("How many users are there?")["needs_stats"] is True
    assert router.route("What is the average salary?")["needs_stats"] is True
    assert router.route("Which country has the highest sales?")["needs_stats"] is True
    assert router.route("Which country has the most customers?")["needs_stats"] is True
    
    res = router.route("Tell me about this country.")
    assert not res["needs_stats"]
    
    res = router.route("Which account has the highest balance?")
    assert res["needs_stats"] is True # highest -> max (needs_stats=True)
    
    res = router.route("Hello")
    assert not res["needs_stats"]
    assert not res["needs_retrieval"]

def test_ambiguous_columns():
    df = pd.DataFrame({
        "revenue": [1],
        "revenue_total": [2],
        "revenue_usd": [3]
    })
    engine = get_analytics_engine()
    res = engine.analyze("What is the average revenue?", df)
    # The logic sorts by length descending. It'll check 'revenue_total', 'revenue_usd', then 'revenue'.
    # 'revenue_total' is NOT in 'What is the average revenue?'.
    # 'revenue_usd' is NOT in 'What is the average revenue?'.
    # 'revenue' IS in the query. So it correctly picks 'revenue'.
    assert "error" not in res
    assert res["column"] == "revenue"

def test_non_numeric():
    df = pd.DataFrame({"name": ["Alice", "Bob"]})
    engine = get_analytics_engine()
    res = engine.analyze("What is the average name?", df)
    assert "error" in res

def test_missing_column():
    df = pd.DataFrame({"name": ["Alice", "Bob"]})
    engine = get_analytics_engine()
    res = engine.analyze("What is the average missing_column?", df)
    assert "error" in res

def test_nan_infinity_json():
    df = pd.DataFrame({"val": [10, pd.NA, float('inf')]})
    engine = get_analytics_engine()
    res = engine.analyze("mean of val", df)
    # the safe_float function should handle this
    val = res.get("value")
    assert val is None or not math.isinf(val)
    if "error" in res:
        pass # either error or null value is fine, but NO raw exception

def test_zero_denominator():
    df = pd.DataFrame({"val": [pd.NA, pd.NA]})
    engine = get_analytics_engine()
    res = engine.analyze("mean val", df)
    assert "error" in res

def test_constant_correlation():
    df = pd.DataFrame({"x": [1, 1, 1], "y": [2, 3, 4]})
    engine = get_analytics_engine()
    res = engine.analyze("correlation x y", df)
    assert "error" in res

def test_percentage():
    df = pd.DataFrame({"country": ["Egypt", "USA", "Egypt"]})
    engine = get_analytics_engine()
    res = engine.analyze("percentage of customers from Egypt", df)
    assert res["operation"] == "percentage"
    assert round(res["value"], 2) == 66.67
