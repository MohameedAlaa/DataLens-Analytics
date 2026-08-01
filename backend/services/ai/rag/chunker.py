"""Chunker module for RAG retrieval pipeline.

Splits loaded Documents into embeddable Chunks using token-based limits
while preserving strict row boundaries.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List
import tiktoken

from services.data.document_loader import Document

logger = logging.getLogger(__name__)

class Chunk:
    """Represents a discrete embeddable fragment of a document."""
    def __init__(self, chunk_id: str, doc_id: str, text: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.text = text
        self.metadata = metadata

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, documents: List[Document]) -> List[Chunk]:
        pass

class TokenRowChunker(BaseChunker):
    """Chunks tabular datasets by token count while strictly preserving row boundaries."""

    def __init__(
        self,
        min_tokens: int = 300,
        max_tokens: int = 600,
        model_name: str = "cl100k_base"
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding(model_name)

    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text, disallowed_special=()))

    def chunk(self, documents: List[Document]) -> List[Chunk]:
        chunks: List[Chunk] = []

        for doc in documents:
            lines = doc.content.splitlines()
            if not lines:
                continue

            # Identify the header portion and the data portion
            try:
                data_start_idx = lines.index("Data:") + 1
            except ValueError:
                data_start_idx = 0

            header = "\n".join(lines[:data_start_idx])
            header_tokens = self._count_tokens(header)

            data_lines = lines[data_start_idx:]
            if not data_lines:
                continue
            
            # The first data line is the CSV header (columns)
            csv_header = data_lines[0]
            data_rows = data_lines[1:]

            current_chunk_lines = []
            current_tokens = header_tokens + self._count_tokens(csv_header + "\n")
            
            chunk_idx = 0
            row_start = 0

            dataset_id = doc.metadata.get("dataset_id", doc.doc_id)
            column_names = doc.metadata.get("column_names", [])
            sheet_name = doc.metadata.get("sheet_name", "Sheet1")

            for i, row in enumerate(data_rows):
                row_tokens = self._count_tokens(row + "\n")

                # If adding this row pushes us over max_tokens, and we have enough to form a valid chunk
                if current_tokens + row_tokens > self.max_tokens and current_chunk_lines:
                    chunk_text = f"{header}\n{csv_header}\n" + "\n".join(current_chunk_lines)
                    chunk_id = f"{dataset_id}_chunk_{chunk_idx}"
                    
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        text=chunk_text,
                        metadata={
                            "dataset_id": dataset_id,
                            "chunk_id": chunk_id,
                            "row_start": row_start,
                            "row_end": row_start + len(current_chunk_lines) - 1,
                            "column_names": column_names,
                            "chunk_type": "tabular",
                            "sheet_name": sheet_name
                        }
                    ))
                    
                    # Reset for next chunk
                    chunk_idx += 1
                    current_chunk_lines = []
                    current_tokens = header_tokens + self._count_tokens(csv_header + "\n")
                    row_start = i

                current_chunk_lines.append(row)
                current_tokens += row_tokens

            # Flush remaining lines
            if current_chunk_lines:
                chunk_text = f"{header}\n{csv_header}\n" + "\n".join(current_chunk_lines)
                chunk_id = f"{dataset_id}_chunk_{chunk_idx}"
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    text=chunk_text,
                    metadata={
                        "dataset_id": dataset_id,
                        "chunk_id": chunk_id,
                        "row_start": row_start,
                        "row_end": row_start + len(current_chunk_lines) - 1,
                        "column_names": column_names,
                        "chunk_type": "tabular",
                        "sheet_name": sheet_name
                    }
                ))

            logger.info("Chunked document '%s' into %d chunks.", doc.doc_id, len(chunks))

        return chunks
