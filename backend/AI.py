import asyncio
import logging
import time
from typing import Any, Dict
import httpx

try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)


def _extract_response_text(data: Dict[str, Any]) -> str:
    """Extract candidate text response from Gemini API response structure.
    
    Supports both single-part and multi-part text candidates.
    """
    if isinstance(data, dict):
        candidates = data.get("candidates")
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, dict):
                content = first.get("content")
                if isinstance(content, dict):
                    parts = content.get("parts")
                    if isinstance(parts, list) and parts:
                        text_fragments = [
                            p.get("text", "")
                            for p in parts
                            if isinstance(p, dict) and "text" in p
                        ]
                        full_text = "".join(text_fragments).strip()
                        if full_text:
                            return full_text

    raise RuntimeError("Unexpected or empty candidate structure from Google Gemini API")


async def call_ai_async(prompt: str) -> str:
    """Asynchronously call the Google Gemini API with a prompt."""
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable not set for Google Gemini inference")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.google_api_key,
    }
    # Official Gemini 3.x Flash payload schema
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 800,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(2):
            try:
                response = await client.post(settings.ai_api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return _extract_response_text(data)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 503 and attempt == 0:
                    logger.warning("Gemini API returned 503; retrying in 1.5s...")
                    await asyncio.sleep(1.5)
                    continue
                logger.error("Gemini API request returned error status: %s", exc.response.status_code)
                raise RuntimeError(f"Gemini API returned error status {exc.response.status_code}") from exc
            except httpx.RequestError as exc:
                logger.error("Gemini API network request failed: %s", exc)
                raise RuntimeError("Failed to connect to Google Gemini API") from exc


def call_ai(prompt: str) -> str:
    """Synchronous wrapper for Google Gemini API inference."""
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable not set for Google Gemini inference")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.google_api_key,
    }
    # Official Gemini 3.x Flash payload schema
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 800,
        },
    }

    for attempt in range(2):
        try:
            response = httpx.post(settings.ai_api_url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return _extract_response_text(data)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 503 and attempt == 0:
                logger.warning("Gemini API returned 503; retrying in 1.5s...")
                time.sleep(1.5)
                continue
            logger.error("Gemini API request returned error status: %s", exc.response.status_code)
            raise RuntimeError(f"Gemini API returned error status {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            logger.error("Gemini API network request failed: %s", exc)
            raise RuntimeError("Failed to connect to Google Gemini API") from exc


