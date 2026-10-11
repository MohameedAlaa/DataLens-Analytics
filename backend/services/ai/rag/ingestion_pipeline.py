"""Ingestion pipeline coordinator for RAG architecture.

Coordinates the document loading, chunking, embedding, and vector insertion
as an asynchronous background task. Updates the DatasetManager with indexing status.
"""

import logging
import asyncio
from typing import Any, Dict
import pandas as pd


from services.data.document_loader import DatasetDocumentLoader
from services.ai.rag.chunker import TokenRowChunker
from services.ai.embeddings.embedding_service import SentenceTransformerEmbeddingService
from services.data.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Coordinates the ingestion steps for a newly uploaded dataset."""

    def __init__(self):
        # We lazily initialize these or inject them. For now, simple instantiation.
        self.document_loader = DatasetDocumentLoader()
        self.chunker = TokenRowChunker(min_tokens=300, max_tokens=600)
        self.embedding_service = None
        self.vector_store = None
        
        # Avoid loading models blocking the main thread if possible, 
        # but for simplicity in V1 we initialize on first use or in background.

    def _ensure_services_initialized(self):
        from services.ai.embeddings.embedding_service import get_embedding_service
        from services.data.vector_store import get_vector_store
        
        if self.embedding_service is None:
            logger.info("Retrieving global Embedding Service...")
            self.embedding_service = get_embedding_service()
        if self.vector_store is None:
            logger.info("Retrieving global Vector Store...")
            self.vector_store = get_vector_store()

    def run_ingestion(self, dataset_id: str, df: pd.DataFrame, filename: str, dataset_manager) -> None:
        """Run the ingestion pipeline synchronously (called via BackgroundTasks)."""
        try:
            logger.info("Dataset Ingestion Started for '%s'", dataset_id)
            dataset_manager.update_indexing_status(dataset_id, "PROCESSING")

            self._ensure_services_initialized()

            # 1. Document Loader
            logger.info("Dataset Loading Started for '%s'", dataset_id)
            documents = self.document_loader.load(source=df, dataset_id=dataset_id, filename=filename)
            logger.info("Dataset Loaded: %d documents created.", len(documents))

            # 2. Chunker
            logger.info("Chunking Started for '%s'", dataset_id)
            chunks = self.chunker.chunk(documents)
            logger.info("Chunks Created: %d chunks for dataset '%s'", len(chunks), dataset_id)

            if not chunks:
                logger.warning("No chunks created for dataset '%s'. Completing early.", dataset_id)
                dataset_manager.update_indexing_status(dataset_id, "READY")
                return

            # 3. Embedding
            logger.info("Embedding Started for '%s' (%d chunks)", dataset_id, len(chunks))
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.embed_documents(chunk_texts)
            logger.info("Embedding Completed for '%s'", dataset_id)

            # 4. Vector Store Insert
            logger.info("Vector Store Insert Started for '%s'", dataset_id)
            
            # Clean up any existing vectors for this dataset_id to prevent duplicate orphans
            self.vector_store.delete_dataset(dataset_id)
            
            self.vector_store.add_chunks(chunks, embeddings)
            logger.info("Vector Store Inserted for '%s'", dataset_id)

            # 5. Index Verification
            vector_count = self.vector_store.count_vectors(dataset_id)
            if vector_count == 0:
                raise RuntimeError("Index verification failed: 0 vectors found in Chroma after insertion.")
            elif vector_count != len(chunks):
                logger.warning("Index verification mismatch: inserted %d chunks but found %d vectors in Chroma.", len(chunks), vector_count)
            else:
                logger.info("Index verified: %d vectors successfully stored.", vector_count)

            # Update extended RAG metadata
            import datetime
            rag_meta = {
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dimension": 384,
                "chunk_count": len(chunks),
                "vector_count": vector_count,
                "indexed_at": datetime.datetime.utcnow().isoformat() + "Z",
                "index_version": "1.0"
            }
            dataset_manager.update_rag_metadata(dataset_id, rag_meta)

            # Done
            dataset_manager.update_indexing_status(dataset_id, "READY")
            logger.info("Index Ready for dataset '%s'", dataset_id)

        except Exception as e:
            logger.exception("Ingestion failed for dataset '%s': %s", dataset_id, e)
            dataset_manager.update_indexing_status(dataset_id, "FAILED")
            # We explicitly do NOT delete the dataset from dataset_manager to keep it available.

# Singleton instance
ingestion_pipeline = IngestionPipeline()
