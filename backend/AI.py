import os
import logging
from pathlib import Path
from typing import Any, Dict
import httpx

logger = logging.getLogger(__name__)

def load_dotenv(env_path: Path) -> None:
    """Load environment variables from a .env file if key is not already set."""
    if not env_path.is_file():
        return
    with env_path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

AI_MODEL = os.getenv("AI_MODEL", "gemini-1.5-flash")
API_KEY = os.getenv("GOOGLE_API_KEY")

AI_API_URL = os.getenv(
    "AI_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{AI_MODEL}:generateContent?key={API_KEY}"
)


def _extract_response_text(data: Dict[str, Any]) -> str:
    """Extract candidate text response from Gemini API response structure."""
    if isinstance(data, dict):
        candidates = data.get("candidates")
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, dict):
                content = first.get("content")
                if isinstance(content, dict):
                    parts = content.get("parts")
                    if isinstance(parts, list) and parts:
                        first_part = parts[0]
                        if isinstance(first_part, dict):
                            return first_part.get("text", "").strip()

    raise RuntimeError("Unexpected or empty candidate structure from Google Gemini API")


async def call_ai_async(prompt: str) -> str:
    """Asynchronously call the Google Gemini API with a prompt."""
    if not API_KEY:
        raise RuntimeError("GOOGLE_API_KEY environment variable not set for Google Gemini inference")

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(AI_API_URL, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Gemini API request returned error status: %s", exc.response.status_code)
            raise RuntimeError(f"Gemini API returned error status {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error("Gemini API network request failed: %s", exc)
            raise RuntimeError("Failed to connect to Google Gemini API") from exc

        data = response.json()
        return _extract_response_text(data)


def call_ai(prompt: str) -> str:
    """Synchronous wrapper for Google Gemini API inference."""
    if not API_KEY:
        raise RuntimeError("GOOGLE_API_KEY environment variable not set for Google Gemini inference")

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
        },
    }

    try:
        response = httpx.post(AI_API_URL, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Gemini API request returned error status: %s", exc.response.status_code)
        raise RuntimeError(f"Gemini API returned error status {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.error("Gemini API network request failed: %s", exc)
        raise RuntimeError("Failed to connect to Google Gemini API") from exc

    data = response.json()
    return _extract_response_text(data)

