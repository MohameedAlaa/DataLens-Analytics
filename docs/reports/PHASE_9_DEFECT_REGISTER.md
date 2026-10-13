# DataLens Analytics — Phase 9 Defect Register

**Document Version:** 1.0  
**STLC Stage:** Stage 6 — Defect Reporting, Fixing, and Retesting  
**Date:** October 11, 2026  
**Auditor:** Antigravity QA Engineering  

---

## 1. Defect Summary Table

| Defect ID | Linked Req | Severity | Priority | Component | Summary | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | REQ-FUNC-03 | High | P1 | Backend / Packaging | `pyarrow` dependency missing from `backend/requirements.txt` | **RESOLVED** |
| **DEF-02** | REQ-FUNC-12 | High | P1 | AI Service / Config | Deprecated `gemini-1.5-flash` model family referenced | **RESOLVED** |
| **DEF-03** | REQ-FUNC-12 | High | P1 | AI Service / Transport | Legacy `temperature` parameter causes deprecation in Gemini 3.x payload | **RESOLVED** |
| **DEF-04** | REQ-DEP-02 | Medium | P2 | Frontend / Client | Missing `frontend/.env.example` and missing runtime warning when `VITE_API_BASE_URL` unset | **RESOLVED** |
| **DEF-05** | REQ-FUNC-12 | High | P1 | External / Deployment | Local `GOOGLE_API_KEY` returns HTTP 400 Invalid Key against live Gemini endpoint | **BLOCKED (Release Blocker)** |

---

## 2. Detailed Defect Records

### DEF-01: Missing `pyarrow` Dependency in `backend/requirements.txt`
- **Defect ID:** DEF-01
- **Linked Requirement:** REQ-FUNC-03
- **Severity:** High | **Priority:** P1
- **Component:** `backend/requirements.txt`
- **Description:** `DiskStorageEngine` invokes `pandas.DataFrame.to_parquet` and `pandas.read_parquet`. When running in a clean container or fresh virtual environment installed strictly via `pip install -r backend/requirements.txt`, Parquet operations raise `ImportError: Unable to find a usable engine; tried using: 'pyarrow', 'fastparquet'`.
- **Root Cause:** `pyarrow` was present on the local development machine but omitted from the package manifest.
- **Fix Implemented:** Added `pyarrow>=14.0.0,<20.0.0` to `backend/requirements.txt`.
- **Regression Verification:** Verified via `test_persistent_disk_storage_across_process_restart`. Clean installation confirmed.
- **Retest Status:** **RESOLVED / VERIFIED**

---

### DEF-02: Deprecated `gemini-1.5-flash` Model Family in Config Defaults
- **Defect ID:** DEF-02
- **Linked Requirement:** REQ-FUNC-12
- **Severity:** High | **Priority:** P1
- **Component:** `backend/config.py`, `backend/.env.example`, `backend/.env`
- **Description:** The application configuration previously defaulted to `gemini-1.5-flash`, a model family that has been retired/shut down by Google.
- **Root Cause:** Legacy model naming from earlier phases.
- **Fix Implemented:** Updated default model to **`gemini-3.8-flash`**, the currently supported stable production model for general-purpose tasks in new projects. `ai_api_url` updated to dynamically format `/models/{self.ai_model}:generateContent`.
- **Regression Verification:** Verified via `test_gemini_model_endpoint_url` in `backend/tests/test_gemini_transport.py`.
- **Retest Status:** **RESOLVED / VERIFIED**

---

### DEF-03: Unsupported Legacy Parameters in Gemini 3.x Generation Config
- **Defect ID:** DEF-03
- **Linked Requirement:** REQ-FUNC-12
- **Severity:** High | **Priority:** P1
- **Component:** `backend/AI.py`
- **Description:** In Gemini 3.x models, `generationConfig` parameters such as `temperature`, `topK`, `topP` are ignored, and parameters like `candidateCount` trigger HTTP 400 errors. `backend/AI.py` hard-coded `"temperature": 0.7`.
- **Root Cause:** Legacy v1 schema assumptions.
- **Fix Implemented:** Cleaned up payload in `backend/AI.py` to send only official parameters (`contents` and `generationConfig: {"maxOutputTokens": 800}`). Enhanced `_extract_response_text` to concatenate multi-part text fragments safely.
- **Regression Verification:** Added `test_gemini_request_schema_and_headers_async` and `test_gemini_request_schema_and_headers_sync`.
- **Retest Status:** **RESOLVED / VERIFIED**

---

### DEF-04: Lack of Build-Time API URL Guidance in Frontend
- **Defect ID:** DEF-04
- **Linked Requirement:** REQ-DEP-02
- **Severity:** Medium | **Priority:** P2
- **Component:** `frontend/src/utils/apiClient.js`, `frontend/.env.example`
- **Description:** If operators build the frontend for production without setting `VITE_API_BASE_URL`, requests silently fall back to relative `/api`. In a deployment where frontend is hosted on a CDN (e.g. Vercel) and backend on a container, requests route to incompatible in-memory serverless adapters or 404 without clear indication.
- **Root Cause:** No template `.env.example` in `frontend/` and no runtime diagnostics in `apiClient.js`.
- **Fix Implemented:** 
  1. Created `frontend/.env.example`.
  2. Enhanced `getApiBaseUrl()` in `frontend/src/utils/apiClient.js` to emit a prominent browser console warning in production builds if `VITE_API_BASE_URL` is omitted.
- **Regression Verification:** Verified via `npm run build` and `npm test`.
- **Retest Status:** **RESOLVED / VERIFIED**

---

### DEF-05: Live Gemini API Key Returns HTTP 400 (Invalid Key)
- **Defect ID:** DEF-05
- **Linked Requirement:** REQ-FUNC-12
- **Severity:** High | **Priority:** P1
- **Component:** External Cloud Provider / Deployment Secret Store
- **Description:** Live REST calls to Google Generative Language API using the local environment key fail with `HTTP 400 Bad Request: API key not valid. Please pass a valid API key.`
- **Root Cause:** The key present in the local `.env` is invalid, expired, or unauthorized for the Google Generative Language API.
- **Impact:** While all local mocked tests pass and internal deterministic analytics bypasses AI successfully, real-time natural language summaries using the live Gemini cloud API cannot generate responses until a valid key is provided.
- **Remediation Plan:** An operator or project administrator must provision an active Google Gemini API key from Google AI Studio / Google Cloud Console with the Generative Language API enabled, and inject it as `GOOGLE_API_KEY` into the deployment secret manager.
- **Current Status:** **OPEN / BLOCKED (Documented Release Blocker)**
