import pytest
from fastapi.testclient import TestClient
from app import app
from services.analytics.analytics_engine import get_analytics_engine
from services.ai.rag.llm_service import RagLLMService

client = TestClient(app)

class DummyLLMService(RagLLMService):
    async def generate(self, prompt: str, **kwargs) -> str:
        return prompt
    async def generate_json(self, prompt: str, schema: dict, **kwargs) -> dict:
        return {"mocked": True}

@pytest.fixture(autouse=True)
def override_llm_service(monkeypatch):
    monkeypatch.setattr("api_helpers.build_llm_service", lambda: DummyLLMService())

def test_integration_analytics_exact_numeric(make_csv):
    """Verify exact numeric calculations (count, sum, mean, median, min, max, std, variance) against a known set."""
    csv_data = "id,value\n1,10\n2,20\n3,30\n4,40\n5,50"
    upload_res = client.post("/upload", files={"file": ("data.csv", csv_data, "text/csv")})
    assert upload_res.status_code == 200
    dataset_id = upload_res.json()["dataset_id"]

    tests = [
        ("What is the count of value?", 5),
        ("What is the total value?", 150),
        ("What is the average value?", 30),
        ("What is the median value?", 30),
        ("What is the minimum value?", 10),
        ("What is the highest value?", 50),
    ]

    for q, expected in tests:
        res = client.post("/chat", json={"dataset_id": dataset_id, "question": q, "history": []})
        data = res.json()
        assert "answer" in data
        assert "analytics" in data, f"Analytics result missing for {q}"
        assert data["analytics"]["value"] == expected
        assert str(expected) in data["answer"], f"Expected {expected} in prompt for {q} but got {data['answer']}"

def test_integration_analytics_std_var(make_csv):
    """Verify std/variance ddof=1 for sample stats."""
    csv_data = "id,value\n1,10\n2,20\n3,30\n4,40\n5,50"
    upload_res = client.post("/upload", files={"file": ("data.csv", csv_data, "text/csv")})
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post("/chat", json={"dataset_id": dataset_id, "question": "What is the standard deviation of value?", "history": []})
    assert "15.811" in str(res.json()["answer"])
    assert "analytics" in res.json()

    res = client.post("/chat", json={"dataset_id": dataset_id, "question": "What is the variance of value?", "history": []})
    assert "250.0" in str(res.json()["answer"])
    assert "analytics" in res.json()

def test_integration_analytics_filter_aware(make_csv):
    """Prove filter-aware analytics (filtering the DataFrame before aggregation)."""
    csv_data = "id,value\n1,100\n2,200\n3,300\n4,400"
    upload_res = client.post("/upload", files={"file": ("data.csv", csv_data, "text/csv")})
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post("/chat", json={
        "dataset_id": dataset_id,
        "question": "What is the average value?",
        "filters": {"value": {">": 200}},
        "history": []
    })
    # Mean of 300 and 400 is 350
    assert "350" in str(res.json()["answer"])
    assert "analytics" in res.json()

def test_integration_ambiguous_column_resolution(make_csv):
    """Implement unambiguous column resolution (or explicit errors)."""
    csv_data = "revenue,revenue_total,revenue_usd\n100,200,300\n100,200,300"
    upload_res = client.post("/upload", files={"file": ("data.csv", csv_data, "text/csv")})
    dataset_id = upload_res.json()["dataset_id"]

    # Unambiguous exact match for 'revenue'
    res = client.post("/chat", json={"dataset_id": dataset_id, "question": "What is the average revenue?", "history": []})
    assert "100" in str(res.json()["answer"]), res.json()
    assert "analytics" in res.json()

    # Ambiguous - user says "rev" which is not an exact match but substring of all
    res = client.post("/chat", json={"dataset_id": dataset_id, "question": "What is the average rev?", "history": []})
    assert "analytics" not in res.json() # Should not be deterministically resolved

def test_integration_grouped_analytics(make_csv):
    """Verify grouped analytics logic (e.g., 'Which country has the highest sales?')."""
    csv_data = "country,sales\nUSA,1000\nUSA,700\nEgypt,1200"
    upload_res = client.post("/upload", files={"file": ("data.csv", csv_data, "text/csv")})
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post("/chat", json={"dataset_id": dataset_id, "question": "Which country has the highest sales?", "history": []})
    assert "USA" in str(res.json()["answer"])
    assert "analytics" in res.json()
    
def test_edge_cases(make_csv):
    """Handle edge cases (NaN, Inf, empty sets, non-numeric)."""
    csv_data = "id,val\n1,NaN\n2,Inf\n3,10"
    upload_res = client.post("/upload", files={"file": ("data.csv", csv_data, "text/csv")})
    dataset_id = upload_res.json()["dataset_id"]

    res = client.post("/chat", json={"dataset_id": dataset_id, "question": "What is the maximum val?", "history": []})
    assert "10" in str(res.json()["answer"])
    assert "analytics" in res.json()


def test_strict_json_serialization(make_csv):
    """Ensure all analytics outputs strictly conform to JSON standards (allow_nan=False)."""
    import json
    import numpy as np
    import pandas as pd
    
    eng = get_analytics_engine()
    
    # 1. Zero denominator
    df_zero = pd.DataFrame({"a": [10], "b": [0]})
    res_zero = eng.analyze("What is the percentage of a in b?", df_zero)
    serialized_zero = json.dumps(res_zero, allow_nan=False)
    assert "error" in json.loads(serialized_zero)
    
    # 2. NaN and None
    df_nan = pd.DataFrame({"val": [10.0, np.nan, None, 20.0]})
    res_nan = eng.analyze("What is the mean val?", df_nan)
    serialized_nan = json.dumps(res_nan, allow_nan=False)
    assert json.loads(serialized_nan)["value"] == 15.0

    # 3. Positive & Negative Infinity
    df_inf = pd.DataFrame({"val": [1.0, float("inf"), float("-inf"), 3.0]})
    res_inf = eng.analyze("What is the mean val?", df_inf)
    serialized_inf = json.dumps(res_inf, allow_nan=False)
    assert json.loads(serialized_inf)["value"] == 2.0

    # 4. Correlation with constant column
    df_const = pd.DataFrame({"x": [5, 5, 5], "y": [1, 2, 3]})
    res_const = eng.analyze("What is the correlation between x and y?", df_const)
    serialized_const = json.dumps(res_const, allow_nan=False)
    assert "error" in json.loads(serialized_const)

    # 5. Full FastAPI response through /chat
    csv_data = "id,val\n1,NaN\n2,Inf\n3,10"
    upload_res = client.post("/upload", files={"file": ("strict.csv", csv_data, "text/csv")})
    dataset_id = upload_res.json()["dataset_id"]
    res_chat = client.post("/chat", json={"dataset_id": dataset_id, "question": "What is the maximum val?", "history": []})
    assert res_chat.status_code == 200
    # Strict validation of actual HTTP response content:
    json.dumps(res_chat.json(), allow_nan=False)


def test_analytics_bypasses_rag_retrieval(monkeypatch, make_csv):
    """Prove AnalyticsEngine executes and bypasses RAG retrieval for statistical queries."""
    from services.ai.rag.retriever import Retriever
    
    retriever_called = []
    original_retrieve = Retriever.retrieve

    def spy_retrieve(self, *args, **kwargs):
        retriever_called.append((args, kwargs))
        return original_retrieve(self, *args, **kwargs)

    monkeypatch.setattr(Retriever, "retrieve", spy_retrieve)

    # Case A: "Which country has the highest sales?"
    csv_sales = "country,sales\nUSA,1000\nUSA,700\nEgypt,1200"
    upload_a = client.post("/upload", files={"file": ("sales.csv", csv_sales, "text/csv")})
    dataset_id_a = upload_a.json()["dataset_id"]

    retriever_called.clear()
    res_a = client.post("/chat", json={
        "dataset_id": dataset_id_a,
        "question": "Which country has the highest sales?",
        "history": []
    })
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert "analytics" in data_a
    assert data_a["analytics"]["group_value"] == "USA"
    assert data_a["analytics"]["value"] == 1700
    assert len(retriever_called) == 0, "Retriever was called unexpectedly during country sales query!"

    # Case B: "Which account has the highest balance?"
    csv_accounts = "account,balance\nChecking,500.0\nSavings,2500.0\nInvestment,1500.0"
    upload_b = client.post("/upload", files={"file": ("accounts.csv", csv_accounts, "text/csv")})
    dataset_id_b = upload_b.json()["dataset_id"]

    retriever_called.clear()
    res_b = client.post("/chat", json={
        "dataset_id": dataset_id_b,
        "question": "Which account has the highest balance?",
        "history": []
    })
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert "analytics" in data_b
    assert data_b["analytics"]["group_value"] == "Savings"
    assert data_b["analytics"]["value"] == 2500.0
    assert len(retriever_called) == 0, "Retriever was called unexpectedly during account balance query!"

