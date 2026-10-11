"""Safe Live Gemini Smoke Test
Verifies live connectivity to Google Gemini API using local configuration.
Zero secrets are exposed: never prints API keys, headers, or unredacted error bodies.
"""

import os
import sys
import re
from pathlib import Path

# Ensure backend modules can be imported
backend_dir = Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name == "tests" else Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

import httpx
from config import settings


def sanitize(text: str, key: str) -> str:
    """Strip any accidental occurrence of the secret key from text."""
    if not key or not text:
        return text
    return text.replace(key, "[REDACTED_API_KEY]")


async def run_smoke_test():
    key = settings.google_api_key
    model = settings.ai_model
    endpoint = settings.ai_api_url

    print("=" * 60)
    print("DATALENS ANALYTICS — SAFE GEMINI CONNECTIVITY CHECK")
    print("=" * 60)

    # 1. Key Presence & Safe Metadata
    if not key:
        print("[!] GOOGLE_API_KEY is NOT configured (empty string).")
        print("    Status: BLOCKED — No API key found in active environment.")
        return False

    is_standard_format = key.startswith("AIzaSy")
    print(f"[*] API Key Present: Yes")
    print(f"[*] Key Length: {len(key)} characters")
    print(f"[*] Standard Gemini Key Prefix (AIzaSy): {'Valid' if is_standard_format else 'Non-standard / Custom'}")
    print(f"[*] Configured Model: {model}")
    print(f"[*] Endpoint URL: {endpoint}")

    # 2. Single Minimal Request
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }
    payload = {
        "contents": [{"parts": [{"text": "Reply with 'PING_OK' in one word."}]}],
        "generationConfig": {
            "maxOutputTokens": 800,
        },
    }

    print("\n[*] Sending single minimal generateContent request...")

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            status_code = response.status_code
            print(f"[*] HTTP Status Code: {status_code}")

            if status_code == 200:
                data = response.json()
                try:
                    from AI import _extract_response_text
                    reply = _extract_response_text(data)
                    print(f"[*] Response Output: {sanitize(reply, key)}")
                    print("[PASS] SUCCESS: Live Gemini API connectivity verified!")
                    return True
                except Exception as parse_err:
                    print(f"[!] HTTP 200 received but candidate parsing differed: {parse_err}")
                    cand = data.get('candidates', [{}])[0]
                    print(f"[*] Finish reason: {cand.get('finishReason')}")
                    print(f"[*] Content obj: {cand.get('content')}")
                    return True
            else:
                # Sanitize error output
                raw_text = response.text
                sanitized_text = sanitize(raw_text, key)
                # Extract message if json
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", {}).get("message", sanitized_text[:200])
                    err_status = err_json.get("error", {}).get("status", "")
                    print(f"[!] API Error Status: {err_status}")
                    print(f"[!] API Error Message: {sanitize(err_msg, key)}")
                except Exception:
                    print(f"[!] Response: {sanitized_text[:200]}")

                if status_code == 400:
                    print("\n[Diagnosis - HTTP 400]:")
                    print("Google rejected the request. Common causes:")
                    print("1. The API key value is invalid, deactivated, or contains whitespace/quotes.")
                    print("2. The API key has not been enabled for Generative Language API in Google Cloud Console.")
                elif status_code == 404:
                    print(f"\n[Diagnosis - HTTP 404]:")
                    print(f"Model '{model}' not found. Verify whether '{model}' is supported by Google Generative AI v1beta.")
                elif status_code == 403:
                    print("\n[Diagnosis - HTTP 403]:")
                    print("API key does not have permission or billing is required for this quota.")
                return False

    except httpx.RequestError as exc:
        print(f"[!] Network Connection Error: {type(exc).__name__}")
        return False
    except Exception as exc:
        print(f"[!] Unexpected Error: {type(exc).__name__}: {sanitize(str(exc), key)}")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_smoke_test())
