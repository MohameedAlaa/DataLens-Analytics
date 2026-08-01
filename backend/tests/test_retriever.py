import pytest
from unittest.mock import Mock

from services.ai.rag.retriever import Retriever
from services.data.vector_store import BaseVectorStore
from services.ai.embeddings.embedding_service import BaseEmbeddingService

@pytest.fixture
def mock_vector_store():
    store = Mock(spec=BaseVectorStore)
    return store

@pytest.fixture
def mock_embedding_service():
    service = Mock(spec=BaseEmbeddingService)
    return service

@pytest.fixture
def retriever(mock_vector_store, mock_embedding_service):
    return Retriever(vector_store=mock_vector_store, embedding_service=mock_embedding_service)

def test_retrieve_successful(retriever, mock_vector_store, mock_embedding_service):
    query = "test query"
    dataset_id = "test_dataset_123"
    top_k = 3
    
    # Mock behavior
    mock_vector_store.dataset_exists.return_value = True
    mock_embedding_service.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    mock_vector_store.search.return_value = [
        {"id": "chunk_1", "document": "doc1", "metadata": {}},
        {"id": "chunk_2", "document": "doc2", "metadata": {}}
    ]

    results = retriever.retrieve(query=query, dataset_id=dataset_id, top_k=top_k)

    assert len(results) == 2
    mock_vector_store.dataset_exists.assert_called_once_with(dataset_id)
    mock_embedding_service.embed_documents.assert_called_once_with([query])
    mock_vector_store.search.assert_called_once_with(
        query_embedding=[0.1, 0.2, 0.3],
        dataset_id=dataset_id,
        top_k=top_k
    )

def test_retrieve_dataset_not_exists(retriever, mock_vector_store, mock_embedding_service):
    query = "test query"
    dataset_id = "test_dataset_123"
    
    mock_vector_store.dataset_exists.return_value = False

    results = retriever.retrieve(query=query, dataset_id=dataset_id)

    assert results == []
    mock_vector_store.dataset_exists.assert_called_once_with(dataset_id)
    mock_embedding_service.embed_documents.assert_not_called()
    mock_vector_store.search.assert_not_called()

def test_retrieve_embedding_failure(retriever, mock_vector_store, mock_embedding_service):
    query = "test query"
    dataset_id = "test_dataset_123"
    
    mock_vector_store.dataset_exists.return_value = True
    mock_embedding_service.embed_documents.side_effect = Exception("Embedding API down")

    results = retriever.retrieve(query=query, dataset_id=dataset_id)

    assert results == []
    mock_vector_store.dataset_exists.assert_called_once_with(dataset_id)
    mock_embedding_service.embed_documents.assert_called_once_with([query])
    mock_vector_store.search.assert_not_called()
