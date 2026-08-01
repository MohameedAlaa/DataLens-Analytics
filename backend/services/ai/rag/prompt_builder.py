"""Prompt builder for the RAG chat flow."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Construct a RAG-style prompt from retrieved chunks and dataset context."""

    def build(
        self,
        question: str,
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        dataset_context: Optional[str] = None,
    ) -> str:
        history_text = ""
        if history:
            history_text = "\n".join(
                f"{item.get('role', 'user').title()}: {item.get('content', '').strip()}"
                for item in history[-4:]
            )
            if history_text:
                history_text = f"\nConversation history:\n{history_text}\n"

        chunk_text = ""
        if retrieved_chunks:
            chunk_parts = []
            for chunk in retrieved_chunks:
                text = (chunk.get("document") or chunk.get("text") or "").strip()
                if text:
                    chunk_parts.append(text)
            if chunk_parts:
                chunk_text = "\n\nRelevant context:\n" + "\n\n".join(chunk_parts)

        context_block = dataset_context or ""
        if context_block:
            context_block = f"\n\nDataset context:\n{context_block}"

        return (
            f"{system_prompt}{history_text}{context_block}{chunk_text}\n\n"
            f"User question: {question}\n"
            "Answer using the provided context and be concise."
        )
