"""Vector store module for vector indexing and similarity search.

Provides BaseVectorStore ABC and InMemoryVectorStore implementation using NumPy
cosine similarity. Easily pluggable for ChromaDB, Pinecone, or DuckDB.
"""

from abc import ABC, abstractmethod
import threading
from typing import Dict, List, Optional
import numpy as np

from .base import Chunk, SearchResult


class BaseVectorStore(ABC):
    """Abstract interface for vector database storage and similarity retrieval."""

    @abstractmethod
    async def add_chunks(self, chunks: List[Chunk]) -> int:
        """Add embedded Chunk objects into the vector store."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        doc_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """Search for top_k most similar chunks matching query_vector."""
        pass

    @abstractmethod
    async def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all stored chunks belonging to doc_id."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all indexed vectors and chunks."""
        pass


class InMemoryVectorStore(BaseVectorStore):
    """Thread-safe in-memory vector store using NumPy for cosine similarity search."""

    def __init__(self) -> None:
        self._chunks: Dict[str, Chunk] = {}  # chunk_id -> Chunk
        self._lock = threading.RLock()

    async def add_chunks(self, chunks: List[Chunk]) -> int:
        """Store chunks with valid embedding vectors."""
        count = 0
        with self._lock:
            for chunk in chunks:
                if chunk.embedding is not None and len(chunk.embedding) > 0:
                    self._chunks[chunk.chunk_id] = chunk
                    count += 1
        return count

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        doc_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """Perform top-k k-NN cosine similarity search matching query_vector."""
        with self._lock:
            candidates: List[Chunk] = []
            for chunk in self._chunks.values():
                if doc_id is not None and chunk.metadata.get("dataset_id") != doc_id and chunk.doc_id != doc_id:
                    continue
                if chunk.embedding is not None:
                    candidates.append(chunk)

            if not candidates:
                return []

            q_arr = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q_arr)
            if q_norm == 0:
                return []

            results: List[SearchResult] = []
            for chunk in candidates:
                c_arr = np.array(chunk.embedding, dtype=np.float32)
                c_norm = np.linalg.norm(c_arr)
                if c_norm == 0:
                    score = 0.0
                else:
                    score = float(np.dot(q_arr, c_arr) / (q_norm * c_norm))

                results.append(SearchResult(chunk=chunk, score=score, metadata=chunk.metadata))

            # Sort descending by similarity score
            results.sort(key=lambda r: r.score, reverse=True)
            return results[:top_k]

    async def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks matching doc_id."""
        with self._lock:
            to_delete = [
                cid
                for cid, c in self._chunks.items()
                if c.doc_id == doc_id or c.metadata.get("dataset_id") == doc_id
            ]
            for cid in to_delete:
                del self._chunks[cid]
            return len(to_delete)

    async def clear(self) -> None:
        """Clear all stored vectors."""
        with self._lock:
            self._chunks.clear()
