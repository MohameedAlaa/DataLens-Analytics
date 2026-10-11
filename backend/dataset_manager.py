import abc
import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class BaseStorageEngine(abc.ABC):
    """Abstract base class for pluggable dataset storage engines.
    
    Implementations include:
    - InMemoryStorageEngine (ephemeral in-memory dictionary)
    - DiskStorageEngine (persistent Parquet + JSON filesystem storage)
    - DuckDBStorageEngine / RedisStorageEngine (distributed external stores)
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

    def store(self, dataset_id: str, df: pd.DataFrame, metadata: Dict[str, Any]) -> None:
        with self._lock:
            self._data[dataset_id] = df
            self._metadata[dataset_id] = metadata

    def get(self, dataset_id: str) -> Optional[pd.DataFrame]:
        with self._lock:
            return self._data.get(dataset_id)

    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._metadata.get(dataset_id)

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            if dataset_id in self._data:
                self._metadata.pop(dataset_id, None)
                self._data.pop(dataset_id, None)
                return True
            return False

    def exists(self, dataset_id: str) -> bool:
        with self._lock:
            return dataset_id in self._data

    def list_ids(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())


class DiskStorageEngine(BaseStorageEngine):
    """Persistent filesystem storage engine for DataFrames and metadata.

    Persists datasets as Parquet files and JSON metadata to a configured directory.
    Enables cross-process persistence and surviving process restarts.
    """

    def __init__(self, storage_dir: Union[str, Path] = "./dataset_storage") -> None:
        self.storage_dir = Path(storage_dir).resolve()
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            # Probe write permissions to fail fast if persistent storage is misconfigured/read-only
            probe_file = self.storage_dir / ".write_probe"
            probe_file.touch()
            probe_file.unlink()
        except Exception as exc:
            raise RuntimeError(
                f"DiskStorageEngine failed to initialize writable directory at '{self.storage_dir}': {exc}"
            ) from exc
        self._lock = threading.Lock()

    def _df_path(self, dataset_id: str) -> Path:
        return self.storage_dir / f"{dataset_id}.parquet"

    def _meta_path(self, dataset_id: str) -> Path:
        return self.storage_dir / f"{dataset_id}.meta.json"

    def store(self, dataset_id: str, df: pd.DataFrame, metadata: Dict[str, Any]) -> None:
        with self._lock:
            df.to_parquet(self._df_path(dataset_id), index=False)
            with open(self._meta_path(dataset_id), "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

    def get(self, dataset_id: str) -> Optional[pd.DataFrame]:
        with self._lock:
            p = self._df_path(dataset_id)
            if not p.is_file():
                return None
            try:
                return pd.read_parquet(p)
            except Exception as e:
                logger.error("Failed to read dataset '%s' from disk: %s", dataset_id, e)
                return None

    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            p = self._meta_path(dataset_id)
            if not p.is_file():
                return None
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to read metadata for '%s' from disk: %s", dataset_id, e)
                return None

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            df_p = self._df_path(dataset_id)
            meta_p = self._meta_path(dataset_id)
            existed = False
            if df_p.is_file():
                df_p.unlink()
                existed = True
            if meta_p.is_file():
                meta_p.unlink()
                existed = True
            return existed

    def exists(self, dataset_id: str) -> bool:
        with self._lock:
            return self._df_path(dataset_id).is_file() and self._meta_path(dataset_id).is_file()

    def list_ids(self) -> List[str]:
        with self._lock:
            return [p.stem for p in self.storage_dir.glob("*.parquet")]


class DatasetManager:
    """Central Dataset Manager handling UUID assignment, internal storage, and retrieval.
    
    Supports pluggable storage engines for in-memory, disk Parquet, DuckDB, and Redis.
    """

    def __init__(self, engine: Optional[BaseStorageEngine] = None) -> None:
        self._engine: BaseStorageEngine = engine or InMemoryStorageEngine()

    def set_engine(self, engine: BaseStorageEngine) -> None:
        """Switch storage engine (e.g. DiskStorageEngine, RedisStorageEngine)."""
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
            df = self.get_dataset(dataset_id)
            if df is not None:
                self._engine.store(dataset_id, df, meta)
            logger.info("Dataset '%s' indexing status updated to %s", dataset_id, status)

    def update_rag_metadata(self, dataset_id: str, rag_metadata: Dict[str, Any]) -> None:
        """Update RAG specific metadata for a dataset."""
        meta = self.get_metadata(dataset_id)
        if meta is not None:
            meta.update(rag_metadata)
            df = self.get_dataset(dataset_id)
            if df is not None:
                self._engine.store(dataset_id, df, meta)
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


def create_default_dataset_manager() -> DatasetManager:
    try:
        from backend.config import settings
    except ImportError:
        try:
            from config import settings
        except ImportError:
            settings = None

    if settings and getattr(settings, "storage_engine", "memory") in ("disk", "filesystem"):
        engine = DiskStorageEngine(storage_dir=settings.dataset_storage_dir)
        logger.info("Initializing DatasetManager with DiskStorageEngine at '%s'", settings.dataset_storage_dir)
    else:
        if settings and getattr(settings, "is_production", False):
            logger.warning(
                "PRODUCTION WARNING: DatasetManager running with InMemoryStorageEngine (STORAGE_ENGINE='%s'). "
                "Dataset state will NOT persist across process restarts or multi-instance deployments. "
                "Configure STORAGE_ENGINE=disk and DATASET_STORAGE_DIR to a persistent volume for production.",
                getattr(settings, "storage_engine", "memory")
            )
        engine = InMemoryStorageEngine()
    return DatasetManager(engine=engine)


# ---------------------------------------------------------------------------
# Default singleton instance (used by serverless api/ and default app state)
# ---------------------------------------------------------------------------
dataset_manager = create_default_dataset_manager()

import sys
# Alias module in sys.modules to prevent duplicate instances when imported as both 'dataset_manager' and 'backend.dataset_manager'
if __name__ in sys.modules:
    sys.modules["backend.dataset_manager"] = sys.modules[__name__]
    sys.modules["dataset_manager"] = sys.modules[__name__]



