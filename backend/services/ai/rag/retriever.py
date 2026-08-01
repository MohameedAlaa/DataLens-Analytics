"""Retriever service for RAG pipeline.

Handles semantic search, metadata filtering, top-K retrieval, and dataset isolation.
Does not include re-ranking logic.
"""

import logging
from typing import Any, Dict, List

from services.data.vector_store import BaseVectorStore
from services.ai.embeddings.embedding_service import BaseEmbeddingService

logger = logging.getLogger(__name__)


class Retriever:
    """Service to retrieve semantic chunks for a given query and dataset."""

    def __init__(self, vector_store: BaseVectorStore, embedding_service: BaseEmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def retrieve(
        self, query: str, dataset_id: str, top_k: int = 5, metadata_filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform a semantic search for the query, scoped to the specific dataset_id.
        
        Args:
            query: The user's semantic query.
            dataset_id: The unique identifier for the dataset (provides strict isolation).
            top_k: Number of chunks to retrieve.
            metadata_filters: Optional metadata filters (future usage).

        Returns:
            List of chunks with their metadata.
        """
        logger.info("Retriever: Starting semantic search for dataset_id '%s'", dataset_id)
        
        if not self.vector_store.dataset_exists(dataset_id):
            logger.warning("Retriever: Dataset index does not exist for dataset_id '%s'", dataset_id)
            return []

        try:
            # 1. Embed the user query
            query_embedding = self.embedding_service.embed_documents([query])[0]
        except Exception as e:
            logger.error("Retriever: Failed to embed query: %s", e)
            return []

        try:
            # 2. Retrieve top-K chunks from the vector store
            # Currently ChromaVectorStore search implementation doesn't expose metadata_filters,
            # but dataset isolation is strictly enforced via dataset_id in the `search` method.
            matches = self.vector_store.search(
                query_embedding=query_embedding,
                dataset_id=dataset_id,
                top_k=top_k
            )
            
            logger.info("Retriever: Found %d chunks for query.", len(matches))
            
            # Additional post-retrieval filtering could be applied here if needed
            return matches

        except Exception as e:
            logger.error("Retriever: Failed to retrieve chunks: %s", e)
            return []
