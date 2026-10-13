# DataLens Analytics — Phase 9 Test Strategy and Plan

**Document Version:** 1.0  
**Methodology:** Software Testing Life Cycle (STLC)  
**Project:** DataLens Analytics  
**Date:** October 11, 2026  
**Auditor:** Antigravity QA Engineering  

---

## 1. Mission and Objectives

The objective of Phase 9 is to conduct an evidence-based, risk-driven, comprehensive Quality Assurance cycle for DataLens Analytics. This STLC cycle systematically validates the application across all functional and non-functional quality dimensions, spans all four standard test levels (Unit, Integration, System, and Acceptance), resolves identified defects within scope, and establishes an objective, audit-ready release baseline.

---

## 2. Scope of Testing

### 2.1 In-Scope Components
1. **Frontend Application (React 18 + Vite)**:
   - File upload interface, drag-and-drop, progress indication, and MIME validation.
   - Interactive dashboard, Recharts visualizations, and Tabular dataset view.
   - Filter builder, multi-column condition filtering, and state synchronization.
   - AI Copilot drawer, chat submission, conversation history truncation (10 turns), and citation rendering.
   - Responsive layouts (desktop, tablet, mobile 360px viewport), keyboard navigation, focus management, and error boundaries.
   - Stale-request discard mechanisms, request sequence tokens, and API error normalization.
2. **Backend Application (FastAPI + Python 3.11)**:
   - Data parsing (`pandas`, `openpyxl`, `pyarrow`), CSV dialect/encoding auto-detection, and magic byte validation.
   - DatasetManager, pluggable storage engines (`InMemoryStorageEngine`, `DiskStorageEngine`), and Parquet persistence.
   - Dataset indexing lifecycle (`PENDING` -> `PROCESSING` -> `READY` / `FAILED`) and 409/400 endpoint status guards.
   - Deterministic AnalyticsEngine (sum, mean, min, max, std, variance, global counts, grouped aggregations, and percentage calculations).
   - QueryRouter decision boundaries (deterministic statistics vs. semantic RAG retrieval).
   - RAG Pipeline: chunking (row-boundary preservation), sentence-transformers embeddings (`all-MiniLM-L6-v2`), ChromaDB storage, semantic retrieval, and citation building.
   - Gemini API integration (`backend/AI.py` with `gemini-3.8-flash` payload formatting and response parsing).
   - Security controls: rate limiting (`slowapi`), CORS restrictions, security headers, request ID propagation, and strict JSON serialization (`allow_nan=False`).
3. **Deployment Topology & Operating Boundaries**:
   - Single-worker persistent FastAPI backend (`uvicorn --workers 1`) with mounted storage volume (`STORAGE_ENGINE=disk`).
   - Process restart survival and data consistency.
   - Fail-fast directory write validation (`.write_probe`).

### 2.2 Out-of-Scope / Exclusions
- External cloud provider provisioning (AWS ECS, Railway, GCP Cloud Run infrastructure).
- Real live destructive penetration testing or brute-force rate-limit attacks against third-party endpoints.
- Real user acceptance testing (UAT) with external stakeholders (simulated via automated acceptance test scenarios).

---

## 3. Testing Levels

| Test Level | Scope & Objective | Tooling / Framework | Primary Location |
| :--- | :--- | :--- | :--- |
| **Level 1: Unit Testing** | Isolated validation of algorithmic routines, statistical calculations, chunkers, routers, error parsers, and state utility functions. | `pytest`, `node:test`, `node:assert/strict` | `backend/tests/test_analytics*.py`, `frontend/src/**/*.test.js`, `backend/tests/test_gemini_transport.py` |
| **Level 2: Integration Testing** | Cross-boundary contract validation: upload -> registration -> background indexing -> chat/filter flow; disk Parquet round-trips; ChromaDB retrieval scoping. | `pytest`, FastAPI `TestClient`, `httpx.AsyncClient` | `backend/tests/test_integration_analytics.py`, `backend/tests/test_serverless_lifecycle.py`, `backend/tests/test_rag_deep_verification.py` |
| **Level 3: System Testing** | End-to-end functional workflows, security guardrails, failure resilience, crash recovery, bundle performance, and configuration validation. | `pytest`, ESLint, Vite Production Builder, Static Code Inspection | Full repository regression suites, configuration probes |
| **Level 4: Acceptance Testing** | Business scenario verification: user uploads dataset, views charts, applies filters, queries metrics deterministically, and handles errors gracefully. | End-to-end scenario assertions, TestClient synthetic journeys | `backend/tests/test_chat_filters.py`, `backend/tests/test_limits_and_errors.py` |

---

## 4. Risk-Based Priority Matrix

| Priority | Risk Category | Examples | Action & Exit Rule |
| :--- | :--- | :--- | :--- |
| **P0 / Critical** | Security, Data Loss, Isolation Breach | Cross-dataset retrieval leakage, plaintext secret exposure, unhandled NaN/Infinity JSON crashes, Parquet corruption. | Zero tolerated. Must be fixed and retested before closure. |
| **P1 / High** | Core Functional & Lifecycle Failure | Upload-to-chat flow broken, incorrect analytical calculations, index premature `READY` state, missing runtime dependencies (`pyarrow`). | Zero tolerated. Must be resolved within cycle. |
| **P2 / Medium** | UI State, Recoverability, Validation | Inconsistent filter reset, unhandled upstream API timeout, missing frontend build configuration warning. | Fix when root cause is clear; otherwise document with mitigation. |
| **P3 / Low** | Cosmetic, Minor Diagnostics | Deprecated test client warnings, non-critical log formatting improvements. | Track in defect register; does not block release. |

---

## 5. Test Environment & Data Strategy

### 5.1 Environment Specification
- **Runtime Environment:** Windows OS, Python 3.11.9, Node.js v20+, npm 10+.
- **Backend Stack:** FastAPI 0.115+, Pandas 2.2+, PyArrow 14+, ChromaDB 0.4+, Sentence-Transformers 2.3+.
- **Frontend Stack:** React 18.2, Vite 5.4, Recharts 2.12, Axios 1.7.
- **Isolated Storage Directories:**
  - Test SQLite / ChromaDB: dynamically isolated via `tmp_path` fixtures in pytest.
  - Test Parquet storage: ephemeral `tmp_path / "datasets"` in tests.

### 5.2 Synthetic Test Data Strategy
- **Standard Tabular Data:** Multi-row, multi-column datasets with numeric (int, float), categorical (strings), and date fields.
- **Grouped Aggregation Data:** Synthetic Sales/Country datasets (e.g. USA: 1700 total sales, Egypt: 1200 total sales) with pre-calculated expected totals.
- **Boundary & Malformed Data:** 
  - Zero-row files (header only).
  - 0-byte empty files.
  - Duplicate column headers.
  - Multi-line CSV cells containing embedded newlines and commas.
  - Non-numeric strings in numeric query columns.
  - Blocked binary signatures (Windows PE `MZ` header, ELF magic bytes).
  - Division by zero datasets (zero denominators).

---

## 6. Mocking Policy & External Boundary Isolation

1. **Internal Application Logic:** Internal code paths (DatasetManager, AnalyticsEngine, Chunker, FilterEngine, ChromaVectorStore) **MUST NOT be mocked** during integration testing.
2. **Google Gemini Cloud API:**
   - Because live cloud credentials in the local environment are invalid (returning HTTP 400), all automated regression tests mock the transport boundary using `httpx.Response` fixtures or `monkeypatch`.
   - **Crucial Rule:** Mocked tests are strictly categorized as local transport/schema verifications and **never** claimed as proof of live cloud connectivity.
   - Live cloud connectivity is explicitly designated **BLOCKED** pending deployment of a valid Google API key.

---

## 7. Entry and Exit Criteria

### Entry Criteria
- Repository baseline stable with passing Phase 8.2 code.
- Test suites discoverable by test runners.
- Storage dependencies declared in `backend/requirements.txt`.

### Exit Criteria
- 100% of collected backend and frontend automated tests execute cleanly.
- RTM provides complete traceability from requirements to test IDs and evidence.
- Zero open P0 or P1 defects in local application logic.
- Discrepancy in test inventory reconciled with exact count.
- Clear separation maintained between local verification (PASS) and live cloud verification (BLOCKED).
- All six STLC deliverables generated and archived.
