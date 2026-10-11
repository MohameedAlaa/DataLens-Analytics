"""Embedding service for vector generation.

Wraps sentence-transformers to generate embeddings for document chunks.
Designed behind an abstract interface for future swap-out (e.g., OpenAI, Voyage).
"""

from abc import ABC, abstractmethod
from typing import List
import logging

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class BaseEmbeddingService(ABC):
    """Abstract interface for embedding text chunks."""
    
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings into high-dimensional vectors."""
        pass

class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """Local embedding service using HuggingFace's sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed.")
        
        logger.info("Initializing SentenceTransformer with model '%s'...", model_name)
        self.model = SentenceTransformer(model_name)
        logger.info("SentenceTransformer initialized successfully.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        # sentence-transformers outputs numpy arrays, convert to lists of floats
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()


_global_embedding_service = None

def get_embedding_service() -> BaseEmbeddingService:
    """Get the global application-scoped embedding service instance."""
    global _global_embedding_service
    if _global_embedding_service is None:
        _global_embedding_service = SentenceTransformerEmbeddingService()
    return _global_embedding_service
