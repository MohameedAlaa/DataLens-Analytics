"""DataLens Analytics AI services package.

Exports core interfaces and implementations for DocumentLoader, EmbeddingService,
VectorStore, LLMService, ChatMemory, and InsightEngine.
"""

from .base import Document, Chunk, SearchResult
from .document_loader import BaseDocumentLoader, DatasetDocumentLoader
from .embedding_service import BaseEmbeddingService, MockEmbeddingService
from .vector_store import BaseVectorStore, InMemoryVectorStore
from .llm_service import BaseLLMService, GeminiLLMService, MockLLMService
from .chat_memory import BaseChatMemory, SlidingWindowChatMemory
from .insight_engine import InsightEngine

__all__ = [
    "Document",
    "Chunk",
    "SearchResult",
    "BaseDocumentLoader",
    "DatasetDocumentLoader",
    "BaseEmbeddingService",
    "MockEmbeddingService",
    "BaseVectorStore",
    "InMemoryVectorStore",
    "BaseLLMService",
    "GeminiLLMService",
    "MockLLMService",
    "BaseChatMemory",
    "SlidingWindowChatMemory",
    "InsightEngine",
]
