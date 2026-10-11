"""Thin LLM adapter for the RAG orchestration layer."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from backend.AI import call_ai_async
except ImportError:
    from AI import call_ai_async

logger = logging.getLogger(__name__)


class RagLLMService:
    """Simple wrapper that uses the existing AI backend."""

    async def generate(self, prompt: str, **_: Any) -> str:
        return await call_ai_async(prompt)
