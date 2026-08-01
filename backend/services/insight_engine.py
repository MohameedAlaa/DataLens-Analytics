"""Insight engine module acting as a orchestrator facade for AI/RAG capabilities.

Integrates DatasetManager, DocumentLoader, EmbeddingService, VectorStore, LLMService,
and ChatMemory to answer analytical questions about datasets.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import Chunk, Document
from .document_loader import DatasetDocumentLoader, BaseDocumentLoader
from .embedding_service import MockEmbeddingService, BaseEmbeddingService
from .vector_store import InMemoryVectorStore, BaseVectorStore
from .llm_service import GeminiLLMService, BaseLLMService
from .chat_memory import SlidingWindowChatMemory, BaseChatMemory

logger = logging.getLogger(__name__)


class InsightEngine:
    """Orchestrator class coordinating dataset loading, search, LLM completion and memory."""

    def __init__(
        self,
        document_loader: Optional[BaseDocumentLoader] = None,
        embedding_service: Optional[BaseEmbeddingService] = None,
        vector_store: Optional[BaseVectorStore] = None,
        llm_service: Optional[BaseLLMService] = None,
        chat_memory: Optional[BaseChatMemory] = None,
    ) -> None:
        self.document_loader = document_loader or DatasetDocumentLoader()
        self.embedding_service = embedding_service or MockEmbeddingService()
        self.vector_store = vector_store or InMemoryVectorStore()
        self.llm_service = llm_service or GeminiLLMService()
        self.chat_memory = chat_memory or SlidingWindowChatMemory()

    async def ingest_dataset(
        self, dataset_id: str, df: Any, filename: str
    ) -> int:
        """Parse, chunk, embed, and index a dataset for search retrieval.

        Note: RAG integration is disabled by default for the core chatbot flow.
        This provides the ingestion scaffold for future RAG indexation.
        """
        try:
            # 1. Load DataFrame rows as Documents
            docs = self.document_loader.load(df, dataset_id=dataset_id, filename=filename)
            if not docs:
                return 0

            # 2. Chunk Documents
            chunks = self.document_loader.chunk(docs)

            # 3. Generate Vector Embeddings
            chunks = await self.embedding_service.embed_chunks(chunks)

            # 4. Insert into Vector Store
            indexed_count = await self.vector_store.add_chunks(chunks)
            logger.info("Ingested dataset %s: indexed %d chunks", dataset_id, indexed_count)
            return indexed_count
        except Exception as exc:
            logger.exception("Error ingesting dataset %s: %s", dataset_id, exc)
            return 0

    async def query_dataset_rag(
        self, dataset_id: str, question: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context chunks matching question using similarity search."""
        try:
            # 1. Embed user query
            query_vector = await self.embedding_service.embed_text(question)

            # 2. Query Vector Store
            results = await self.vector_store.search(
                query_vector, top_k=top_k, doc_id=dataset_id
            )

            # 3. Format matches
            matches = []
            for r in results:
                matches.append(
                    {
                        "chunk_id": r.chunk.chunk_id,
                        "text": r.chunk.text,
                        "score": r.score,
                        "metadata": r.metadata,
                    }
                )
            return matches
        except Exception as exc:
            logger.exception("Error querying RAG context for %s: %s", dataset_id, exc)
            return []

    async def generate_chat_response(
        self,
        question: str,
        history: List[Dict[str, str]],
        system_prompt: str,
        session_id: str,
        use_rag: bool = False,
    ) -> str:
        """Coordinate LLM prompt generation and memory persistence."""
        # 1. Populate Memory with incoming turn and history
        # (For stateless requests we populate memory on-the-fly)
        self.chat_memory.clear(session_id)
        for turn in history:
            self.chat_memory.add_message(
                session_id, turn.get("role", "user"), turn.get("content", "")
            )

        # 2. Format history prompt
        history_prompt = self.chat_memory.format_history_prompt(session_id)

        # 3. Retrieve additional RAG context if requested
        rag_context = ""
        if use_rag:
            matches = await self.query_dataset_rag(session_id, question)
            if matches:
                rag_context = "\n\nAdditional Relevant Context:\n" + "\n".join(
                    [m["text"] for m in matches]
                )

        full_system_prompt = system_prompt
        if rag_context:
            full_system_prompt += rag_context

        # 4. Invoke LLM Service
        prompt = f"{history_prompt}User: {question}\nAssistant:"
        answer = await self.llm_service.generate_response(
            prompt, system_prompt=full_system_prompt
        )

        # 5. Persist final turn in memory
        self.chat_memory.add_message(session_id, "user", question)
        self.chat_memory.add_message(session_id, "assistant", answer)

        return answer
