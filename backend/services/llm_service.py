"""LLM service module providing unified provider interfaces for language model inference.

Provides BaseLLMService ABC, GeminiLLMService wrapping Google Gemini API calls,
and MockLLMService for testing.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional

try:
    from AI import call_ai_async
except ImportError:
    from ..AI import call_ai_async

logger = logging.getLogger(__name__)


class BaseLLMService(ABC):
    """Abstract interface for LLM inference providers."""

    @abstractmethod
    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Generate text completion from a prompt."""
        pass


class GeminiLLMService(BaseLLMService):
    """Google Gemini LLM service implementation."""

    def __init__(self, model_name: str = "gemini-1.5-flash") -> None:
        self.model_name = model_name

    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Generate response asynchronously via Gemini API."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        logger.debug("Dispatching LLM prompt to Gemini (len=%d)", len(full_prompt))
        return await call_ai_async(full_prompt)


class MockLLMService(BaseLLMService):
    """Mock LLM service provider for offline testing and development."""

    def __init__(self, default_response: str = "Mocked LLM answer.") -> None:
        self.default_response = default_response

    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Return static or echo response."""
        return self.default_response
