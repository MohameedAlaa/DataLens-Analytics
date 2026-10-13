# DataLens Analytics — Production Deployment Architecture

**Document Version:** 1.0  
**Phase:** 11 — Production Deployment Preparation  
**Status:** Validated & Ready  

---

## 1. System Architecture Overview

DataLens Analytics is architected as a decoupled two-tier application: a static frontend client deployed on Vercel and a FastAPI backend deployed on Render Free, interfacing with Google Gemini 2.5 Flash for chat synthesis and Google Gemini Embeddings (`gemini-embedding-001`, 768-dim) for semantic RAG retrieval.

```
┌─────────────────────────────────┐
│     Client Browser (User)       │
└────────────────┬────────────────┘
                 │ HTTPS (REST / JSON)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (React 18 + Vite)                  │
│  - Hosted on Vercel (Root Directory: frontend)              │
│  - Environment: VITE_API_BASE_URL (points to Render Backend)│
│  - ZERO secrets exposed in bundle                           │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTPS CORS-gated API Calls (/upload, /chat, /filter, /health)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│             FastAPI Backend (Render Free Tier)              │
│  - Process: Single Worker (uvicorn app:app --workers 1)     │
│  - Security: slowapi rate-limits, trusted proxy validation  │
│  - Analytics Engine: Deterministic arithmetic & aggregations│
│  - Query Router: Keyword & intent classifier                │
└──────────┬─────────────────────────────┬────────────────────┘
           │ Local Disk I/O              │ HTTPS (TLS 1.3)
           ▼                             ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│   Ephemeral Local Storage    │  │      Google Gemini API       │
│  1. DATASET_STORAGE_DIR      │  │  - Chat: gemini-2.5-flash    │
│     (./dataset_storage)      │  │  - Embeddings:               │
│     - Raw CSV / Parquet data │  │    gemini-embedding-001      │
│     - Metadata JSON state    │  │    (768-dim hosted API)      │
│  2. CHROMA_PERSIST_DIR       │  │  - Key: GOOGLE_API_KEY       │
│     (./chroma_db)            │  │    (backend-only secret)     │
│     - HNSW vector index      │  └──────────────────────────────┘
│     - SQLite metadata        │
└──────────────────────────────┘
```

---

## 2. Deployment Assumptions & Prerequisites

1. **Storage Lifecycle on Render Free**: The Render Free tier operates on an ephemeral container filesystem (`STORAGE_ENGINE=disk`). Datasets and ChromaDB indices reside at `./dataset_storage` and `./chroma_db` during the active container lifespan and persist across requests. However, container restarts, spin-downs (after inactivity), or redeployments reset the ephemeral filesystem. (Persistent disks can optionally be attached if upgrading to paid VPS/Starter plans).
2. **Single Worker Concurrency**: The backend process model is **strictly single-worker (`--workers 1`)**. ChromaDB uses local SQLite file locks and does not support multi-process concurrent writes to the same local directory without corruption or lock collisions.
3. **Decoupled Frontend**: The frontend is deployed as a static Single Page Application (SPA) on Vercel with Root Directory `frontend`, communicating over cross-origin HTTPS requests via `VITE_API_BASE_URL`.
4. **Active Google AI Credentials**: `GOOGLE_API_KEY` must be provisioned on Render with valid quota for `gemini-2.5-flash` and `gemini-embedding-001`.
5. **Deterministic Fallback**: In the event of Gemini upstream timeout (504), rate-limit (429), or service outage (503), the backend automatically serves mathematical queries via its internal deterministic analytics engine.

---

## 3. Storage Architecture (Directories Used at Runtime)

The backend uses the following local storage directories:

| Directory | Environment Variable | Default Path | Contents & Function |
|---|---|---|---|
| **Dataset Storage** | `DATASET_STORAGE_DIR` | `./dataset_storage` | Preserves ingested CSV files, normalized Parquet tables, and dataset schema/summary JSON metadata. |
| **Vector Store** | `CHROMA_PERSIST_DIR` | `./chroma_db` | Stores ChromaDB SQLite catalog and HNSW binary index files for semantic document chunks. |

> [!NOTE]
> On Render Free, these directories reside on the container's ephemeral filesystem. If the service restarts or spins down due to inactivity, previously uploaded datasets and embeddings are reset, requiring a fresh upload. If persistent multi-session durability is required, attach a persistent volume (e.g. Render Starter Disk at `/data`).

---

## 4. Required Environment Variables

### Backend Configuration (Server-Only Secrets & Settings)

| Variable | Required | Production Value | Purpose |
|---|---|---|---|
| `APP_ENV` | Yes | `production` | Enforces production security gates (disables `/docs` and `/redoc`, blocks wildcard CORS). |
| `GOOGLE_API_KEY` | Yes | `AIzaSy...` (Secret) | Server-side API key for Google Gemini. Never exposed to client. |
| `AI_MODEL` | Yes | `gemini-2.5-flash` | Selected production LLM model. |
| `STORAGE_ENGINE` | Yes | `disk` | Required for local disk file storage. |
| `DATASET_STORAGE_DIR` | Yes | `./dataset_storage` | Storage directory for tabular datasets (`/data/...` if volume mounted). |
| `CHROMA_PERSIST_DIR` | Yes | `./chroma_db` | Storage directory for vector embeddings (`/data/...` if volume mounted). |
| `CORS_ORIGINS` | Yes | `https://datalens.yourdomain.com` | Explicit trusted origin(s) allowed by `CORSMiddleware`. Wildcards (`*`) are rejected. |
| `CORS_ALLOW_CREDENTIALS` | No | `false` | Whether cross-origin requests support credentials. |
| `TRUSTED_PROXIES` | If proxied | `10.0.0.1,172.16.0.1` | CIDRs/IPs of load balancer/reverse proxy to prevent IP spoofing for rate limits. |
| `RATE_LIMIT_UPLOAD` | No | `10/minute` | Rate limit for `/upload` multipart endpoints. |
| `RATE_LIMIT_CHAT` | No | `30/minute` | Rate limit for `/chat` RAG and LLM endpoints. |
| `RATE_LIMIT_FILTER` | No | `120/minute` | Rate limit for interactive data filtering. |
| `RATE_LIMIT_DEFAULT` | No | `60/minute` | Default endpoint rate limit. |
| `LOG_FORMAT` | No | `json` | Structured JSON log output for ingestion by Datadog, CloudWatch, or Grafana Loki. |
| `LOG_LEVEL` | No | `INFO` | Logging severity threshold. |

### Frontend Configuration (Static Build-Time Settings)

| Variable | Required | Production Value | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | Yes | `https://api.datalens.yourdomain.com` | Base URL used by `apiClient.js` for all backend REST requests. |

---

## 5. Security & Isolation Architecture

1. **Zero Secret Exposure**:
   - `GOOGLE_API_KEY` is loaded strictly by backend `config.py` from server environment variables.
   - Frontend build artifact contains 0 references to API keys or Gemini credentials.
2. **CORS Governance**:
   - In production (`APP_ENV=production`), `Settings` startup validation raises a fatal error if `*` is present in `CORS_ORIGINS`.
3. **Anti-Spoofing Rate Limiting**:
   - Client IPs are extracted via `get_real_client_ip()` in `security.py`.
   - Forwarding headers (`X-Forwarded-For`) are strictly ignored unless the direct socket connection originates from an explicitly declared `TRUSTED_PROXIES` address.
4. **Cross-Dataset Isolation**:
   - Every uploaded dataset is assigned an isolated UUID session key.
   - Ingestion and chunking partitions all embeddings by `dataset_id` in ChromaDB metadata.
   - Chat and retrieval queries strictly filter by active `dataset_id`, preventing cross-tenant or cross-dataset context leaks.
5. **Security Headers & Request Tracing**:
   - Every request is tagged with a UUID `X-Request-ID` for end-to-end audit tracing.
   - Standard security headers enforced: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`.

---

## 6. Hosting Platform Evaluation

### Recommended Production Platforms

| Platform | Tier / Component | Persistent Disk Support | Verdict | Notes |
|---|---|---|---|---|
| **Render** | Web Service (Python 3.13.5) | Optional (Render Free has no disk) | **COMPATIBLE** | Target platform. Render Free tier with single worker (`--workers 1`), ephemeral storage (`./dataset_storage`, `./chroma_db`), ~212 MB peak memory (58% margin under 512 MB RAM ceiling). |
| **Vercel (Frontend)** | Static Web App | N/A (Static SPA) | **COMPATIBLE** | Target frontend platform. Deploy with Root Directory `frontend`, Vite `dist/` output, and `VITE_API_BASE_URL` pointing to Render. |
| **Railway** | Railway Service | Yes (Railway Volume) | **COMPATIBLE** | Supported. Attach volume mount to container directory. |
| **Fly.io** | Fly Machine / App | Yes (Fly Volume) | **COMPATIBLE** | Supported. Fly volumes attach directly to microVM. |
| **AWS ECS / Fargate** | ECS Task Definition | Yes (AWS EFS) | **COMPATIBLE** | Standard enterprise architecture. EFS volume mounted into task. |

### Incompatible Hosting Platforms

| Platform | Reason for Incompatibility |
|---|---|
| **AWS Lambda / Serverless** | Lacks durable local disk persistence for ChromaDB without custom EFS integration; background threads terminate immediately when HTTP response returns. |
| **Vercel Serverless Functions (Backend)** | Maximum execution timeouts; read-only ephemeral filesystem (`/tmp` wiped between invocations); multi-process worker mismatch with local SQLite locks. Note: Vercel is used strictly for static frontend hosting. |
| **Google Cloud Run (Default Ephemeral)** | Ephemeral memory-only disk loses datasets on container scale-to-zero unless Cloud Storage FUSE volume is mounted with single-writer lock. |

---

## 7. Production Startup Command

For containerized or VM deployment:

```bash
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

**Parameters Explained:**
- `--host 0.0.0.0`: Binds to all network interfaces inside container/instance.
- `--port ${PORT:-8000}`: Binds to platform-provided environment port (Render, Railway, Fly, Heroku require dynamic `$PORT`).
- `--workers 1`: Ensures single worker process, maintaining memory-thread safety and preventing ChromaDB SQLite database locks.

---

## 8. Health Check Specification

- **Endpoint**: `GET /health`
- **Rate Limit**: Exempt (`@limiter.exempt`)
- **Success Code**: HTTP 200 OK
- **Payload Contract**:
  ```json
  {
    "status": "ok",
    "env": "production",
    "datasets_loaded": 0
  }
  ```
- **Liveness & Readiness Configuration**:
  - Initial delay: 5 seconds
  - Period: 15 seconds
  - Timeout: 3 seconds
  - Failure threshold: 3

---

## 9. Known Architectural Limitations

1. **Single-Node Scalability**: Because vector embeddings and dataset frames are managed on a local filesystem volume, the backend cannot be scaled horizontally across multiple instances without replacing local ChromaDB with a remote vector service (e.g., Chroma Client/Server, Qdrant, or Pinecone) and replacing disk storage with an object store (e.g., S3 or GCS).
2. **Hosted Embeddings & Ephemeral Storage**: Ingestion calls Gemini `gemini-embedding-001` (768-dim), so it depends on Gemini API quota; failures mark the dataset `FAILED` (no silent fallback in production). On Render Free, `./dataset_storage` and `./chroma_db` are ephemeral and are lost on restart, spin-down, or redeploy.
