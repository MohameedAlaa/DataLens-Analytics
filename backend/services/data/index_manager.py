"""Index Manager service.

Provides a single abstraction over vector indexes, handling creation, deletion,
status checks, and metadata verification, without exposing the underlying VectorStore.
"""

from typing import Any, Dict
import logging

from services.data.vector_store import BaseVectorStore

logger = logging.getLogger(__name__)


class IndexManager:
    """Service to manage vector index lifecycle and metadata."""

    def __init__(self, vector_store: BaseVectorStore):
        self.vector_store = vector_store

    def delete_index(self, dataset_id: str) -> bool:
        """Delete an entire index for a given dataset_id."""
        logger.info("IndexManager: Deleting index for dataset_id '%s'", dataset_id)
        return self.vector_store.delete_dataset(dataset_id)

    def count_vectors(self, dataset_id: str) -> int:
        """Count the number of vectors stored in the index for a dataset."""
        return self.vector_store.count_vectors(dataset_id)

    def dataset_exists(self, dataset_id: str) -> bool:
        """Verify if a dataset's index exists and contains vectors."""
        return self.vector_store.dataset_exists(dataset_id)

    def get_index_metadata(self, dataset_id: str) -> Dict[str, Any]:
        """Return basic metadata about a specific dataset's index."""
        count = self.count_vectors(dataset_id)
        exists = count > 0
        return {
            "dataset_id": dataset_id,
            "exists": exists,
            "vector_count": count,
            "store_type": self.vector_store.__class__.__name__
        }
