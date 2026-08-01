"""Unit tests for the new scalable modular AI architecture.

Tests DocumentLoader, EmbeddingService, VectorStore, LLMService, ChatMemory, and InsightEngine.
"""

import pytest
import pandas as pd

from services import (
    Document,
    Chunk,
    DatasetDocumentLoader,
    MockEmbeddingService,
    InMemoryVectorStore,
    MockLLMService,
    SlidingWindowChatMemory,
    InsightEngine,
)


def test_document_loader():
    """Test DatasetDocumentLoader loading and chunking dataframes."""
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    loader = DatasetDocumentLoader()

    # Load DataFrame as Document
    docs = loader.load(df, dataset_id="test_doc_1", filename="users.csv")
    assert len(docs) == 1
    assert docs[0].doc_id == "test_doc_1"
    assert "users.csv" in docs[0].content
    assert docs[0].metadata["row_count"] == 2

    # Chunk Document (using small chunk size for testing)
    chunks = loader.chunk(docs, chunk_size=1, overlap=0)
    # The document has header info (lines 0..3) + data rows
    assert len(chunks) >= 2
    assert chunks[0].doc_id == "test_doc_1"
    assert "test_doc_1_chunk_0" in chunks[0].chunk_id
    assert "start_line" in chunks[0].metadata


@pytest.mark.asyncio
async def test_embedding_service():
    """Test MockEmbeddingService vector dimensions and unit length normalization."""
    embedder = MockEmbeddingService(dimension=64)
    assert embedder.dimension == 64

    # Embed single text string
    vec = await embedder.embed_text("sample data line")
    assert len(vec) == 64
    # Vector should be L2 unit length (within floating point precision)
    norm = sum(x * x for x in vec)
    assert abs(norm - 1.0) < 1e-4

    # Embed chunk objects in-place
    chunk = Chunk(chunk_id="c1", doc_id="d1", text="some dataset text")
    assert chunk.embedding is None
    await embedder.embed_chunks([chunk])
    assert chunk.embedding is not None
    assert len(chunk.embedding) == 64


@pytest.mark.asyncio
async def test_vector_store():
    """Test InMemoryVectorStore indexing and cosine similarity search."""
    store = InMemoryVectorStore()
    
    # Create mock chunks with known embeddings
    chunk_1 = Chunk(chunk_id="chunk_1", doc_id="doc_A", text="apples are red")
    chunk_1.embedding = [1.0, 0.0]
    
    chunk_2 = Chunk(chunk_id="chunk_2", doc_id="doc_A", text="bananas are yellow")
    chunk_2.embedding = [0.0, 1.0]

    # Add chunks to index
    added = await store.add_chunks([chunk_1, chunk_2])
    assert added == 2

    # Query vector close to [1.0, 0.0] (apples)
    results = await store.search(query_vector=[0.9, 0.1], top_k=1)
    assert len(results) == 1
    assert results[0].chunk.chunk_id == "chunk_1"
    assert results[0].score > 0.8

    # Query vector close to [0.0, 1.0] (bananas)
    results2 = await store.search(query_vector=[0.1, 0.9], top_k=1)
    assert len(results2) == 1
    assert results2[0].chunk.chunk_id == "chunk_2"

    # Delete by doc_id
    deleted = await store.delete_by_doc_id("doc_A")
    assert deleted == 2
    results3 = await store.search(query_vector=[1.0, 0.0], top_k=1)
    assert len(results3) == 0


@pytest.mark.asyncio
async def test_llm_service():
    """Test MockLLMService generating completion response."""
    llm = MockLLMService(default_response="Simulated AI response.")
    response = await llm.generate_response(prompt="Hello", system_prompt="Sys")
    assert response == "Simulated AI response."


def test_chat_memory():
    """Test SlidingWindowChatMemory message appending and sliding window turn eviction."""
    memory = SlidingWindowChatMemory(default_max_turns=2)
    session = "session_x"

    # Add 3 turns (6 messages)
    memory.add_message(session, "user", "turn 1")
    memory.add_message(session, "assistant", "reply 1")
    
    memory.add_message(session, "user", "turn 2")
    memory.add_message(session, "assistant", "reply 2")

    memory.add_message(session, "user", "turn 3")
    memory.add_message(session, "assistant", "reply 3")

    # Bounded to max 2 turns (last 2 messages or last 4 messages if turn is user+assistant pair)
    # get_history bounds messages count by max_turns parameter directly
    history = memory.get_history(session, max_turns=3)
    assert len(history) == 3
    assert history[0]["content"] == "reply 2"
    assert history[1]["content"] == "turn 3"
    assert history[2]["content"] == "reply 3"

    prompt = memory.format_history_prompt(session, max_turns=2)
    assert "User: turn 3" in prompt
    assert "Assistant: reply 3" in prompt
    assert "turn 1" not in prompt


@pytest.mark.asyncio
async def test_insight_engine_facade():
    """Test InsightEngine orchestrates loader, embedding, vector store, and LLM correctly."""
    loader = DatasetDocumentLoader()
    embedder = MockEmbeddingService(dimension=32)
    store = InMemoryVectorStore()
    llm = MockLLMService(default_response="Mock facade reply.")
    memory = SlidingWindowChatMemory()

    engine = InsightEngine(
        document_loader=loader,
        embedding_service=embedder,
        vector_store=store,
        llm_service=llm,
        chat_memory=memory,
    )

    df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    
    # Test Ingestion
    indexed = await engine.ingest_dataset("df_id", df, "data.csv")
    assert indexed > 0

    # Test Querying RAG Context
    matches = await engine.query_dataset_rag("df_id", "find matching cols", top_k=2)
    assert len(matches) > 0
    assert -1.0 <= matches[0]["score"] <= 1.0

    # Test Chat Turn Response
    res = await engine.generate_chat_response(
        question="How many rows are in the data?",
        history=[],
        system_prompt="Analyze this data:",
        session_id="df_id",
        use_rag=True,
    )
    assert res == "Mock facade reply."
