# DATALENS ANALYTICS — PHASE 10.1: TARGETED QA EVIDENCE CLOSURE & BROWSER REGRESSION REPORT

**Date:** October 11, 2026  
**Evaluation Role:** Senior QA Automation Engineer, Playwright Automation Lead & Security Test Specialist  
**Scope:** Phase 10.1 QA Evidence Closure, Full Browser Regression, Rate-Limit & Anti-Spoofing Verification, Responsive Viewport Audit, Live AI Smoke Test  
**Testing Mode:** Real Headless Browser Automation (Playwright on Microsoft Edge / Chromium), Live Gemini 2.5 Smoke Test Override, Security Test Client Execution  

### Status Breakdown:
- **Local Browser Regression:** **PASS** (All 7 user journeys, 4 responsive viewports, and deterministic calculations passed)
- **Live Gemini Generation (Temporary Override: `gemini-2.5-flash`):** **PASS** (Live greeting, semantic RAG query, citation badge, and dataset isolation verified via real Google API)
- **Live Gemini Generation (Configured Default: `gemini-3.8-flash`):** **BLOCKED** (Google Cloud unbilled Free Tier daily quota limit of 20 requests/day exceeded; HTTP 429 `RESOURCE_EXHAUSTED`)
- **Production Deployment:** **UNVERIFIED / NOT CLAIMED** (Verified strictly in local single-process runtime; production cloud release requires separate infrastructure verification)

---

## 1. EXECUTIVE SUMMARY & RECONCILED TEST TOTALS

Following the Phase 10 exploratory user simulation, this targeted QA evidence-closure pass was executed to reconcile all claims against concrete runtime evidence across AI/RAG behavior, rate-limiting policies, anti-spoofing controls, responsive viewports, and automated regression test suites.

### Reconciled Test Totals:
- **Backend Test Suite:** **93 passed, 0 warnings** across 15 test modules in 19.54s (`python -m pytest backend/tests/ -q`).  
  *(Corrected from older report totals; includes `test_deterministic_analytics_fallback_on_llm_failure`; `StarletteDeprecationWarning` filtered in `pytest.ini`).*
- **Rate-Limit & Anti-Spoofing Suite:** **11 passed, 0 warnings** in 9.30s (`pytest backend/tests/test_limits_and_errors.py -q`).
- **Gemini Transport Test Suite:** **8 passed, 0 warnings** in 1.32s (`pytest backend/tests/test_gemini_transport.py -v`).
- **Frontend Test Suite:** **15 passed, 0 failed** in 359ms (`npm test`).
- **Static Code Quality (ESLint):** **0 errors, 0 warnings** across all JSX/JS sources (`npm run lint`).
- **Production Bundle Compilation:** Built cleanly in 10.64s (`npm run build`).
- **Playwright Browser Simulation:** **7/7 user journeys passed** with zero uncaught application exceptions (`node e2e_alex_user_simulation.js`).
- **Responsive Viewport Assertions:** **4/4 viewports interactively tested** (1440×900, 768×1024, 390×844, 360×800) with zero horizontal page overflow.
- **Live AI Smoke Test (Temporary Override):** **3/3 live interactions passed** with HTTP 200 responses from Google API (`node e2e_live_ai_smoke_test.js`).

---

## 2. LIVE AI SMOKE TEST & RAG EVIDENCE

### 2.1 Temporary Model Override Live Smoke Test (`gemini-2.5-flash`)
To conclusively verify that the application's live AI pipeline, prompt assembly, Google API networking, UI streaming, and citation presentation function end-to-end when active quota is available, `AI_MODEL=gemini-2.5-flash` was temporarily configured in `backend/.env` for a controlled smoke test and immediately restored to `gemini-3.8-flash` upon test completion.

| Interaction | Mode | Prompt / Action | Observed HTTP Status & Google Response | UI & Citation Verification | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Greeting Query** | **LIVE** | `"Hello"` | **HTTP 200 OK**<br>`"Hello! How can I assist you with the 'alex_sales_primary.csv' dataset today? Synthesized from dataset context"` | Assistant greeting displayed cleanly in chat container | **PASS** |
| **Semantic / RAG Query** | **LIVE** | `"What products are sold in this dataset and in which countries?"` | **HTTP 200 OK**<br>`"The products sold in this dataset are 'Laptop' and 'Phone'. Both products are sold in 'USA' and 'Egypt'. 1 Verified Citation"` | Verified Citation badge displayed in UI (`citationBadgesInUI: 1`). Citations payload contained 1 item strictly referencing `alex_sales_primary.csv`. | **PASS** |
| **Cross-Dataset Isolation** | **LIVE** | Uploaded `alex_sales_second.csv`; asked `"What quarters and tiers are in this dataset?"` | **HTTP 200 OK**<br>`"The quarters in this dataset are Q1 and Q2. The tiers are Enterprise, Mid-Market, and SMB."` | Citations and answer strictly isolated; zero leakage of primary dataset (`alex_sales_primary.csv` or "Laptop") | **PASS** |

### Live AI Smoke Test Artifacts:
- Results JSON: [`live_smoke_test_results.json`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/live_smoke_test_results.json)
- Greeting Screenshot: [`live_smoke_greeting.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/live_smoke_greeting.png)
- Semantic/RAG Screenshot: [`live_smoke_semantic_rag.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/live_smoke_semantic_rag.png)
- Dataset Isolation Screenshot: [`live_smoke_dataset_isolation.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/live_smoke_dataset_isolation.png)

### 2.2 Restoration of Default Configuration
Immediately upon completion of the live smoke test:
1. `backend/.env` was restored to `AI_MODEL=gemini-3.8-flash`.
2. The backend daemon was restarted and verified via `/health` (HTTP 200).
3. The focused transport suite ([`test_gemini_transport.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/tests/test_gemini_transport.py)) was rerun and verified that all 8 tests pass against `gemini-3.8-flash`.

---

## 3. CONFIG-DEFAULT GEMINI 3.8 FLASH DIAGNOSIS

A single, controlled diagnostic query confirmed why live calls to `gemini-3.8-flash` currently fail:
- **API Key Authentication:** `GET https://generativelanguage.googleapis.com/v1beta/models` returned **HTTP 200 OK** with 50 available models (including `models/gemini-3.8-flash`). The key is 100% authenticated.
- **Sanitized Google Error:**
  ```json
  {
    "error": {
      "code": 429,
      "message": "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.8-flash. Please retry in 3h11m.",
      "status": "RESOURCE_EXHAUSTED",
      "details": [
        {
          "@type": "type.googleapis.com/google.rpc.QuotaFailure",
          "violations": [
            {
              "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
              "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
              "quotaDimensions": { "model": "gemini-3.8-flash", "location": "global" },
              "quotaValue": "20"
            }
          ]
        }
      ]
    }
  }
  ```
- **Root Cause:** The Google Cloud project is on an unbilled Free Tier plan, which caps `gemini-3.8-flash` at **20 requests per day per project**. All 20 requests were consumed during previous test runs.
- **Action Required to Unblock Default Model (`gemini-3.8-flash`):**
  1. In [Google Cloud Console](https://console.cloud.google.com/) or [Google AI Studio](https://aistudio.google.com/), link a billing account / pay-as-you-go plan to remove the 20 RPD free-tier cap.
  2. Alternatively, wait ~3 hours for the 24-hour Google free-tier quota window to reset.

---

## 4. RATE-LIMIT ENFORCEMENT & ANTI-SPOOFING EVIDENCE

All 11 tests in [`test_limits_and_errors.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/tests/test_limits_and_errors.py) passed in **9.30s**:

| Endpoint | Configured Limit | Implementation | Enforcement Evidence |
| :--- | :--- | :--- | :--- |
| `POST /upload` | `10/minute` | `@_rate_limited(settings.rate_limit_upload)` | 10 passed, 11th received HTTP 429 (`test_upload_rate_limit_strictly_enforced`) |
| `POST /chat` | `30/minute` | `@_rate_limited(settings.rate_limit_chat)` | 30 passed, 31st received HTTP 429 (`test_chat_rate_limit_strictly_enforced`) |
| `POST /filter` | `120/minute` | `@_rate_limited(settings.rate_limit_filter)` | 10 rapid queries passed with HTTP 200; frontend debounced at 350ms |
| `GET /stats/*` | `60/minute` | Default limiter policy | Governed by `settings.rate_limit_default` |
| `GET /health` | **Exempt** | `@_exempt` | 70 rapid polling queries all returned HTTP 200 without 429 |

- **Anti-Spoofing Evidence:** Untrusted clients sending rotating `X-Forwarded-For` or `X-Real-IP` headers are rejected; direct TCP peer IP is enforced (`test_get_client_ip_direct_ignores_spoofed_headers` and `test_rate_limiting_prevents_spoofed_ip_bypass`).

---

## 5. RESPONSIVE VIEWPORT EVIDENCE

All 4 viewports were **interactively tested** with Playwright programmatic assertions, DOM element queries, and user actions:

| Viewport Profile | Resolution | Type | Horizontal Overflow Asserted | Interactive Elements Verified & Executed | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Desktop** | 1440 × 900 | Interactive Test | `false` (`scrollWidth <= innerWidth`) | Brand logo visible, dataset pill visible, scrolled to `#dataset`, preview table rendered with 4 rows. | **PASS** |
| **Tablet** | 768 × 1024 | Interactive Test | `false` (`scrollWidth <= innerWidth`) | Brand logo visible, dataset pill visible, scrolled to `#overview`, KPI cards grid rendered cleanly. | **PASS** |
| **Mobile** | 390 × 844 | Interactive Test | `false` (`scrollWidth <= innerWidth`) | Brand logo visible, scrolled to `#dataset`, preview table visible with horizontal scroll containment. | **PASS** |
| **Narrow Mobile** | 360 × 800 | Interactive Test | `false` (`scrollWidth <= innerWidth`) | Brand logo visible, clicked `Open AI Copilot` in Navbar, opened mobile drawer, verified chat input visible, closed drawer via `Close Copilot`. | **PASS** |

---

## 6. BROWSER REGRESSION EVIDENCE TABLE (ALL JOURNEYS)

| Journey | Scenario | Actions & Validations | Observed Status | Evidence Artifact | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. First Visit** | Empty State | Loaded clean session at `http://127.0.0.1:5173`. Verified `"DataLens Analytics"` title, `"No dataset loaded"` badge, and dropzone. | Page rendered; zero uncaught JS exceptions | [`journey_1_first_visit.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_1_first_visit.png) | **PASS** |
| **2. Primary Upload** | CSV Ingestion | Uploaded `alex_sales_primary.csv`. Verified HTTP 200, `"alex_sales_primary.csv"` pill, `"4 rows"` badge, preview table headers (`country, product, sales, customers, date`), and 4 rows. | HTTP 200; Ingestion complete | [`journey_2_dataset_uploaded.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_2_dataset_uploaded.png) | **PASS** |
| **3. Dashboard & Stats** | Statistical Metrics | Verified computed average sales (`725.00`), `customers` and `sales` fields, and 133 Recharts/SVG components. | Computations align with fixture data | [`journey_3_dashboard_populated.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_3_dashboard_populated.png) | **PASS** |
| **4. Filter & Reset** | Rate & State Check | Filtered `sales >= 750` -> 2 rows displayed. Reset filter -> 4 rows displayed. Tested 4 rapid repeated filter queries -> HTTP `[200, 200, 200, 200]`. | Filtered: 2 rows; Reset: 4 rows; 429: False | [`journey_4_filter_active.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_4_filter_active.png), [`journey_4_filter_reset.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_4_filter_reset.png) | **PASS** |
| **5. AI Copilot** | Deterministic & Fallback | Asked `"What is the total sales?"` -> Deterministic engine computed `$2,900` with badge. Default model `gemini-3.8-flash` hit Google 429 quota -> clean fallback. Mocked test proved citation rendering. Live smoke test override proved real generation. | Deterministic: 2900 (HTTP 200); Live 2.5: HTTP 200; Default 3.8: HTTP 429 | [`journey_5_copilot_conversation.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_5_copilot_conversation.png) | **PASS** |
| **6. Dataset Switching** | Schema Isolation | Uploaded `alex_sales_second.csv` (`region, tier, revenue, units, quarter`). Table preview replaced with new headers; old `product` column completely purged. | Schema isolation confirmed | [`journey_6_dataset_switched.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_6_dataset_switched.png) | **PASS** |
| **7. Negative Input** | Error Resilience | Uploaded 0-row `empty_rows.csv` -> HTTP 400 rejection; UI displayed error banner. Re-uploaded valid `alex_sales_primary.csv` -> UI recovered cleanly with 4 rows. | Rejection: 400; Recovery: 200 | [`journey_7_error_feedback.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_7_error_feedback.png), [`journey_7_recovered.png`](file:///C:/Users/moham/.gemini/antigravity-ide/brain/b1bcdca6-5056-49eb-9497-47913775312f/screenshots/journey_7_recovered.png) | **PASS** |

---

## 7. PYTEST WARNING RESOLUTION

- **Warning:** `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
- **Root Cause:** Emitted during test fixture instantiation in `conftest.py` via `fastapi.testclient`.
- **Resolution:** Added `ignore::starlette.exceptions.StarletteDeprecationWarning` to `backend/pytest.ini`.
- **Verification:** Backend test suite completes with **93 passed, 0 warnings** in 19.54s.
