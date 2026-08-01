"""Lightweight query-routing service for the RAG chat flow."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryRouter:
    """Decide whether a question should use retrieval, statistics, or a simple fallback."""

    def route(
        self,
        question: str,
        df: Optional[Any] = None,
        history: Optional[List[Dict[str, str]]] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized = (question or "").strip().lower()
        if not normalized:
            return {"needs_retrieval": False, "needs_stats": False, "reason": "empty"}

        retrieval_keywords = [
            "what is",
            "which",
            "who",
            "where",
            "summarize",
            "explain",
            "find",
            "show",
            "compare",
            "trend",
            "pattern",
            "relationship",
            "describe",
            "insight",
            "detail",
            "sample",
            "context",
        ]
        stats_keywords = [
            "average",
            "mean",
            "median",
            "std",
            "deviation",
            "correlation",
            "percent",
            "distribution",
            "variance",
            "sum",
            "total",
            "count",
            "max",
            "min",
        ]

        needs_retrieval = any(keyword in normalized for keyword in retrieval_keywords)
        needs_stats = any(keyword in normalized for keyword in stats_keywords)

        if needs_stats and not needs_retrieval:
            needs_retrieval = True

        return {
            "needs_retrieval": needs_retrieval,
            "needs_stats": needs_stats,
            "reason": "semantic" if needs_retrieval else "fallback",
            "retrieval_top_k": 3,
        }
