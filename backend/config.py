"""Central application configuration loaded from environment variables.

All tuneable values live here.  Import ``settings`` from this module
everywhere instead of calling ``os.getenv`` directly throughout the codebase.

Environment variables are read in this precedence order:
  1. Real environment (set by Docker / Vercel / system)
  2. ``backend/.env`` file (local development)
  3. Hard-coded defaults below

Security-sensitive variables (API keys) are *never* given defaults.
"""

import os
from pathlib import Path
from typing import List


# ---------------------------------------------------------------------------
# .env loader (lightweight — avoids a hard python-dotenv dependency)
# ---------------------------------------------------------------------------

def _load_dotenv(env_path: Path) -> None:
    """Load variables from a .env file into os.environ if not already set."""
    if not env_path.is_file():
        return
    with env_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")
_load_dotenv(Path(__file__).resolve().parent / ".env")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _env_list(key: str, default: str) -> List[str]:
    """Read a comma-separated environment variable into a list of strings."""
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class _Settings:
    """Immutable settings bag. All values are resolved at import time."""

    # --- AI / Google ---
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "gemini-2.5-flash")

    @property
    def ai_api_url(self) -> str:
        override = os.getenv("AI_API_URL")
        if override:
            return override
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.ai_model}:generateContent"

    # --- Vector database ---
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # --- Dataset storage engine ---
    storage_engine: str = os.getenv("STORAGE_ENGINE", "memory").lower()
    dataset_storage_dir: str = os.getenv("DATASET_STORAGE_DIR", "./dataset_storage")

    # --- Upload limits ---
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
    upload_preview_limit: int = int(os.getenv("UPLOAD_PREVIEW_LIMIT", "100"))

    # --- CORS ---
    # Comma-separated list.  Use "*" only during local dev; set explicit
    # origins in production via CORS_ORIGINS or CORS_ALLOWED_ORIGINS env var.
    cors_origins: List[str] = _env_list("CORS_ORIGINS", os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"))
    cors_allow_credentials: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"

    def __init__(self):
        # Validate CORS in production
        if self.is_production and "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins (*) are not permitted in production.")
        if self.cors_allow_credentials and "*" in self.cors_origins:
            raise ValueError("CORS credentials are not permitted with wildcard origins.")

    # --- Rate limiting ---
    # Uses slowapi token-bucket semantics: N requests per window per IP.
    rate_limit_upload: str = os.getenv("RATE_LIMIT_UPLOAD", "10/minute")
    rate_limit_chat: str = os.getenv("RATE_LIMIT_CHAT", "30/minute")
    rate_limit_filter: str = os.getenv("RATE_LIMIT_FILTER", "120/minute")
    rate_limit_default: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")

    # --- Proxy / Trusted IPs ---
    # Comma-separated list of trusted reverse proxy IP addresses.
    # When empty (default), forwarding headers (X-Forwarded-For, X-Real-IP) are untrusted
    # to prevent IP spoofing attacks and rate limit bypasses.
    trusted_proxies: List[str] = _env_list("TRUSTED_PROXIES", "")

    # --- Logging ---
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format: str = os.getenv("LOG_FORMAT", "json")   # "json" | "text"

    # --- App metadata ---
    app_env: str = os.getenv("APP_ENV", "development")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = _Settings()
