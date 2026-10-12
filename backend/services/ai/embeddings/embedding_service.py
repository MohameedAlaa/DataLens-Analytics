"""Embedding service for vector generation.

Wraps Google Gemini's hosted embedContent / batchEmbedContents API for lightweight,
high-performance embeddings without heavy local PyTorch or transformers dependencies.
Designed behind an abstract interface (BaseEmbeddingService) for seamless swap-out.
"""

from abc import ABC, abstractmethod
import hashlib
import logging
import math
from typing import Any, Dict, List, Optional

import httpx

try:
    from backend.config import settings
except ImportError:
    try:
        from config import settings
    except ImportError:
        settings = None

logger = logging.getLogger(__name__)


class BaseEmbeddingService(ABC):
    """Abstract interface for embedding text chunks."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings into high-dimensional vectors."""
        pass


class GeminiEmbeddingService(BaseEmbeddingService):
    """Hosted embedding service using Google Gemini text-embedding API.

    Features:
    - Zero local PyTorch/Transformers dependencies.
    - Uses existing GOOGLE_API_KEY.
    - Output dimension defaults to 768 for optimal performance and ChromaDB indexing.
    - Graceful deterministic fallback when offline or in test environments without API key.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-embedding-001",
        dimension: int = 768,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or (getattr(settings, "google_api_key", "") if settings else "")
        self.model_name = model_name
        self.dimension = dimension
        self.timeout = timeout
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # If no API key is provided, allow deterministic vectors ONLY in non-production offline/test mode
        if not self.api_key:
            if settings and settings.is_production:
                raise RuntimeError(
                    "GOOGLE_API_KEY is not configured for Gemini embeddings in production environment."
                )
            logger.info("GeminiEmbeddingService: GOOGLE_API_KEY not configured. Using deterministic offline embeddings.")
            return [self._deterministic_pseudo_embedding(t) for t in texts]

        results: List[List[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            batch_embeddings = self._embed_batch(chunk)
            results.extend(batch_embeddings)
        return results

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            url = f"{self.api_url}:batchEmbedContents"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            payload = {
                "requests": [
                    {
                        "model": f"models/{self.model_name}",
                        "content": {"parts": [{"text": t}]},
                        "outputDimensionality": self.dimension,
                    }
                    for t in texts
                ]
            }
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = data.get("embeddings", [])
                    return [e.get("values", []) for e in embeddings]
                else:
                    err_msg = (
                        f"Gemini embedding API returned status {resp.status_code}: {resp.text[:200]}"
                    )
                    logger.error(err_msg)
                    raise RuntimeError(err_msg)
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            err_msg = f"Gemini embedding API call failed: {exc}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from exc

    def _deterministic_pseudo_embedding(self, text: str) -> List[float]:
        """Fast, normalized 768-dim float vector based on SHA-256 seed. Zero external dependencies."""
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
        vec = []
        for i in range(self.dimension):
            val = math.sin(seed + i * 1.6180339887)
            vec.append(val)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]


class SentenceTransformerEmbeddingService(BaseEmbeddingService):
    """Optional local fallback embedding service. Lazy loads sentence-transformers only if instantiated."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError("sentence-transformers is not installed. Use GeminiEmbeddingService.")

        logger.info("Initializing SentenceTransformer with model '%s'...", model_name)
        self.model = SentenceTransformer(model_name)
        logger.info("SentenceTransformer initialized successfully.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()


_global_embedding_service: Optional[BaseEmbeddingService] = None


def get_embedding_service() -> BaseEmbeddingService:
    """Get the global application-scoped embedding service instance."""
    global _global_embedding_service
    if _global_embedding_service is None:
        _global_embedding_service = GeminiEmbeddingService()
    return _global_embedding_service
