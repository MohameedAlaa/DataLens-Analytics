import pytest
import pandas as pd
import numpy as np
from services.analytics import AnalyticsEngine, get_analytics_engine
from services.ai.rag.query_router import QueryRouter

def test_analytics_engine_instantiation():
    engine = get_analytics_engine()
    assert isinstance(engine, AnalyticsEngine)

def test_query_router_identifies_analytics():
    router = QueryRouter()
    
    # Should flag as analytics
    res = router.route("What is the average revenue?")
    assert res["needs_stats"] is True
    assert res["reason"] == "analytics"
    
    # "country" should not trigger "count"
    res = router.route("Which country is this from?")
    assert res["needs_stats"] is False
    assert res["needs_retrieval"] is True
    assert res["reason"] == "semantic"
    
    # "%" should trigger stats
    res = router.route("What % of users are from Egypt?")
    assert res["needs_stats"] is True
    assert res["reason"] == "analytics"

def test_analytics_engine_mean():
    engine = get_analytics_engine()
    df = pd.DataFrame({"revenue": [100, 200, 300, 400]})
    
    res = engine.analyze("What is the average revenue?", df)
    assert res.get("operation") == "mean"
    assert res.get("column") == "revenue"
    assert res.get("value") == 250.0
    
def test_analytics_engine_correlation():
    engine = get_analytics_engine()
    df = pd.DataFrame({
        "temperature": [20, 25, 30, 35, 40],
        "ice_cream_sales": [100, 150, 200, 250, 300]
    })
    
    res = engine.analyze("Is there a correlation between temperature and ice_cream_sales?", df)
    assert res.get("operation") == "correlation"
    assert res.get("value") == 1.0
    assert "error" not in res

def test_analytics_engine_percentage():
    engine = get_analytics_engine()
    df = pd.DataFrame({
        "country": ["Egypt", "USA", "Egypt", "UK"],
        "revenue": [100, 200, 300, 400]
    })
    
    res = engine.analyze("What percentage of customers are from Egypt?", df)
    assert res.get("operation") == "percentage"
    assert res.get("column") == "country"
    assert res.get("value") == 50.0

def test_analytics_engine_empty_df():
    engine = get_analytics_engine()
    df = pd.DataFrame()
    res = engine.analyze("average revenue", df)
    assert "error" in res

def test_analytics_engine_non_numeric():
    engine = get_analytics_engine()
    df = pd.DataFrame({"country": ["Egypt", "USA"]})
    res = engine.analyze("What is the average country?", df)
    assert "error" in res
    assert res["operation"] == "mean"

def test_analytics_engine_count_global():
    engine = get_analytics_engine()
    df = pd.DataFrame({"revenue": [100, 200, 300]})
    res = engine.analyze("How many rows?", df)
    assert res["operation"] == "count"
    assert res["value"] == 3
