# DataLens Analytics — Serverless Adapters (`api/`)

## Architectural Notice & Status

> [!IMPORTANT]
> **Status: Legacy Test Fixtures / Process Isolation Harnesses**  
> The Python modules in this directory (`api/index.py`, `api/upload.py`, `api/chat.py`, `api/filter.py`) are **NOT** the active production backend.

### 1. Canonical Production Architecture
The authoritative production backend is [`backend/app.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/app.py), deployed as a persistent FastAPI Web Service on Render via [`render.yaml`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/render.yaml) (`uvicorn app:app --workers 1`).

The frontend is deployed to Vercel as a static SPA with root directory `frontend/`. As configured in [`frontend/vercel.json`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/frontend/vercel.json), all `/api/(.*)` requests are proxied via edge rewrites directly to the Render FastAPI backend:

```json
"rewrites": [
  {
    "source": "/api/(.*)",
    "destination": "https://datalens-backend-jt3p.onrender.com/$1"
  },
  {
    "source": "/(.*)",
    "destination": "/index.html"
  }
]
```

### 2. Purpose of this Directory
The modules in `api/` are preserved for automated architectural regression testing:
- [`backend/tests/test_serverless_lifecycle.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/tests/test_serverless_lifecycle.py)
- [`backend/tests/test_deployment_architecture.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/tests/test_deployment_architecture.py)

These tests execute against `api/` to prove that serverless multi-worker environments do not share in-memory dataset state, validating why a persistent single-worker backend (`backend/app.py`) is required for embedded ChromaDB SQLite locks and dataset persistence.

### 3. Route & Capability Comparison

| Feature / Route | Canonical Backend (`backend/app.py`) | Serverless Wrappers (`api/`) |
| :--- | :--- | :--- |
| **`POST /upload`** | Yes (with magic byte validation & rate limits) | Yes (basic parsing only) |
| **`POST /filter`** | Yes (with pagination, bounding & rate limits) | Yes (basic filtering only) |
| **`POST /chat`** | Yes (with deterministic math & RAG) | Yes (basic chat) |
| **`GET /stats/{id}`** | **Yes** | **None** |
| **`GET /categories`** | **Yes** | **None** |
| **`GET /health`** | **Yes** | Root `/` only |
| **Rate Limiting** | **Yes** (slowapi) | None |
| **Security Headers** | **Yes** (SecurityHeadersMiddleware) | None |
| **Request Tracing** | **Yes** (RequestIDMiddleware) | None |
| **Deployment Target** | Render Web Service (`render.yaml`) | None (Decommissioned) |
