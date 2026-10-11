# DataLens Analytics — Phase 8.2 Deployment Configuration Check

**Final Release Status:** **PARTIAL PASS**  
- **Local Architecture, Tests & Build:** **PASS** (77/77 backend tests pass, 15/15 frontend tests pass, ESLint 0 errors, Vite production build clean)  
- **Live Cloud Gemini API Connectivity:** **BLOCKED** (The local environment API key returns `HTTP 400 Bad Request: API key not valid`. A valid Google Gemini API key must be provisioned before live cloud inference can function).  
**Date:** October 11, 2026  
**Auditor:** Antigravity AI  

---

## 1. Gemini Model Selection & Endpoint Verification

### Model Specification: `gemini-3.8-flash`
- **Family Status:** Google has retired older model generations (`gemini-1.5-flash` and `gemini-2.0-flash`). For new implementations, Google officially designates **`gemini-3.8-flash`** as the general-purpose, high-performance production default.
- **REST Endpoint Structure:**
  ```
  https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent
  ```
- **Updates Applied Across Codebase:**
  - `backend/config.py`: `ai_model: str = os.getenv("AI_MODEL", "gemini-3.8-flash")`
  - `backend/.env.example`: `AI_MODEL=gemini-3.8-flash`
  - Request format: Standard Google Generative Language v1beta JSON schema with `contents` parts and `x-goog-api-key` header authentication.

### Live API Credentials & Smoke Test Probe
A live probe was executed against the official Google Generative Language REST endpoint (`v1beta/models`) using credentials present in the local environment:
- **Observed Result:** `HTTP 400 Bad Request` (`"API key not valid. Please pass a valid API key."`).
- **Security Policy:** No secrets or key strings were printed, logged, or exposed in chat or artifacts.
- **Auditing Determination:**
  - Mocked test suite (`pytest backend/tests/test_rag_orchestration.py`, `test_chat.py`): **PASSED**.
  - **Live Cloud Connectivity:** **BLOCKED / UNVERIFIED**. Mocked test execution is never presented as proof of live cloud authorization.
  - **Required Action to Unblock:**
    1. Obtain an active Gemini API key from Google AI Studio or Google Cloud Console.
    2. Confirm that the **Generative Language API** is enabled for the associated project.
    3. Set `GOOGLE_API_KEY=<active_key>` in the deployment secret manager or container environment.

---

## 2. Disk Storage Dependencies & Parquet Serialization

### Verified Dependencies in `backend/requirements.txt`
All dependencies required by `DiskStorageEngine` are explicitly declared:
```text
pandas>=2.0.0,<3.0.0
openpyxl>=3.1.0,<4.0.0
pyarrow>=14.0.0,<20.0.0
httpx>=0.24.0,<1.0.0
chromadb>=0.4.22
sentence-transformers>=2.3.0
tiktoken>=0.5.2
```
- `pyarrow` is declared for Parquet columnar storage (`df.to_parquet`, `pd.read_parquet`).
- `chromadb` is declared for vector similarity storage (`PersistentClient` with SQLite/HNSW index).

### Storage Lifecycle Verification
1. **Dataset Write & Read:** Writes `.parquet` files and reads DataFrames back with exact column datatypes.
2. **Metadata Write & Read:** Atomic `.meta.json` storage with dataset schema, statistics, and indexing lifecycle status.
3. **Process Restart Persistence:** Verified in `test_persistent_disk_storage_across_process_restart` (Worker 1 writes -> terminates -> Worker 2 loads data with zero loss).
4. **Startup Write Probe:** Verified in `test_disk_storage_engine_fails_fast_on_unwritable_path` (If storage directory is read-only or unwritable, `DiskStorageEngine` immediately raises `RuntimeError` on startup).
5. **Deletion Cleanup:** Deletion unlinks both the `.parquet` data file and `.meta.json` metadata file.

---

## 3. Production Configuration Matrix

| Setting | Production Requirement | Status & Implementation |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Disables `/docs` and `/redoc`, activates production safety checks. |
| `STORAGE_ENGINE` | `disk` | Selects `DiskStorageEngine`. Emits `PRODUCTION WARNING` if configured with `memory`. |
| `DATASET_STORAGE_DIR` | Mounted persistent volume path | Verified writable via startup write-probe (`.write_probe`). |
| `CHROMA_PERSIST_DIR` | Mounted persistent volume path | ChromaDB vectors persisted to SQLite & HNSW on persistent disk. |
| `CORS_ORIGINS` | Explicit frontend origin(s) | Wildcard `*` disallowed in production by `_Settings.__init__`. |
| `VITE_API_BASE_URL` | Actual FastAPI backend URL | Injected at frontend build time via `VITE_API_BASE_URL`. |
| `AI_MODEL` | `gemini-3.8-flash` | Supported stable Gemini model for new projects. |
| `GOOGLE_API_KEY` | Valid API key from secret store | Secret; currently blocked pending valid production key. |

### Frontend Build Environment
- `frontend/src/utils/apiClient.js` dynamically reads `import.meta.env.VITE_API_BASE_URL`.
- If `VITE_API_BASE_URL` is omitted in a production build, `apiClient.js` emits a console warning in the browser.
- **Operators must provide the real URL of the persistent FastAPI backend during build:**
  ```bash
  export VITE_API_BASE_URL=https://<actual-backend-host>
  npm run build
  ```
- No placeholder or invented hostnames are baked into source code.

---

## 4. Concurrency & Availability Guarantees

### Topology: Single-Worker Backend (`--workers 1`)
- **Process Concurrency Boundary:**
  - `DiskStorageEngine` uses Python `threading.Lock()`, which synchronizes threads inside a **single** process.
  - It does **NOT** coordinate cross-process writes across multiple OS processes or multiple container replicas.
  - ChromaDB local persistence uses embedded SQLite (`chroma.sqlite3`). Multi-process writes to SQLite on shared network disks cause lock contention (`OperationalError: database is locked`).
- **Supported Architecture:**
  - **A single backend instance with a single worker process (`--workers 1`) is strictly required.**
  - **Horizontal scaling across multiple backend container replicas is EXPLICITLY UNSUPPORTED** under the local filesystem engine.
- **Volume & Backup Requirements:**
  - Mount a persistent block volume (AWS EBS, Google Persistent Disk, or local SSD) formatted with a standard POSIX filesystem (ext4 / XFS).
  - Backups must be performed via storage volume snapshots to capture consistent state across Parquet tables and ChromaDB SQLite files.
- **Crash Behavior During In-Flight Ingestion:**
  - Ingestion runs in-process via FastAPI `BackgroundTasks`.
  - If the backend crashes while indexing is in-flight, the background task dies.
  - On restart, the dataset on disk remains in `indexing_status: "PROCESSING"`.
  - Subsequent requests return **`409 Conflict`** (`"Dataset is still being processed and indexed. Please retry shortly."`).
  - The dataset never falsely transitions to `READY`. Interrupted jobs do not automatically resume; the file must be re-uploaded.

---

## 5. Security & Contract Regression Verification

1. **UUID-Based Lookup:** Datasets are registered and indexed strictly by UUID4.
2. **Filename Lookup Rejection:** Filter and chat endpoints reject filename-only lookups (`test_filter_rejects_filename_only_lookup` PASSED).
3. **Dataset Isolation:** ChromaDB queries enforce strict `where={"dataset_id": dataset_id}` filtering.
4. **Deterministic Analytics Bypass:** Numeric and statistical queries bypass RAG embeddings, calculate deterministically via Pandas, and validate strict JSON (`allow_nan=False`).
5. **Frontend Protections:** Stale async requests are invalidated on dataset switch, sequence tokens prevent out-of-order filter overwrites, and HTML 502/504 gateway responses are safely handled.

---

## 6. Execution Evidence & Verification Results

### 1. Backend Suite (`pytest backend/tests/ -v`)
```
======================= 77 passed, 1 warning in 36.99s =======================
Exit Code: 0
```
All 77 tests passed across analytics, integration, limits, RAG verification, retriever, serverless lifecycle, and upload suites.

### 2. Frontend Test Suite (`npm test`)
```
> datalens-frontend@0.1.0 test
> node --test src/**/*.test.js

✔ dataLifecycle: normalizeDatasetInfo handles sparse/partial backend responses (4.5318ms)
✔ dataLifecycle: request sequence token prevents out-of-order filter overwrites (61.2004ms)
✔ dataLifecycle: new upload resets active filters to empty dict (0.7651ms)
✔ chatSafety: prepareChatPayload bounds history to last 10 messages (5.1677ms)
✔ chatSafety: prepareChatPayload includes active filters (0.6941ms)
✔ chatSafety: normalizeAssistantResponse preserves deterministic analytics without mutation (0.8758ms)
✔ chatSafety: normalizeAssistantResponse handles citations defensive parsing (0.5812ms)
✔ chatSafety: stale async response discarded when dataset switched (3.3279ms)
✔ apiClient.extractErrorMessage handles Pydantic validation error arrays (2.8537ms)
✔ apiClient.extractErrorMessage handles string detail (0.4627ms)
✔ apiClient.extractErrorMessage handles object detail safely without crashing React (0.4432ms)
✔ apiClient.extractErrorMessage intercepts HTML 502/504 Bad Gateway pages (0.3705ms)
✔ apiClient.extractErrorMessage handles Network Error (0.7278ms)
✔ apiClient.extractErrorMessage handles timeout error (0.5253ms)
✔ apiClient.extractErrorMessage handles cancellation errors (0.5956ms)
ℹ tests 15 | pass 15 | fail 0 | duration_ms 990.3142
Exit Code: 0
```

### 3. Frontend Linting (`npm run lint` in `frontend/`)
```
> datalens-frontend@0.1.0 lint
> eslint src

Exit Code: 0 (0 errors, 0 warnings)
```

### 4. Frontend Production Build (`npm run build` in `frontend/`)
```
> datalens-frontend@0.1.0 build
> vite build

vite v5.4.21 building for production...
transforming...
✓ 2779 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                              0.65 kB │ gzip:   0.37 kB
dist/assets/index-B_JnJZxM.css              28.71 kB │ gzip:   6.02 kB
dist/assets/Chatbot-DUDjE5N-.js             13.02 kB │ gzip:   3.89 kB
dist/assets/vendor-icons-AnSEqm-q.js        23.28 kB │ gzip:   4.98 kB
dist/assets/AIInsightsSection-yNTj_h90.js   24.01 kB │ gzip:   6.99 kB
dist/assets/Dashboard-DGRba1nl.js           28.80 kB │ gzip:   8.20 kB
dist/assets/index-Wia-CiZF.js               68.32 kB │ gzip:  24.35 kB
dist/assets/vendor-markdown-BnO8lLWC.js    117.57 kB │ gzip:  36.12 kB
dist/assets/vendor-react-c6vpYEMA.js       141.96 kB │ gzip:  45.49 kB
dist/assets/vendor-charts-Ddcf9vfY.js      445.77 kB │ gzip: 116.89 kB
✓ built in 19.14s
Exit Code: 0
```

---

## 7. Remaining Release Blockers & Deployment Checklist

### Unresolved Blocker
- [ ] **Valid Production Gemini API Key:** The local key returns HTTP 400 (`API key not valid`). Live AI chat inference requires a valid Google Gemini API key to be provisioned in the deployment environment.

### Production Deployment Checklist
1. **Provision Persistent Volume:**
   ```bash
   mkdir -p /var/data/datalens/datasets /var/data/datalens/chroma_db
   chmod 750 /var/data/datalens
   ```
2. **Set Backend Environment Variables:**
   ```bash
   export APP_ENV=production
   export STORAGE_ENGINE=disk
   export DATASET_STORAGE_DIR=/var/data/datalens/datasets
   export CHROMA_PERSIST_DIR=/var/data/datalens/chroma_db
   export CORS_ORIGINS=https://app.yourdomain.com
   export GOOGLE_API_KEY="AIzaSy...<PROVISIONED_KEY>"
   export AI_MODEL=gemini-3.8-flash
   export LOG_FORMAT=json
   ```
3. **Launch Single-Worker Backend:**
   ```bash
   cd backend
   uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
   ```
4. **Build & Deploy Frontend with Actual Backend URL:**
   ```bash
   cd frontend
   export VITE_API_BASE_URL=https://api.yourdomain.com
   npm run build
   # Upload dist/ to CDN or static host (Vercel, Cloudflare, S3)
   ```
