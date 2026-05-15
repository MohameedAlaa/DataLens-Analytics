import os
from pathlib import Path
import httpx

AI_MODEL = os.getenv('AI_MODEL', 'gemini-1.5-flash')


def load_dotenv(env_path: Path) -> None:
    if not env_path.is_file():
        return
    with env_path.open('r', encoding='utf-8') as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


ENV_PATH = Path(__file__).resolve().parent / '.env'
load_dotenv(ENV_PATH)

API_KEY = os.getenv('GOOGLE_API_KEY')  # Set your Google API key in the environment or backend/.env
AI_API_URL = os.getenv(
    'AI_API_URL',
    f"https://generativelanguage.googleapis.com/v1beta2/models/{AI_MODEL}:generateText?key={API_KEY}",
)


def call_qwen(prompt: str) -> str:
    if not API_KEY:
        raise RuntimeError("GOOGLE_API_KEY environment variable not set for Google Gemini inference")
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800,
        }
    }
    response = httpx.post(AI_API_URL, headers=headers, json=payload, timeout=60.0)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Google Gemini inference failed for model '{AI_MODEL}': {exc.response.status_code} {exc.response.reason_phrase}"
        ) from exc

    data = response.json()
    if isinstance(data, dict):
        # Gemini 1.5 response structure: data['candidates'][0]['content']['parts'][0]['text']
        candidates = data.get("candidates")
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            content = first.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list) and parts:
                    return parts[0].get("text", "").strip()
    
    raise RuntimeError(f"Unexpected response from Google Gemini API: {data}")
