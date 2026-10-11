"""Vector store interface and ChromaDB implementation.

Provides storage and similarity search for document chunks.
Designed behind an abstract interface for future swap-out (e.g., Qdrant).
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List
import os

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from services.ai.rag.chunker import Chunk

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """Abstract interface for a vector database."""

    @abstractmethod
    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Insert chunks and their vector embeddings into the database."""
        pass

    @abstractmethod
    def search(
        self, query_embedding: List[float], dataset_id: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search the database for similar chunks, scoped by dataset_id."""
        pass

    @abstractmethod
    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete all chunks associated with a dataset_id."""
        pass

    @abstractmethod
    def count_vectors(self, dataset_id: str) -> int:
        """Count the number of chunks for a dataset_id."""
        pass

    @abstractmethod
    def dataset_exists(self, dataset_id: str) -> bool:
        """Check if any chunks exist for a dataset_id."""
        pass


class ChromaVectorStore(BaseVectorStore):
    """Vector store using local ChromaDB."""

    def __init__(self, collection_name: str = "datalens_rag", persist_directory: str = None):
        if chromadb is None:
            raise RuntimeError("chromadb is not installed.")

        if not persist_directory:
            try:
                from backend.config import settings
                persist_directory = settings.chroma_persist_dir
            except ImportError:
                try:
                    from config import settings
                    persist_directory = settings.chroma_persist_dir
                except ImportError:
                    persist_directory = "./chroma_db"

        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        logger.info("ChromaVectorStore initialized at '%s' with collection '%s'", persist_directory, collection_name)

    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        if not chunks or not embeddings:
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("Mismatched number of chunks and embeddings.")

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        # Chroma requires metadata values to be str, int, float, or bool.
        # We must stringify lists or dicts in metadata (e.g., column_names).
        metadatas = []
        for chunk in chunks:
            clean_meta = {}
            for k, v in chunk.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                elif isinstance(v, list):
                    clean_meta[k] = ", ".join([str(item) for item in v])
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info("Inserted %d chunks into ChromaDB.", len(chunks))

    def search(
        self, query_embedding: List[float], dataset_id: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"dataset_id": dataset_id}
        )

        matches = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                matches.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results and results["distances"] else 0.0
                })
        return matches

    def delete_dataset(self, dataset_id: str) -> bool:
        try:
            self.collection.delete(where={"dataset_id": dataset_id})
            logger.info("Deleted chunks for dataset_id '%s' from ChromaDB.", dataset_id)
            return True
        except Exception as e:
            logger.error("Failed to delete dataset_id '%s' from ChromaDB: %s", dataset_id, e)
            return False

    def count_vectors(self, dataset_id: str) -> int:
        try:
            results = self.collection.get(where={"dataset_id": dataset_id}, include=[])
            if results and "ids" in results:
                return len(results["ids"])
            return 0
        except Exception as e:
            logger.error("Failed to count vectors for dataset_id '%s': %s", dataset_id, e)
            return 0

    def dataset_exists(self, dataset_id: str) -> bool:
        return self.count_vectors(dataset_id) > 0


_global_vector_store = None

def get_vector_store() -> BaseVectorStore:
    """Get the global application-scoped vector store instance."""
    global _global_vector_store
    if _global_vector_store is None:
        _global_vector_store = ChromaVectorStore()
    return _global_vector_store
