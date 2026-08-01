import pytest
from unittest.mock import Mock

from services.data.index_manager import IndexManager
from services.data.vector_store import BaseVectorStore

@pytest.fixture
def mock_vector_store():
    store = Mock(spec=BaseVectorStore)
    return store

@pytest.fixture
def index_manager(mock_vector_store):
    return IndexManager(vector_store=mock_vector_store)

def test_delete_index(index_manager, mock_vector_store):
    dataset_id = "test_dataset_123"
    mock_vector_store.delete_dataset.return_value = True

    result = index_manager.delete_index(dataset_id)

    assert result is True
    mock_vector_store.delete_dataset.assert_called_once_with(dataset_id)

def test_count_vectors(index_manager, mock_vector_store):
    dataset_id = "test_dataset_123"
    mock_vector_store.count_vectors.return_value = 42

    result = index_manager.count_vectors(dataset_id)

    assert result == 42
    mock_vector_store.count_vectors.assert_called_once_with(dataset_id)

def test_dataset_exists(index_manager, mock_vector_store):
    dataset_id = "test_dataset_123"
    mock_vector_store.dataset_exists.return_value = True

    result = index_manager.dataset_exists(dataset_id)

    assert result is True
    mock_vector_store.dataset_exists.assert_called_once_with(dataset_id)

def test_get_index_metadata(index_manager, mock_vector_store):
    dataset_id = "test_dataset_123"
    mock_vector_store.count_vectors.return_value = 10
    
    # Needs to match the Mock class name, which is 'Mock' in this test setup
    expected_store_type = mock_vector_store.__class__.__name__

    metadata = index_manager.get_index_metadata(dataset_id)

    assert metadata == {
        "dataset_id": dataset_id,
        "exists": True,
        "vector_count": 10,
        "store_type": expected_store_type
    }
