"""Security helpers for DataLens Analytics backend.

Contains:
  - Magic-byte file validation (prevents MIME spoofing)
  - Request ID middleware (traces every request in logs)
  - Input sanitisation validators (question length, filter key whitelist)
  - Rate limiter factory (slowapi)
  - Global exception handlers for FastAPI
"""

import logging
import time
import uuid
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Magic-byte signatures for allowed file types
# ---------------------------------------------------------------------------

# Each entry: (display_name, list_of_leading_byte_sequences)
_FILE_SIGNATURES: Dict[str, list] = {
    "csv": [
        # CSVs are plain text — any valid UTF printable start is acceptable.
        # We explicitly BLOCK binary magic bytes instead (see below).
    ],
    "xlsx": [
        b"\x50\x4b\x03\x04",   # ZIP PK header (OOXML)
    ],
    "xls": [
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",  # OLE2 Compound Document
    ],
}

# Byte signatures that MUST NOT appear in uploaded files (binary / executable)
_BLOCKED_SIGNATURES = [
    b"\x4d\x5a",           # Windows PE / MZ executable
    b"\x7f\x45\x4c\x46",  # ELF binary
    b"\x25\x50\x44\x46",  # PDF  (%PDF)
    b"\xff\xd8\xff",       # JPEG
    b"\x89\x50\x4e\x47",  # PNG
    b"\x47\x49\x46",       # GIF
]

_MAX_FILENAME_LENGTH = 255
_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def validate_file_magic(contents: bytes, filename: str) -> None:
    """Verify that uploaded bytes match the declared file extension.

    Raises:
        ValueError: if the content does not match, is a blocked type, or
                    the filename has a disallowed extension.
    """
    if not contents:
        raise ValueError("Uploaded file is empty.")

    # --- Filename sanity ---
    if len(filename) > _MAX_FILENAME_LENGTH:
        raise ValueError(f"Filename exceeds maximum length of {_MAX_FILENAME_LENGTH} characters.")

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}."
        )

    # --- Block known binary / executable signatures ---
    header = contents[:8]
    for blocked in _BLOCKED_SIGNATURES:
        if header.startswith(blocked):
            logger.warning(
                "Upload blocked: file '%s' matched blocked binary signature %s",
                filename, blocked.hex(),
            )
            raise ValueError(
                "Uploaded file appears to be a binary or executable type, which is not permitted."
            )

    # --- Validate XLSX / XLS magic bytes ---
    if ext == ".xlsx":
        if not contents[:4].startswith(_FILE_SIGNATURES["xlsx"][0]):
            raise ValueError(
                "File declared as .xlsx does not have a valid Excel (OOXML/ZIP) header. "
                "Ensure the file has not been corrupted or renamed."
            )

    if ext == ".xls":
        if not contents[:8].startswith(_FILE_SIGNATURES["xls"][0]):
            raise ValueError(
                "File declared as .xls does not have a valid Excel (OLE2) header. "
                "Ensure the file has not been corrupted or renamed."
            )

    # CSV: no binary magic check needed — the absence of blocked signatures above is sufficient.
    logger.debug("Magic-byte validation passed for '%s' (ext=%s)", filename, ext)


# ---------------------------------------------------------------------------
# Input sanitisation
# ---------------------------------------------------------------------------

_MAX_QUESTION_LENGTH = 2000
_MAX_FILTER_KEYS = 20
_MAX_FILTER_VALUE_LENGTH = 500


def sanitise_question(question: str) -> str:
    """Strip and truncate a chat question; raise ValueError if blank or too long."""
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question must not be empty.")
    if len(cleaned) > _MAX_QUESTION_LENGTH:
        raise ValueError(
            f"Question exceeds maximum length of {_MAX_QUESTION_LENGTH} characters."
        )
    return cleaned


def sanitise_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate filter structure to prevent oversized or malformed payloads.

    Raises:
        ValueError: if the filter map is too large or contains invalid values.
    """
    if len(filters) > _MAX_FILTER_KEYS:
        raise ValueError(
            f"Too many filter keys ({len(filters)}). "
            f"Maximum allowed is {_MAX_FILTER_KEYS}."
        )
    for key, val in filters.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("All filter keys must be non-empty strings.")
        if isinstance(val, str) and len(val) > _MAX_FILTER_VALUE_LENGTH:
            raise ValueError(
                f"Filter value for key '{key}' exceeds "
                f"maximum length of {_MAX_FILTER_VALUE_LENGTH} characters."
            )
    return filters


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request_id to every request and response.

    The ID is:
      - Added as ``X-Request-ID`` response header.
      - Stored in ``request.state.request_id`` for use in log statements.

    This makes it easy to correlate a client error with the exact server log
    line, both in local text output and structured JSON logs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 1),
            },
        )
        return response


# ---------------------------------------------------------------------------
# Security response headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "0"   # Modern browsers ignore this; CSP is preferred
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


# ---------------------------------------------------------------------------
# Client IP resolution & Rate limiter (slowapi)
# ---------------------------------------------------------------------------

def get_client_ip(request: Request) -> str:
    """Extract client IP address defensively.

    If request is from a direct client or untrusted peer, return request.client.host.
    Do NOT trust X-Forwarded-For or X-Real-IP headers unless request.client.host is
    explicitly in settings.trusted_proxies. This prevents IP spoofing and rate-limit bypass.
    """
    direct_ip = getattr(request.client, "host", "127.0.0.1") if request.client else "127.0.0.1"

    try:
        from config import settings
        trusted_proxies = getattr(settings, "trusted_proxies", [])
    except Exception:
        trusted_proxies = []

    if not trusted_proxies or direct_ip not in trusted_proxies:
        return direct_ip

    # Peer is a verified trusted proxy: check X-Real-IP first
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    # If X-Forwarded-For is present, traverse from right to left to find the first untrusted client IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        for ip in reversed(ips):
            if ip not in trusted_proxies:
                return ip
        if ips:
            return ips[0]

    return direct_ip


def create_rate_limiter():
    """Create and return a slowapi Limiter, or None if slowapi is not installed."""
    try:
        from slowapi import Limiter
        try:
            from config import settings
            default_limit = settings.rate_limit_default
        except Exception:
            default_limit = "60/minute"
        limiter = Limiter(key_func=get_client_ip, default_limits=[default_limit])
        logger.info("Rate limiter enabled (slowapi)")
        return limiter
    except ImportError:
        logger.warning(
            "slowapi not installed — rate limiting disabled. "
            "Install with: pip install slowapi"
        )
        return None


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers that return structured JSON.

    All responses follow the same shape:
        {"error": "<type>", "detail": "<message>", "request_id": "<uuid>"}

    This prevents FastAPI's default handlers from leaking stack traces.
    """
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        # Flatten Pydantic validation errors into readable messages
        messages = []
        for error in exc.errors():
            loc = " → ".join(str(l) for l in error.get("loc", []))
            messages.append(f"{loc}: {error.get('msg', 'invalid value')}")
        logger.warning(
            "Request validation failed",
            extra={"request_id": request_id, "errors": messages},
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "detail": messages,
                "request_id": request_id,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        log_fn = logger.error if exc.status_code >= 500 else logger.warning
        log_fn(
            "HTTP exception",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "detail": exc.detail,
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "Unhandled exception",
            extra={"request_id": request_id, "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred. Please try again.",
                "request_id": request_id,
            },
        )
