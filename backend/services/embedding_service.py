"""Embedding service interface and providers for vector representation generation.

Provides BaseEmbeddingService ABC and MockEmbeddingService for zero-dependency test
and development environments. Easily pluggable for OpenAI/Gemini embedding models.
"""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import List
import numpy as np

from .base import Chunk


class BaseEmbeddingService(ABC):
    """Abstract interface for embedding text strings and chunks into vector spaces."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector embedding output dimension."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string into a vector of float values."""
        pass

    @abstractmethod
    async def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Embed a list of Chunk objects in-place, populating their embedding field."""
        pass


class MockEmbeddingService(BaseEmbeddingService):
    """Zero-dependency mock embedding provider generating deterministic vector representations.

    Uses SHA-256 hash hashing of text strings into a normalized unit vector space
    to support functional similarity testing without external API calls.
    """

    def __init__(self, dimension: int = 128) -> None:
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _hash_to_vector(self, text: str) -> List[float]:
        """Convert string text into a deterministic, unit-normalized float vector."""
        vec = []
        # Generate pseudorandom floats seeded by text hash chunks
        for i in range(self._dim):
            h = hashlib.sha256(f"{text}_{i}".encode("utf-8")).hexdigest()
            # Map hex hash snippet to float in range [-1.0, 1.0]
            val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
            vec.append(val)

        # Normalize vector to unit length (L2 norm)
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        return self._hash_to_vector(text)

    async def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Embed a batch of chunks."""
        for chunk in chunks:
            chunk.embedding = self._hash_to_vector(chunk.text)
        return chunks
