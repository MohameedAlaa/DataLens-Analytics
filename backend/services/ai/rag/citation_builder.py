"""Citation builder for RAG responses."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CitationBuilder:
    """Build lightweight citations from retrieved metadata."""

    def build(
        self,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        if not retrieved_chunks:
            return []

        citations: List[Dict[str, Any]] = []
        for chunk in retrieved_chunks:
            metadata = chunk.get("metadata") or {}
            citation = {
                "chunk_id": metadata.get("chunk_id") or chunk.get("id"),
                "dataset_id": metadata.get("dataset_id"),
                "text": chunk.get("document", ""),
                "row_start": metadata.get("row_start"),
                "row_end": metadata.get("row_end"),
                "filename": metadata.get("filename"),
                "source": metadata.get("sheet_name") or metadata.get("source") or "dataset",
            }
            citations.append(citation)
        return citations
