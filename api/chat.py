"""Serverless chat endpoint for DataLens Analytics (Vercel / api/ router).

Architecture change:
  OLD: POST /chat  { question, history, dataset: [...all rows...] }
  NEW: POST /chat  { question, history, dataset_id: "<uuid>" }

The backend retrieves the dataset from the DatasetManager by dataset_id.
The frontend only needs to store and forward the dataset_id returned at upload.

NOTE: In a true multi-worker serverless deployment (separate process per
invocation) the in-memory DatasetManager state is not shared across workers.
For those environments, swap InMemoryStorageEngine for a Redis or DuckDB
engine at startup.  Within a single-process deployment (dev server, single
Vercel function), this works correctly as-is.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.api_helpers import (
        AIRateLimitError,
        AIUnavailableError,
        check_dataset_ready,
        generate_chat_response_async,
    )
    from backend.dataset_manager import dataset_manager
except ImportError:
    from api_helpers import (
        AIRateLimitError,
        AIUnavailableError,
        check_dataset_ready,
        generate_chat_response_async,
    )
    from dataset_manager import dataset_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint.

    The ``dataset`` field has been removed.  Clients must supply the
    ``dataset_id`` UUID returned by the /upload endpoint.  The backend
    retrieves the full dataset internally — no row data is transmitted.
    """
    question: str
    dataset_id: str                             # Required — from /upload response
    history: List[ChatMessage] = Field(default_factory=list)
    filename: Optional[str] = None              # Deprecated — ignored if dataset_id resolves
    filters: Optional[Dict[str, Any]] = None    # Filters active in the UI


@router.post("/")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    """Handle an AI chat query about a previously uploaded dataset.

    The dataset is resolved from the DatasetManager by dataset_id.
    No dataset rows are accepted or expected in the request body.
    """
    # Enforce lifecycle state (PENDING -> PROCESSING -> READY)
    meta = dataset_manager.get_metadata(req.dataset_id)
    check_dataset_ready(meta)

    # Retrieve the dataset from internal storage (no data in request body)
    df = dataset_manager.get_dataset(req.dataset_id)
    if df is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset '{req.dataset_id}' not found. "
                "Upload a file first and use the returned dataset_id."
            ),
        )

    display_name = meta.get("filename", req.dataset_id) if meta else req.dataset_id
    resolved_id = meta.get("dataset_id", req.dataset_id) if meta else req.dataset_id

    history_dicts = [{"role": msg.role, "content": msg.content} for msg in req.history]

    try:
        return await generate_chat_response_async(
            question=req.question,
            history=history_dicts,
            data_or_df=df,
            filename=display_name,
            dataset_id=resolved_id,
            filters=req.filters,
        )
    except AIRateLimitError as exc:
        logger.warning("AI rate limit hit for dataset_id='%s': %s", resolved_id, exc)
        raise HTTPException(
            status_code=429,
            detail="AI backend is rate limiting requests. Please wait a moment and try again.",
        )
    except AIUnavailableError as exc:
        logger.error("AI backend unavailable for dataset_id='%s': %s", resolved_id, exc)
        raise HTTPException(
            status_code=503,
            detail="AI backend is temporarily unavailable. Please try again shortly.",
        )
    except Exception as exc:
        logger.exception("Unexpected error in /chat for dataset_id='%s': %s", resolved_id, exc)
        raise HTTPException(status_code=500, detail="Chat request failed to process.")
