import pytest
import pandas as pd
import uuid
import io
import asyncio
from fastapi.testclient import TestClient

from app import app
from services.ai.rag.ingestion_pipeline import IngestionPipeline
from services.data.vector_store import get_vector_store
from services.ai.embeddings.embedding_service import get_embedding_service
from services.ai.rag.llm_service import RagLLMService

# A mock LLM to prevent real API calls but return what RAG gave it
class VerificationMockLLM(RagLLMService):
    def __init__(self):
        self.last_prompt = ""
        
    async def generate(self, prompt: str, **kwargs) -> str:
        self.last_prompt = prompt
        return "MOCKED_ANSWER_BASED_ON_RAG"

@pytest.fixture
def mock_llm_service(monkeypatch):
    mock_llm = VerificationMockLLM()
    monkeypatch.setattr("api_helpers.build_llm_service", lambda: mock_llm)
    # Remove the global generate_chat_response_async mock if it's there
    from api_helpers import generate_chat_response_async
    monkeypatch.setattr("app.generate_chat_response_async", generate_chat_response_async)
    return mock_llm



@pytest.mark.asyncio
async def test_cross_dataset_isolation_and_citations(client, mock_llm_service):
    """Test datasets cannot leak vectors into each other, and citations are perfectly correct."""
    
    # Dataset A (Sales A)
    csv_a = "name,country,value\nAlice,Egypt,100\nBob,Egypt,200\nCharlie,USA,300"
    res_a = client.post("/upload", files={"file": ("sales_a.csv", io.BytesIO(csv_a.encode()), "text/csv")})
    assert res_a.status_code == 200
    dataset_id_a = res_a.json()["dataset_id"]
    
    # Dataset B (Sales B)
    csv_b = "name,country,value\nJohn,Germany,900\nSarah,France,800\nMike,Japan,700"
    res_b = client.post("/upload", files={"file": ("sales_b.csv", io.BytesIO(csv_b.encode()), "text/csv")})
    assert res_b.status_code == 200
    dataset_id_b = res_b.json()["dataset_id"]

    # Run ingestion synchronously for the tests


    # Query Dataset A
    res_chat_a = client.post("/chat", json={
        "question": "What is the value for Bob?",
        "dataset_id": dataset_id_a
    })
    assert res_chat_a.status_code == 200
    data_a = res_chat_a.json()
    assert "answer" in data_a
    assert "citations" in data_a
    citations_a = data_a["citations"]
    assert len(citations_a) > 0
    
    # Verify Citation Correctness
    for c in citations_a:
        assert c["dataset_id"] == dataset_id_a
        assert c["filename"] == "sales_a.csv"
        assert "chunk_id" in c
        assert "row_start" in c and "row_end" in c
        # Ensure NO data from Dataset B is retrieved
        assert "John" not in c["text"]
        assert "Germany" not in c["text"]
        
    # Query Dataset B
    res_chat_b = client.post("/chat", json={
        "question": "What is the value for John?",
        "dataset_id": dataset_id_b
    })
    data_b = res_chat_b.json()
    citations_b = data_b["citations"]
    for c in citations_b:
        assert c["dataset_id"] == dataset_id_b
        assert c["filename"] == "sales_b.csv"
        # Ensure NO data from Dataset A is retrieved
        assert "Alice" not in c["text"]
        assert "Bob" not in c["text"]

@pytest.mark.asyncio
async def test_multiline_csv_chunking_and_row_boundaries_e2e(client, mock_llm_service):
    """Test that multiline CSV fields don't break row calculation (E2E API)."""
    csv_content = 'col1,col2,col3\nA,"hello\nworld",10\nB,"another\nmultiline\ndescription",20\nC,normal,30'
    res = client.post("/upload", files={"file": ("multi.csv", io.BytesIO(csv_content.encode()), "text/csv")})
    dataset_id = res.json()["dataset_id"]
    
    res_chat = client.post("/chat", json={
        "question": "Find multiline description",
        "dataset_id": dataset_id
    })
    citations = res_chat.json()["citations"]
    
    assert any("another" in c["text"] and "multiline" in c["text"] for c in citations)
    for c in citations:
        assert c["row_start"] <= c["row_end"]
        assert c["row_end"] <= 3

@pytest.mark.asyncio
async def test_multiline_csv_chunking_and_row_boundaries_direct(client, mock_llm_service):
    """Test that multiline CSV fields don't break row calculation (Direct RAG retrieval bypasses router)."""
    csv_content = 'col1,col2,col3\nA,"hello\nworld",10\nB,"another\nmultiline\ndescription",20\nC,normal,30'
    res = client.post("/upload", files={"file": ("multi2.csv", io.BytesIO(csv_content.encode()), "text/csv")})
    dataset_id = res.json()["dataset_id"]
    
    from api_helpers import build_retriever, build_citation_builder
    retriever = build_retriever()
    chunks = retriever.retrieve(query="multiline description", dataset_id=dataset_id, top_k=5)
    
    citation_builder = build_citation_builder()
    citations = citation_builder.build(chunks)
    
    assert len(citations) > 0
    assert any("another" in c["text"] and "multiline" in c["text"] for c in citations)
    for c in citations:
        assert c["row_start"] <= c["row_end"]
        assert c["row_end"] <= 3

@pytest.mark.asyncio
async def test_idempotency_and_duplicate_prevention(client, mock_llm_service):
    """Test that running ingestion twice doesn't duplicate vectors."""
    csv_content = "name,value\nA,1\nB,2"
    res = client.post("/upload", files={"file": ("dup.csv", io.BytesIO(csv_content.encode()), "text/csv")})
    dataset_id = res.json()["dataset_id"]
    # Ingestion already happened during upload
    store = get_vector_store()
    count_1 = store.count_vectors(dataset_id)
    assert count_1 > 0
    
    # Run ingestion again manually to test idempotency
    from services.ai.rag.ingestion_pipeline import ingestion_pipeline
    import pandas as pd
    
    df = pd.read_csv(io.BytesIO(csv_content.encode()))
    ingestion_pipeline.run_ingestion(dataset_id, df, "dup.csv", app.state.dataset_manager)
    count_2 = store.count_vectors(dataset_id)
    
    assert count_1 == count_2  # Vector count should not increase

@pytest.mark.asyncio
async def test_rag_fallback_on_missing_index(client, mock_llm_service):
    """Test that querying a missing index gracefully falls back to basic chat."""
    csv_content = "name,value\nA,1\nB,2"
    res = client.post("/upload", files={"file": ("missing.csv", io.BytesIO(csv_content.encode()), "text/csv")})
    dataset_id = res.json()["dataset_id"]
    
    # Manually delete the index to simulate a missing index
    store = get_vector_store()
    store.delete_dataset(dataset_id)
    

    res_chat = client.post("/chat", json={
        "question": "What is the value of A?",
        "dataset_id": dataset_id
    })
    
    assert res_chat.status_code == 200
    data = res_chat.json()
    assert "answer" in data
    # No citations because RAG failed gracefully
    assert data.get("citations") == []

@pytest.mark.asyncio
async def test_failure_injection_during_ingestion(client, monkeypatch):
    """Test that ingestion errors lead to FAILED state."""
    csv_content = "name,value\nA,1\nB,2"
    # Inject a failure in chunking before upload
    def fake_chunk(*args, **kwargs):
        raise ValueError("Simulated chunking failure")
    
    from services.ai.rag.chunker import TokenRowChunker
    monkeypatch.setattr(TokenRowChunker, "chunk", fake_chunk)
    
    res = client.post("/upload", files={"file": ("fail.csv", io.BytesIO(csv_content.encode()), "text/csv")})
    dataset_id = res.json()["dataset_id"]

    
    # Verify state is FAILED
    dm = app.state.dataset_manager
    meta = dm.get_metadata(dataset_id)
    assert meta["indexing_status"] == "FAILED"
