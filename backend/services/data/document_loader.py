"""Document loader for tabular datasets.

Converts pandas DataFrames into semantic representations suitable for token chunking.
"""

from abc import ABC, abstractmethod
import uuid
from typing import Any, Dict, List
import pandas as pd

class Document:
    """Represents a full dataset document before chunking."""
    def __init__(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        self.doc_id = doc_id
        self.content = content
        self.metadata = metadata

class BaseDocumentLoader(ABC):
    """Abstract interface for loading data sources."""
    @abstractmethod
    def load(self, source: Any, **kwargs: Any) -> List[Document]:
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
        """Convert a DataFrame into a Document containing column schemas and rows.

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
        columns = [str(c) for c in source.columns]
        
        metadata = {
            "dataset_id": doc_id,
            "filename": filename,
            "row_count": rows,
            "column_count": cols,
            "column_names": columns,
            "sheet_name": kwargs.get("sheet_name", "Sheet1"),
            "df": source
        }

        content = (
            f"Dataset: '{filename}' (ID: {doc_id})\n"
            f"Dimensions: {rows} rows, {cols} columns\n"
            f"Columns: {', '.join(columns)}\n"
        )

        return [Document(doc_id=doc_id, content=content, metadata=metadata)]
