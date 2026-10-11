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
        
        # We rely on AnalyticsEngine to do the deep parsing, but the router needs to set needs_stats.
        # Use word boundaries so "country" doesn't match "count".
        import re
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
            "maximum",
            "min",
            "minimum",
            "how many",
            "number of",
            "highest",
            "lowest",
            "largest",
            "smallest",
            "most"
        ]

        needs_retrieval = any(re.search(r'\b' + re.escape(kw) + r'\b', normalized) for kw in retrieval_keywords)
        needs_stats = any(re.search(r'\b' + re.escape(kw) + r'\b', normalized) for kw in stats_keywords)
        
        # Handle "percentage" or "%" specifically
        if "percent" in normalized or "%" in normalized:
            needs_stats = True

        reason = "fallback"
        if needs_stats:
            reason = "analytics"
        elif needs_retrieval:
            reason = "semantic"

        return {
            "needs_retrieval": needs_retrieval,
            "needs_stats": needs_stats,
            "reason": reason,
            "retrieval_top_k": 3,
        }
