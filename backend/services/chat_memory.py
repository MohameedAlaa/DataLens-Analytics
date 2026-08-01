"""Chat memory service for managing conversation history and prompt bounding.

Provides BaseChatMemory ABC and SlidingWindowChatMemory for sliding-window turn eviction
and prompt formatting.
"""

from abc import ABC, abstractmethod
import threading
from typing import Dict, List, Optional


class BaseChatMemory(ABC):
    """Abstract interface for conversation memory management."""

    @abstractmethod
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message turn to session conversation history."""
        pass

    @abstractmethod
    def get_history(self, session_id: str, max_turns: Optional[int] = None) -> List[Dict[str, str]]:
        """Retrieve stored message turns for session_id."""
        pass

    @abstractmethod
    def format_history_prompt(self, session_id: str, max_turns: Optional[int] = None) -> str:
        """Format history turns into a role-labelled prompt string."""
        pass

    @abstractmethod
    def clear(self, session_id: str) -> None:
        """Clear conversation history for session_id."""
        pass


class SlidingWindowChatMemory(BaseChatMemory):
    """Thread-safe conversation memory using sliding-window history bounding."""

    def __init__(self, default_max_turns: int = 10) -> None:
        self.default_max_turns = default_max_turns
        self._store: Dict[str, List[Dict[str, str]]] = {}
        self._lock = threading.RLock()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add message to session history."""
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = []
            self._store[session_id].append({"role": role, "content": content})

    def get_history(self, session_id: str, max_turns: Optional[int] = None) -> List[Dict[str, str]]:
        """Retrieve up to max_turns message turns."""
        limit = max_turns or self.default_max_turns
        with self._lock:
            history = self._store.get(session_id, [])
            return list(history[-limit:])

    def format_history_prompt(self, session_id: str, max_turns: Optional[int] = None) -> str:
        """Format conversation turns into labelled prompt string."""
        history = self.get_history(session_id, max_turns=max_turns)
        if not history:
            return ""
        lines: List[str] = []
        for msg in history:
            role = msg.get("role", "user")
            label = "User" if role == "user" else "Assistant"
            lines.append(f"{label}: {msg.get('content', '').strip()}")
        return "\n".join(lines) + "\n"

    def clear(self, session_id: str) -> None:
        """Clear session memory."""
        with self._lock:
            self._store.pop(session_id, None)
