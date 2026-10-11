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

        import csv
        import io
        import hashlib

        def format_row_to_csv(row_tuple):
            si = io.StringIO()
            cw = csv.writer(si)
            cw.writerow(row_tuple)
            return si.getvalue()

        for doc in documents:
            dataset_id = doc.metadata.get("dataset_id", doc.doc_id)
            column_names = doc.metadata.get("column_names", [])
            sheet_name = doc.metadata.get("sheet_name", "Sheet1")
            filename = doc.metadata.get("filename", "dataset")
            df = doc.metadata.get("df")

            if df is None or df.empty:
                continue

            header = doc.content + "\nData:\n"
            csv_header = format_row_to_csv(df.columns.tolist())
            header_tokens = self._count_tokens(header)

            current_chunk_rows = []
            current_tokens = header_tokens + self._count_tokens(csv_header)
            
            chunk_idx = 0
            row_start = 0

            for i, row in enumerate(df.itertuples(index=False)):
                row_csv = format_row_to_csv(row)
                row_tokens = self._count_tokens(row_csv)

                # Protect against DOS/OOM: Skip rows that individually exceed the max_tokens limit
                if row_tokens > self.max_tokens:
                    logger.warning("Skipping oversized row %d in dataset '%s' (%d tokens)", i, dataset_id, row_tokens)
                    continue

                # If adding this row pushes us over max_tokens, and we have enough to form a valid chunk
                if current_tokens + row_tokens > self.max_tokens and current_chunk_rows:
                    chunk_text = f"{header}{csv_header}" + "".join(current_chunk_rows)
                    
                    row_end = row_start + len(current_chunk_rows) - 1
                    chunk_id_str = f"{dataset_id}_{row_start}_{row_end}"
                    chunk_hash = hashlib.sha256(chunk_id_str.encode()).hexdigest()[:12]
                    chunk_id = f"{dataset_id}_chunk_{chunk_hash}"
                    
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        text=chunk_text,
                        metadata={
                            "dataset_id": dataset_id,
                            "filename": filename,
                            "chunk_id": chunk_id,
                            "row_start": row_start,
                            "row_end": row_end,
                            "column_names": column_names,
                            "chunk_type": "tabular",
                            "sheet_name": sheet_name
                        }
                    ))
                    
                    # Reset for next chunk
                    chunk_idx += 1
                    current_chunk_rows = []
                    current_tokens = header_tokens + self._count_tokens(csv_header)
                    row_start = i

                current_chunk_rows.append(row_csv)
                current_tokens += row_tokens

            # Flush remaining lines
            if current_chunk_rows:
                chunk_text = f"{header}{csv_header}" + "".join(current_chunk_rows)
                
                row_end = row_start + len(current_chunk_rows) - 1
                chunk_id_str = f"{dataset_id}_{row_start}_{row_end}"
                chunk_hash = hashlib.sha256(chunk_id_str.encode()).hexdigest()[:12]
                chunk_id = f"{dataset_id}_chunk_{chunk_hash}"

                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    text=chunk_text,
                    metadata={
                        "dataset_id": dataset_id,
                        "filename": filename,
                        "chunk_id": chunk_id,
                        "row_start": row_start,
                        "row_end": row_end,
                        "column_names": column_names,
                        "chunk_type": "tabular",
                        "sheet_name": sheet_name
                    }
                ))

            logger.info("Chunked document '%s' into %d chunks.", doc.doc_id, len(chunks))

        return chunks
