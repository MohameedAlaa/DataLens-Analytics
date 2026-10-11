# DataLens Analytics — Production Deployment Checklist

**Phase:** 11 — Production Deployment Preparation  
**Model Configured:** `gemini-2.5-flash`  
**Storage Architecture:** Persistent Disk (`STORAGE_ENGINE=disk`) + Single-Worker Uvicorn  

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
- [x] **Persistence Engine Set**: `STORAGE_ENGINE=disk` configured in environment template.
- [x] **Persistent Directories Defined**: `DATASET_STORAGE_DIR` and `CHROMA_PERSIST_DIR` paths mapped to durable volume paths.
- [x] **Worker Model Fixed**: Single worker (`--workers 1`) documented as mandatory for ChromaDB / SQLite concurrency safety.
- [x] **Deterministic Analytics Retained**: Mathematical queries routed with exact arithmetic fallback in case of LLM outage.

---

## 2. Cloud Deployment Execution Steps

Follow these sequential steps during active infrastructure provisioning:

### Step A: Backend Provisioning (PaaS / Docker / VPS)
1. **Target Platform Selection**: Deploy to a container or VPS provider that supports persistent storage volumes (Render Web Service with Persistent Disk, Railway with Volume, Fly.io with Mount, or AWS ECS with EFS).
2. **Attach Persistent Storage Volume**:
   - Create and mount a durable volume (e.g. `/data` or `/var/lib/datalens`).
   - Configure directory paths:
     - `DATASET_STORAGE_DIR=/data/dataset_storage`
     - `CHROMA_PERSIST_DIR=/data/chroma_db`
3. **Inject Backend Environment Secrets**:
   - `APP_ENV=production`
   - `GOOGLE_API_KEY=<SECRET_PRODUCTION_KEY>`
   - `AI_MODEL=gemini-2.5-flash`
   - `STORAGE_ENGINE=disk`
   - `CORS_ORIGINS=https://app.datalens.yourdomain.com` (your exact frontend URL)
   - `CORS_ALLOW_CREDENTIALS=false`
   - `TRUSTED_PROXIES=<REVERSE_PROXY_OR_LOAD_BALANCER_IPS>`
   - `RATE_LIMIT_UPLOAD=10/minute`
   - `RATE_LIMIT_CHAT=30/minute`
   - `RATE_LIMIT_FILTER=120/minute`
4. **Configure Start Command**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
   ```
5. **Verify Backend Liveness**:
   - Issue request to `GET /health`.
   - Confirm HTTP 200 response: `{"status":"ok","env":"production",...}`.

### Step B: Frontend Static Deployment (Vercel / Netlify / Cloudflare / S3)
1. **Set Build Environment Variable**:
   - Set `VITE_API_BASE_URL=https://api.datalens.yourdomain.com` (public HTTPS URL of backend).
2. **Execute Build**:
   ```bash
   npm run build
   ```
3. **Publish Static Assets**:
   - Publish `dist/` directory.
   - Configure Single Page Application rewrite rule: `/* -> /index.html` (HTTP 200).
4. **Enforce HTTPS**:
   - Ensure TLS/SSL is active and HTTP redirects to HTTPS.

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
- [ ] **10. Persistence Across Container Restart**:
  - Restart the production backend container service.
  - Refresh browser; verify existing dataset UUID session remains valid and accessible without HTTP 404.
