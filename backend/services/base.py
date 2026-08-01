"""Core data models for DataLens Analytics AI services architecture.

Defines standardized data containers used across DocumentLoader, EmbeddingService,
VectorStore, LLMService, ChatMemory, and InsightEngine.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """Represents an un-chunked document or dataset slice."""

    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Represents a text chunk suitable for embedding and retrieval."""

    chunk_id: str
    doc_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Represents a vector similarity query match result."""

    chunk: Chunk
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
