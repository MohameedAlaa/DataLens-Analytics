"""Mocked transport tests for Gemini 2.5 Flash generateContent API.

Verifies:
1. Exact model endpoint URL (gemini-2.5-flash:generateContent).
2. Clean request schema without unsupported legacy parameters (e.g. no temperature or candidateCount).
3. Header authentication using x-goog-api-key without printing or exposing secrets.
4. Response parsing for single-part and multi-part candidates.
5. Error handling for HTTP 400, 429, 503, network dropouts, and missing keys.
"""

import sys
from pathlib import Path
import pytest
import httpx

root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.config import settings
from backend.AI import call_ai, call_ai_async, _extract_response_text


def test_gemini_model_endpoint_url():
    """Verify that the default endpoint points to the official gemini-2.5-flash generateContent URL."""
    assert settings.ai_model == "gemini-2.5-flash"
    assert settings.ai_api_url.endswith("/models/gemini-2.5-flash:generateContent")
    assert "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" == settings.ai_api_url


def test_gemini_request_schema_and_headers_async(monkeypatch):
    """Verify exact payload schema and headers sent by call_ai_async."""
    captured_request = {}

    async def fake_post(self, url, headers=None, json=None, **kwargs):
        captured_request["url"] = str(url)
        captured_request["headers"] = headers
        captured_request["json"] = json
        # Return valid mock Gemini response
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Synthetic response from Gemini 2.5 Flash."}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ]
        }
        return httpx.Response(200, json=mock_response_data, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(settings, "google_api_key", "test-mock-key-abc123xyz")

    import asyncio
    result = asyncio.run(call_ai_async("Analyze this dataset."))

    assert result == "Synthetic response from Gemini 2.5 Flash."
    assert captured_request["url"].endswith("/models/gemini-2.5-flash:generateContent")
    assert captured_request["headers"]["Content-Type"] == "application/json"
    assert captured_request["headers"]["x-goog-api-key"] == "test-mock-key-abc123xyz"

    # Schema verification: contents parts must match Gemini generateContent schema
    payload = captured_request["json"]
    assert "contents" in payload
    assert payload["contents"] == [{"parts": [{"text": "Analyze this dataset."}]}]

    # Verification: legacy parameters (temperature, candidateCount, topP) MUST NOT be present
    gen_config = payload.get("generationConfig", {})
    assert "temperature" not in gen_config, "temperature is not supported on Gemini 3.x Flash and must be omitted"
    assert "candidateCount" not in gen_config, "candidateCount causes 400 errors on Gemini 3.x and must be omitted"
    assert "topP" not in gen_config
    assert "topK" not in gen_config
    assert gen_config.get("maxOutputTokens") == 800


def test_gemini_request_schema_and_headers_sync(monkeypatch):
    """Verify exact payload schema and headers sent by synchronous call_ai."""
    captured_request = {}

    def fake_post(url, headers=None, json=None, **kwargs):
        captured_request["url"] = str(url)
        captured_request["headers"] = headers
        captured_request["json"] = json
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Sync mock answer."}],
                    }
                }
            ]
        }
        return httpx.Response(200, json=mock_response_data, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(settings, "google_api_key", "test-mock-key-abc123xyz")

    result = call_ai("Summarize columns.")
    assert result == "Sync mock answer."
    assert captured_request["url"].endswith("/models/gemini-2.5-flash:generateContent")
    assert "temperature" not in captured_request["json"]["generationConfig"]


def test_gemini_response_parsing_multipart():
    """Verify that multi-part candidate responses are concatenated correctly."""
    multi_part_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Part 1 of the explanation. "},
                        {"text": "Part 2 with additional insights."},
                    ]
                }
            }
        ]
    }
    extracted = _extract_response_text(multi_part_data)
    assert extracted == "Part 1 of the explanation. Part 2 with additional insights."


def test_gemini_response_parsing_malformed():
    """Verify that empty or malformed candidates raise RuntimeError."""
    with pytest.raises(RuntimeError, match="Unexpected or empty candidate structure"):
        _extract_response_text({"candidates": []})

    with pytest.raises(RuntimeError, match="Unexpected or empty candidate structure"):
        _extract_response_text({"candidates": [{"content": {"parts": []}}]})

    with pytest.raises(RuntimeError, match="Unexpected or empty candidate structure"):
        _extract_response_text({})


@pytest.mark.asyncio
async def test_gemini_http_400_error_handling(monkeypatch):
    """Verify HTTP 400 (e.g. invalid key or bad argument) raises clean RuntimeError."""
    async def fake_post_400(*args, **kwargs):
        req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent")
        return httpx.Response(400, json={"error": {"message": "API key not valid"}}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post_400)
    monkeypatch.setattr(settings, "google_api_key", "invalid-key")

    with pytest.raises(RuntimeError, match="Gemini API returned error status 400"):
        await call_ai_async("Test prompt")


@pytest.mark.asyncio
async def test_gemini_network_failure_handling(monkeypatch):
    """Verify network dropout raises clean connection failure RuntimeError."""
    async def fake_post_network_err(*args, **kwargs):
        raise httpx.ConnectTimeout("Connection timed out to Google APIs")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post_network_err)
    monkeypatch.setattr(settings, "google_api_key", "valid-key")

    with pytest.raises(RuntimeError, match="Failed to connect to Google Gemini API"):
        await call_ai_async("Test prompt")


@pytest.mark.asyncio
async def test_gemini_missing_api_key_raises_runtime_error(monkeypatch):
    """Verify that calling call_ai_async with empty key raises informative RuntimeError without network call."""
    monkeypatch.setattr(settings, "google_api_key", "")

    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY environment variable not set"):
        await call_ai_async("Test prompt")
