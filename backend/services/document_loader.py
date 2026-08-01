"""Document loader module for dataset parsing, chunking, and metadata extraction.

Provides an abstract interface BaseDocumentLoader and DatasetDocumentLoader implementation
that breaks datasets into structured Document objects and embeddable Chunks.
"""

from abc import ABC, abstractmethod
import uuid
from typing import Any, Dict, List, Optional
import pandas as pd

from .base import Chunk, Document


class BaseDocumentLoader(ABC):
    """Abstract interface for loading and chunking data sources."""

    @abstractmethod
    def load(self, source: Any, **kwargs: Any) -> List[Document]:
        """Load a raw data source into a list of Document objects."""
        pass

    @abstractmethod
    def chunk(
        self, documents: List[Document], chunk_size: int = 5, overlap: int = 0
    ) -> List[Chunk]:
        """Split Document objects into smaller embeddable Chunk fragments."""
        pass


class DatasetDocumentLoader(BaseDocumentLoader):
    """Document loader tailored for pandas DataFrames and tabular datasets."""

    def load(
        self,
        source: pd.DataFrame,
        dataset_id: str = "",
        filename: str = "dataset",
        **kwargs: Any
    ) -> List[Document]:
        """Convert a DataFrame into a Document containing column schemas, stats summary, and rows.

        Args:
            source: The pandas DataFrame.
            dataset_id: Unique identifier for the dataset.
            filename: Original dataset filename.

        Returns:
            List containing a Document object representation of the dataset.
        """
        if source.empty:
            return []

        doc_id = dataset_id or str(uuid.uuid4())
        rows, cols = source.shape
        metadata = {
            "dataset_id": doc_id,
            "filename": filename,
            "row_count": rows,
            "column_count": cols,
            "columns": [str(c) for c in source.columns],
        }

        # Convert rows into text records
        records_text = source.to_string(index=False)
        content = (
            f"Dataset: '{filename}' (ID: {doc_id})\n"
            f"Dimensions: {rows} rows, {cols} columns\n"
            f"Columns: {', '.join([str(c) for c in source.columns])}\n\n"
            f"Data Records:\n{records_text}"
        )

        return [Document(doc_id=doc_id, content=content, metadata=metadata)]

    def chunk(
        self, documents: List[Document], chunk_size: int = 10, overlap: int = 2
    ) -> List[Chunk]:
        """Chunk dataset document into row batches for fine-grained retrieval.

        Args:
            documents: List of Document objects.
            chunk_size: Number of text lines/records per chunk.
            overlap: Number of overlapping lines between consecutive chunks.

        Returns:
            List of Chunk objects.
        """
        chunks: List[Chunk] = []

        for doc in documents:
            lines = doc.content.splitlines()
            if not lines:
                continue

            # Header info lives in lines[:4]
            header = "\n".join(lines[:4])
            body_lines = lines[4:] if len(lines) > 4 else lines

            if not body_lines:
                chunk_id = f"{doc.doc_id}_chunk_0"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        text=doc.content,
                        metadata={**doc.metadata, "chunk_index": 0},
                    )
                )
                continue

            step = max(1, chunk_size - overlap)
            chunk_idx = 0
            for i in range(0, len(body_lines), step):
                batch = body_lines[i : i + chunk_size]
                chunk_text = f"{header}\n\n" + "\n".join(batch)
                chunk_id = f"{doc.doc_id}_chunk_{chunk_idx}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        text=chunk_text,
                        metadata={
                            **doc.metadata,
                            "chunk_index": chunk_idx,
                            "start_line": i,
                            "end_line": i + len(batch),
                        },
                    )
                )
                chunk_idx += 1

        return chunks
