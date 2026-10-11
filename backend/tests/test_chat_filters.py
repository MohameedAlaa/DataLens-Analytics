from fastapi.testclient import TestClient
from app import app

import pandas as pd

client = TestClient(app)

def test_chat_filter_aware_analytics(mock_ai_response):
    # Setup test dataset
    manager = app.state.dataset_manager
    df = pd.DataFrame({
        "revenue": [100, 200, 300, 400],
        "category": ["A", "A", "B", "B"]
    })
    manager.register_dataset(
        df=df,
        filename="sales.csv",
        dataset_id="test-filter-dataset"
    )
    manager.update_indexing_status("test-filter-dataset", "READY")

    # Query with filter
    payload = {
        "dataset_id": "test-filter-dataset",
        "question": "What is the average revenue?",
        "filters": {
            "revenue": {"min": 200}
        },
        "history": []
    }

    response = client.post("/chat", json=payload)
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    data = response.json()
    
    assert data["response"] == "Mocked AI answer about dataset."

    # Query without filter
    payload_no_filter = {
        "dataset_id": "test-filter-dataset",
        "question": "What is the average revenue?",
        "history": []
    }
    response2 = client.post("/chat", json=payload_no_filter)
    data2 = response2.json()
    assert data2["response"] == "Mocked AI answer about dataset."
