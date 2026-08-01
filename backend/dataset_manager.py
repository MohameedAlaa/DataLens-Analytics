import abc
import logging
import threading
import uuid
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class BaseStorageEngine(abc.ABC):
    """Abstract base class for pluggable dataset storage engines.
    
    Future implementations can inherit from this class to support:
    - DuckDBStorageEngine (relational OLAP queries)
    - SQLiteStorageEngine (disk-persisted SQL storage)
    - RedisStorageEngine (distributed in-memory cache)
    """

    @abc.abstractmethod
    def store(self, dataset_id: str, df: pd.DataFrame, metadata: Dict[str, Any]) -> None:
        """Store dataset DataFrame and metadata under a unique dataset_id."""
        pass

    @abc.abstractmethod
    def get(self, dataset_id: str) -> Optional[pd.DataFrame]:
        """Retrieve stored dataset DataFrame by dataset_id."""
        pass

    @abc.abstractmethod
    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored metadata by dataset_id."""
        pass

    @abc.abstractmethod
    def delete(self, dataset_id: str) -> bool:
        """Delete stored dataset by dataset_id."""
        pass

    @abc.abstractmethod
    def exists(self, dataset_id: str) -> bool:
        """Check if dataset_id exists in storage."""
        pass

    @abc.abstractmethod
    def list_ids(self) -> List[str]:
        """List all stored dataset IDs."""
        pass


class InMemoryStorageEngine(BaseStorageEngine):
    """Default thread-safe in-memory storage engine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, pd.DataFrame] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._filename_to_id: Dict[str, str] = {}  # Index for legacy filename fallback lookups

    def store(self, dataset_id: str, df: pd.DataFrame, metadata: Dict[str, Any]) -> None:
        with self._lock:
            self._data[dataset_id] = df
            self._metadata[dataset_id] = metadata
            filename = metadata.get("filename")
            if filename:
                self._filename_to_id[filename] = dataset_id

    def get(self, dataset_id: str) -> Optional[pd.DataFrame]:
        with self._lock:
            if dataset_id in self._data:
                return self._data[dataset_id]
            # Fallback lookup by legacy filename for backwards compatibility
            if dataset_id in self._filename_to_id:
                target_id = self._filename_to_id[dataset_id]
                logger.warning(
                    "Legacy lookup using filename '%s'. Please migrate client to dataset_id '%s'",
                    dataset_id, target_id
                )
                return self._data.get(target_id)
            return None

    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if dataset_id in self._metadata:
                return self._metadata[dataset_id]
            if dataset_id in self._filename_to_id:
                return self._metadata.get(self._filename_to_id[dataset_id])
            return None

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            if dataset_id in self._data:
                meta = self._metadata.pop(dataset_id, {})
                filename = meta.get("filename")
                if filename and self._filename_to_id.get(filename) == dataset_id:
                    self._filename_to_id.pop(filename, None)
                self._data.pop(dataset_id, None)
                return True
            return False

    def exists(self, dataset_id: str) -> bool:
        with self._lock:
            return dataset_id in self._data or dataset_id in self._filename_to_id

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())


class DatasetManager:
    """Central Dataset Manager handling UUID assignment, internal storage, and retrieval.
    
    Supports pluggable storage engines for future DuckDB, SQLite, and Redis integration.
    """

    def __init__(self, engine: Optional[BaseStorageEngine] = None) -> None:
        self._engine: BaseStorageEngine = engine or InMemoryStorageEngine()

    def set_engine(self, engine: BaseStorageEngine) -> None:
        """Switch storage engine (e.g. DuckDBStorageEngine, SQLiteStorageEngine, RedisStorageEngine)."""
        logger.info("Switching DatasetManager storage engine to %s", engine.__class__.__name__)
        self._engine = engine

    def register_dataset(
        self,
        df: pd.DataFrame,
        filename: str,
        dataset_id: Optional[str] = None,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Assign a unique UUID to dataset, store internally, and return dataset_id.

        Args:
            df: The full pandas DataFrame to store.
            filename: Original upload filename (used for legacy filename-based lookups).
            dataset_id: Optional pre-generated UUID. If provided, it is used as-is instead of
                        generating a new one. Useful when the caller (e.g. parse_dataset_bytes)
                        has already issued a UUID that must be returned to the client.
            extra_meta: Additional key/value pairs to merge into the stored metadata dict.

        Returns:
            The dataset_id string under which the dataset is stored.
        """
        if dataset_id is None:
            dataset_id = str(uuid.uuid4())
        metadata: Dict[str, Any] = {
            "dataset_id": dataset_id,
            "filename": filename,
            "rows": df.shape[0],
            "cols": df.shape[1],
            "columns": [str(c) for c in df.columns],
            "indexing_status": "PENDING"
        }
        if extra_meta:
            metadata.update(extra_meta)

        self._engine.store(dataset_id, df, metadata)
        logger.info("Registered dataset '%s' with UUID '%s' (Shape: %s, Status: PENDING)", filename, dataset_id, df.shape)
        return dataset_id

    def update_indexing_status(self, dataset_id: str, status: str) -> None:
        """Update the indexing status of a dataset (PENDING, PROCESSING, READY, FAILED)."""
        meta = self.get_metadata(dataset_id)
        if meta is not None:
            meta["indexing_status"] = status
            # Updating dict in place works for InMemoryStorageEngine, 
            # but ideally we should call a method on the engine. For now, this suffices.
            logger.info("Dataset '%s' indexing status updated to %s", dataset_id, status)

    def update_rag_metadata(self, dataset_id: str, rag_metadata: Dict[str, Any]) -> None:
        """Update RAG specific metadata for a dataset."""
        meta = self.get_metadata(dataset_id)
        if meta is not None:
            meta.update(rag_metadata)
            logger.info("Dataset '%s' RAG metadata updated: %s", dataset_id, list(rag_metadata.keys()))

    def get_dataset(self, dataset_id_or_filename: str) -> Optional[pd.DataFrame]:
        """Retrieve dataset DataFrame by dataset_id (or legacy filename)."""
        return self._engine.get(dataset_id_or_filename)

    def get_metadata(self, dataset_id_or_filename: str) -> Optional[Dict[str, Any]]:
        """Retrieve dataset metadata by dataset_id (or legacy filename)."""
        return self._engine.get_metadata(dataset_id_or_filename)

    def delete_dataset(self, dataset_id: str) -> bool:
        """Remove dataset by dataset_id."""
        return self._engine.delete(dataset_id)

    def exists(self, dataset_id_or_filename: str) -> bool:
        """Check if dataset exists by dataset_id or filename."""
        return self._engine.exists(dataset_id_or_filename)

    def list_datasets(self) -> List[str]:
        """List all stored dataset IDs."""
        return self._engine.list_ids()


# Global singleton instance of DatasetManager
dataset_manager = DatasetManager()
