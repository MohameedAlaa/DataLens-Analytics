"""Structured logging configuration for DataLens Analytics backend.

Supports two output formats controlled by the LOG_FORMAT env var:
  - "json"  → machine-readable JSON lines (default; ideal for production)
  - "text"  → human-readable coloured text (useful for local dev)

Usage (call once at startup before any other logger is used):
    from logging_config import configure_logging
    configure_logging()
"""

import logging
import sys
from typing import Optional

try:
    from backend.config import settings
except ImportError:
    from config import settings


# ---------------------------------------------------------------------------
# Optional: python-json-logger for structured JSON output
# ---------------------------------------------------------------------------
try:
    from pythonjsonlogger import jsonlogger as _jsonlogger
    _JSON_LOGGER_AVAILABLE = True
except ImportError:
    _JSON_LOGGER_AVAILABLE = False


class _TextFormatter(logging.Formatter):
    """Simple coloured text formatter for local development."""

    _GREY = "\x1b[38;5;245m"
    _BLUE = "\x1b[34m"
    _YELLOW = "\x1b[33m"
    _RED = "\x1b[31m"
    _BOLD_RED = "\x1b[31;1m"
    _RESET = "\x1b[0m"

    _LEVEL_COLORS = {
        logging.DEBUG: _GREY,
        logging.INFO: _BLUE,
        logging.WARNING: _YELLOW,
        logging.ERROR: _RED,
        logging.CRITICAL: _BOLD_RED,
    }

    FMT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        color = self._LEVEL_COLORS.get(record.levelno, self._RESET)
        formatter = logging.Formatter(f"{color}{self.FMT}{self._RESET}", datefmt="%H:%M:%S")
        return formatter.format(record)


def configure_logging(
    level: Optional[str] = None,
    fmt: Optional[str] = None,
) -> None:
    """Configure root logger with structured output.

    Args:
        level: Override LOG_LEVEL env var (e.g. "DEBUG", "INFO").
        fmt:   Override LOG_FORMAT env var ("json" or "text").
    """
    log_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)
    log_format = (fmt or settings.log_format).lower()

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers to avoid duplicates on reload
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if log_format == "json" and _JSON_LOGGER_AVAILABLE:
        json_fmt = _jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(json_fmt)
    else:
        if log_format == "json" and not _JSON_LOGGER_AVAILABLE:
            # Warn once then fall back to text
            print(
                "[logging_config] python-json-logger not installed; "
                "falling back to text format.  Run: pip install python-json-logger",
                file=sys.stderr,
            )
        handler.setFormatter(_TextFormatter())

    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "uvicorn.access", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
