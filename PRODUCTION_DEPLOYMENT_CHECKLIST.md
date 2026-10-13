# DataLens Analytics — Production Deployment Checklist

**Phase:** 11 — Production Deployment Preparation  
**Model Configured:** `gemini-2.5-flash`  
**Storage Architecture:** Ephemeral Local Storage (`STORAGE_ENGINE=disk`) + Single-Worker Uvicorn (Render Free)

---

## 1. Pre-Deployment Verification Checklist

Verify all prerequisites locally and in CI/CD pipelines before initiating cloud resource provisioning or deployment.

### Code Quality & Automated Test Gates
- [x] **Backend Unit & Integration Tests**: 93 passed, 0 failures, 0 warnings (`python -m pytest backend/tests/ -q`).
- [x] **Frontend Unit & Component Tests**: 15 passed, 0 failures (`npm test`).
- [x] **Frontend Code Quality (ESLint)**: 0 lint errors, 0 warnings (`npm run lint`).
- [x] **Production Bundle Compilation**: Clean Vite compilation into `frontend/dist/` without errors (`npm run build`).
- [x] **Live AI Smoke Testing**: Live Google Gemini 2.5 Flash query execution verified with 100% success on greeting, semantic RAG query, citations, and cross-dataset isolation.
- [x] **Browser End-to-End Simulation**: Complete Alex User Simulation passed across all 7 journeys and 4 responsive viewports (`node e2e_alex_user_simulation.js`).

### Security & Secret Governance Gate
- [x] **Zero Hardcoded Secrets**: Confirmed no API keys, tokens, or plaintext credentials committed to version control.
- [x] **Git Ignore Verification**: `.gitignore` strictly excludes `.env`, `backend/.env`, `*.sqlite3`, `chroma_db/`, and `dataset_storage/`.
- [x] **Frontend Secrets Isolation**: Frontend source tree contains zero references to `GOOGLE_API_KEY` or backend-only environment variables.
- [x] **Production CORS Guardrail**: `Settings` in `config.py` verified to block wildcard CORS (`*`) when `APP_ENV=production`.
- [x] **Anti-Spoofing Rate Limiting**: `TRUSTED_PROXIES` configuration tested to ensure client IPs from unverified `X-Forwarded-For` headers are discarded.

### Configuration & Persistence Alignment
- [x] **AI Model Set**: `AI_MODEL=gemini-2.5-flash` verified in `backend/config.py` and template `.env.example`.
- [x] **Embeddings Architecture Set**: Gemini `gemini-embedding-001` (768-dim) verified; zero local PyTorch/sentence-transformers dependencies.
- [x] **Storage Engine Set**: `STORAGE_ENGINE=disk` configured in `render.yaml` and environment templates.
- [x] **Ephemeral Directories Defined**: `DATASET_STORAGE_DIR=./dataset_storage` and `CHROMA_PERSIST_DIR=./chroma_db` configured for Render Free.
- [x] **Worker Model Fixed**: Single worker (`--workers 1`) documented as mandatory for ChromaDB / SQLite concurrency safety.
- [x] **Deterministic Analytics Retained**: Mathematical queries routed with exact arithmetic fallback in case of LLM outage.

---

## 2. Cloud Deployment Execution Steps

Follow these sequential steps during active infrastructure provisioning:

### Step A: Backend Provisioning (Render Free Web Service)
1. **Target Platform Selection**: Deploy to Render as a Web Service using declarative blueprint [`render.yaml`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/render.yaml) (`plan: free`).
2. **Storage Configuration**:
   - Render Free uses container ephemeral storage (`STORAGE_ENGINE=disk`).
   - Ephemeral directory paths:
     - `DATASET_STORAGE_DIR=./dataset_storage`
     - `CHROMA_PERSIST_DIR=./chroma_db`
   - No persistent disk required.
3. **Inject Backend Environment Secrets**:
   - `APP_ENV=production`
   - `PYTHON_VERSION=3.13.5`
   - `GOOGLE_API_KEY=<SECRET_PRODUCTION_KEY>` (injected securely as a Render Dashboard secret)
   - `AI_MODEL=gemini-2.5-flash`
   - `STORAGE_ENGINE=disk`
   - `DATASET_STORAGE_DIR=./dataset_storage`
   - `CHROMA_PERSIST_DIR=./chroma_db`
   - `CORS_ORIGINS=https://your-frontend.vercel.app` (your exact Vercel frontend URL)
   - `CORS_ALLOW_CREDENTIALS=false`
   - `RATE_LIMIT_UPLOAD=10/minute`
   - `RATE_LIMIT_CHAT=30/minute`
   - `RATE_LIMIT_FILTER=120/minute`
   - `RATE_LIMIT_DEFAULT=60/minute`
   - `LOG_FORMAT=json`
4. **Configure Start Command**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1
   ```
5. **Verify Backend Liveness**:
   - Issue request to `GET /health`.
   - Confirm HTTP 200 response: `{"status":"ok","env":"production",...}`.

### Step B: Frontend Static Deployment (Vercel)
1. **Target Platform Selection**: Deploy to Vercel with **Root Directory** set to `frontend`.
2. **Set Build Environment Variable**:
   - Set `VITE_API_BASE_URL=https://datalens-backend.onrender.com` (public HTTPS URL of Render backend).
3. **Build & Routing Configuration**:
   - Install command: `npm install`
   - Build command: `npm run build` (`vite build`)
   - Output directory: `dist`
   - SPA routing: Handled via [`frontend/vercel.json`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/frontend/vercel.json) (`rewrites: [{"source": "/(.*)", "destination": "/index.html"}]`).
4. **Enforce HTTPS**:
   - Vercel automatically enforces TLS/SSL and redirects HTTP to HTTPS.

---

## 3. Post-Deployment Live Release Smoke Test

Execute this manual or automated validation protocol immediately following deployment:

- [ ] **1. Application Load**:
  - Navigate to production frontend URL.
  - Page loads with header "DataLens Analytics" and empty state indicator "No dataset loaded".
- [ ] **2. Dataset Ingestion**:
  - Upload sample tabular dataset (e.g. `test_fixtures/alex_sales_primary.csv`).
  - Confirm HTTP 200 response from `/upload`.
  - Confirm table preview renders correct rows and columns.
- [ ] **3. Dashboard & Chart Rendering**:
  - Verify key metric cards render formatted values (row count, numeric averages).
  - Verify charts and histograms render without console errors.
- [ ] **4. Interactive Filtering**:
  - Apply numeric range filter (e.g., minimum sales).
  - Confirm table and dashboard statistics update dynamically.
  - Reset filters and confirm original row count restored.
- [ ] **5. AI Copilot Greeting**:
  - Submit query: `"Hello"`.
  - Confirm assistant responds with greeting referencing active dataset name.
- [ ] **6. Deterministic Mathematical Query**:
  - Submit query: `"What is the total sales?"`.
  - Confirm response contains exact sum (`2900`) and deterministic analytics badge.
- [ ] **7. Live Semantic / RAG Query**:
  - Submit query: `"What products are sold in this dataset and in which countries?"`.
  - Assistant answers with verified product and country details.
  - Confirm "Verified Citation" badge is rendered in chat bubble.
- [ ] **8. Dataset Switching & State Isolation**:
  - Upload second distinct dataset (e.g. `test_fixtures/alex_sales_second.csv`).
  - Verify UI reflects new column schema.
  - Query second dataset: verify assistant answers strictly from new dataset with zero citation leakage from the first.
- [ ] **9. Negative File Resilience**:
  - Attempt upload of invalid or empty CSV (e.g. `test_fixtures/empty_rows.csv`).
  - Confirm clear error toast/feedback in UI; confirm application does not crash.
- [ ] **10. Ephemeral Storage Lifecycle on Render Free**:
  - Note that on Render Free, uploaded datasets and ChromaDB indices persist across requests during active runtime.
  - On cold container spin-down or new deployment, ephemeral filesystem resets cleanly, requiring a fresh dataset upload.
