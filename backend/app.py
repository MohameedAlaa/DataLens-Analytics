# FastAPI backend for DataLens Analytics

import io
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from api_helpers import (
    AIRateLimitError,
    AIUnavailableError,
    apply_filters,
    calculate_dataset_stats,
    check_dataset_ready,
    detect_csv_encoding,
    generate_chat_response_async,
    parse_dataset_bytes,
)
from config import settings

from logging_config import configure_logging
from security import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    create_rate_limiter,
    get_client_ip,
    register_exception_handlers,
    sanitise_filters,
    sanitise_question,
    validate_file_magic,
)
from services.ai.rag.ingestion_pipeline import ingestion_pipeline

# ---------------------------------------------------------------------------
# Logging — must be configured before the first log call
# ---------------------------------------------------------------------------
configure_logging()
logger = logging.getLogger(__name__)

from dataset_manager import DatasetManager, dataset_manager

# ---------------------------------------------------------------------------
# Rate limiter (optional — degrades gracefully if slowapi is not installed)
# ---------------------------------------------------------------------------
limiter = create_rate_limiter()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DataLens Analytics API",
    description="Backend service for data parsing, filtering, statistics, and AI chat analysis.",
    version="1.0.0",
    # Disable automatic /docs and /redoc in production to reduce attack surface
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Application scoped DatasetManager (defaults to module singleton, overridable in tests/DI)
app.state.dataset_manager = dataset_manager

def get_dataset_manager(request: Request) -> DatasetManager:
    return request.app.state.dataset_manager


# ---------------------------------------------------------------------------
# Middleware (applied in reverse registration order — last added runs first)
# ---------------------------------------------------------------------------

# 1. Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)

# 2. Request-ID tracing
app.add_middleware(RequestIDMiddleware)

# 3. CORS — origins loaded from env var CORS_ORIGINS (comma-separated).
#    Defaults to localhost only.  Set CORS_ORIGINS=* only for local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
)

# 4. Attach rate-limiter state (required by slowapi) — no-op if limiter is None
if limiter is not None:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 5. Global structured exception handlers
register_exception_handlers(app)

logger.info(
    "DataLens Analytics API starting",
    extra={
        "env": settings.app_env,
        "cors_origins": settings.cors_origins,
        "max_upload_mb": settings.max_upload_bytes // (1024 * 1024),
        "rate_limit_upload": settings.rate_limit_upload,
        "rate_limit_chat": settings.rate_limit_chat,
        "rate_limit_filter": settings.rate_limit_filter,
        "rate_limit_default": settings.rate_limit_default,
        "log_format": settings.log_format,
    },
)


# ---------------------------------------------------------------------------
# Helper: decorate endpoint with optional rate limit
# ---------------------------------------------------------------------------
def _rate_limited(limit_string: str):
    """Return a slowapi rate-limit decorator, or a no-op if slowapi is absent."""
    if limiter is not None:
        return limiter.limit(limit_string)
    # No-op decorator
    def _noop(fn):
        return fn
    return _noop


def _exempt(fn):
    """Exempt an endpoint from global default rate limiting."""
    if limiter is not None:
        return limiter.exempt(fn)
    return fn


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@app.post("/upload")
@_rate_limited(settings.rate_limit_upload)
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dataset_manager: DatasetManager = Depends(get_dataset_manager)
) -> Dict[str, Any]:
    """Validate, parse an uploaded dataset file (CSV/Excel), assign a UUID, and store internally.

    Validation pipeline:
      1. Filename present and has allowed extension
      2. Magic-byte check (prevents MIME spoofing / executable uploads)
      3. File-size limit (default 50 MB, set via MAX_UPLOAD_MB)
      4. CSV/Excel parseable
      5. Non-empty (rows and columns)
      6. No duplicate column headers
    """
    request_id = getattr(request.state, "request_id", "?")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    logger.info(
        "Upload request received",
        extra={"request_id": request_id, "target_filename": file.filename},
    )

    try:
        # Security: Read in chunks to enforce size limit before memory exhaustion
        contents = bytearray()
        max_bytes = settings.max_upload_bytes
        while chunk := await file.read(1024 * 1024):
            contents.extend(chunk)
            if len(contents) > max_bytes:
                raise ValueError(f"File exceeds maximum allowed limit of {max_bytes // (1024 * 1024)} MB.")
        contents = bytes(contents)

        # Security: magic-byte validation before any parsing
        validate_file_magic(contents, file.filename)

        # Full validation + preview parsing (size, encoding, duplicates, emptiness)
        parsed_result = parse_dataset_bytes(
            contents,
            file.filename,
            preview_limit=settings.upload_preview_limit,
            max_bytes=settings.max_upload_bytes,
        )

        # Re-parse the full DataFrame for storage
        if file.filename.lower().endswith(".csv"):
            encoding = detect_csv_encoding(contents)
            df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
        else:
            df = pd.read_excel(io.BytesIO(contents))

        dataset_id = parsed_result["dataset_id"]
        dataset_manager.register_dataset(
            df=df,
            filename=file.filename,
            dataset_id=dataset_id,
        )
        
        # Enqueue the background RAG ingestion pipeline
        background_tasks.add_task(ingestion_pipeline.run_ingestion, dataset_id, df, file.filename, dataset_manager)

        logger.info(
            "Dataset stored and ingestion queued",
            extra={
                "request_id": request_id,
                "target_filename": file.filename,
                "dataset_id": dataset_id,
                "rows": df.shape[0],
                "cols": df.shape[1],
                "size_kb": round(len(contents) / 1024, 1),
            },
        )
        return parsed_result

    except ValueError as exc:
        err_msg = str(exc)
        logger.warning(
            "Upload validation failed",
            extra={"request_id": request_id, "target_filename": file.filename, "reason": err_msg},
        )
        status = 413 if "exceeds maximum allowed limit" in err_msg else 400
        raise HTTPException(status_code=status, detail=err_msg)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected upload error",
            extra={"request_id": request_id, "target_filename": file.filename},
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the upload.",
        )


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

class FilterRequest(BaseModel):
    filters: Dict[str, Any]
    dataset_id: Optional[str] = None
    filename: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None

    @model_validator(mode="before")
    @classmethod
    def map_filename(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("dataset_id") and data.get("filename"):
                data["dataset_id"] = data["filename"]
        return data

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return sanitise_filters(v)

    @field_validator("dataset_id", mode="before")
    @classmethod
    def strip_ids(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


@app.post("/filter")
@_rate_limited(settings.rate_limit_filter)
async def filter_data(
    request: Request, 
    req: FilterRequest,
    dataset_manager: DatasetManager = Depends(get_dataset_manager)
) -> JSONResponse:
    """Filter a stored dataset by criteria.

    Supply ``dataset_id`` or inline ``data`` rows.
    """
    request_id = getattr(request.state, "request_id", "?")
    lookup_key = req.dataset_id

    if lookup_key:
        meta = dataset_manager.get_metadata(lookup_key)
        check_dataset_ready(meta)
        
        df = dataset_manager.get_dataset(lookup_key)
        if df is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found. Provide a valid 'dataset_id' returned from /upload.",
            )
        target_data = df
    elif req.data is not None:
        target_data = req.data
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide 'dataset_id', 'filename', or 'data' to filter.",
        )

    try:
        summary = apply_filters(target_data, req.filters)
        return JSONResponse(content=summary)
    except Exception as exc:
        logger.exception(
            "Filter error",
            extra={"request_id": request_id, "lookup_key": lookup_key},
        )
        raise HTTPException(status_code=400, detail="Failed to apply filter criteria.")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@app.get("/stats/{dataset_id}")
@_rate_limited(settings.rate_limit_default)
async def get_stats(
    request: Request, 
    dataset_id: str,
    dataset_manager: DatasetManager = Depends(get_dataset_manager)
) -> Dict[str, Any]:
    """Retrieve statistical summaries and correlation matrix for a stored dataset."""
    request_id = getattr(request.state, "request_id", "?")

    if not dataset_id or not dataset_id.strip():
        raise HTTPException(status_code=400, detail="dataset_id must not be empty.")

    meta = dataset_manager.get_metadata(dataset_id.strip())
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' not found. Provide a valid dataset_id from /upload.",
        )
    
    df = dataset_manager.get_dataset(dataset_id.strip())
    if df is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' not found. Provide a valid dataset_id from /upload.",
        )

    try:
        return calculate_dataset_stats(df)
    except Exception as exc:
        logger.exception(
            "Stats computation error",
            extra={"request_id": request_id, "dataset_id": dataset_id},
        )
        raise HTTPException(status_code=500, detail="Failed to compute dataset statistics.")


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"user", "assistant"}:
            raise ValueError("Message role must be 'user' or 'assistant'.")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content must not be empty.")
        return v.strip()


class ChatRequest(BaseModel):
    question: str
    dataset_id: Optional[str] = None
    filename: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    history: List[ChatMessage] = Field(default_factory=list)

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        from security import sanitise_filters
        return sanitise_filters(v)

    @model_validator(mode="before")
    @classmethod
    def map_filename(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("dataset_id") and data.get("filename"):
                data["dataset_id"] = data["filename"]
        return data

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        return sanitise_question(v)

    @field_validator("history")
    @classmethod
    def validate_history(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        if len(v) > 100:
            raise ValueError("History must not exceed 100 messages.")
        return v


@app.post("/chat")
@_rate_limited(settings.rate_limit_chat)
async def chat(
    request: Request, 
    req: ChatRequest,
    dataset_manager: DatasetManager = Depends(get_dataset_manager)
) -> Dict[str, Any]:
    """Process a natural language question about a stored dataset.

    The dataset is retrieved internally from the DatasetManager by dataset_id.
    The frontend sends only: question, dataset_id, history.
    No dataset rows are transmitted on the wire.
    """
    request_id = getattr(request.state, "request_id", "?")
    lookup_key = req.dataset_id

    if not lookup_key:
        raise HTTPException(
            status_code=400,
            detail="Provide 'dataset_id' to identify the dataset.",
        )

    meta = dataset_manager.get_metadata(lookup_key)
    check_dataset_ready(meta)

    df = dataset_manager.get_dataset(lookup_key.strip())
    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Provide a valid dataset_id returned from /upload.",
        )
        
    if req.filters:
        from api_helpers import apply_filters
        try:
            df = pd.DataFrame(apply_filters(df, req.filters)["filtered_data"])
        except Exception as exc:
            logger.exception("Failed to apply filters in chat", extra={"request_id": request_id, "lookup_key": lookup_key})
            raise HTTPException(status_code=400, detail="Failed to apply filter criteria.")

    display_name = meta.get("filename", lookup_key) if meta else lookup_key
    resolved_id = meta.get("dataset_id", lookup_key) if meta else lookup_key
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in req.history]

    logger.info(
        "Chat request",
        extra={
            "request_id": request_id,
            "dataset_id": resolved_id,
            "question_length": len(req.question),
            "history_turns": len(history_dicts),
        },
    )

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
        logger.warning(
            "AI rate limit",
            extra={"request_id": request_id, "dataset_id": resolved_id},
        )
        raise HTTPException(
            status_code=429,
            detail="AI backend is rate limiting requests. Please wait a moment and try again.",
        )
    except AIUnavailableError as exc:
        logger.error(
            "AI backend unavailable",
            extra={"request_id": request_id, "dataset_id": resolved_id},
        )
        raise HTTPException(
            status_code=503,
            detail="AI backend is temporarily unavailable. Please try again shortly.",
        )
    except Exception as exc:
        logger.exception(
            "Unexpected chat error",
            extra={"request_id": request_id, "dataset_id": resolved_id},
        )
        raise HTTPException(status_code=500, detail="Failed to process chat query.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
@_exempt
async def health(dataset_manager: DatasetManager = Depends(get_dataset_manager)) -> Dict[str, Any]:
    """Lightweight liveness probe — does not check external dependencies."""
    return {
        "status": "ok",
        "env": settings.app_env,
        "datasets_loaded": len(dataset_manager.list_datasets()),
    }
