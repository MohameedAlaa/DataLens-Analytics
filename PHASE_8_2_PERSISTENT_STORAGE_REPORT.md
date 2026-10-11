# PHASE 8.2 — PERSISTENT DATA STORAGE & DEPLOYMENT ARCHITECTURE REPORT

**Project:** DataLens Analytics  
**Date:** October 11, 2026  
**Status:** PASS  
**Auditor / Engineer:** Principal Systems Architect & Senior Backend/Frontend Engineer  

---

## 1. Executive Summary & Chosen Deployment Model

### A. Deployment Model Confirmation
Following thorough inspection of `vercel.json`, `README.md`, `backend/config.py`, `api/`, and `backend/dataset_manager.py`:
- The repository's primary, production-ready target is a **Persistent Backend Deployment** (e.g., Docker container on AWS ECS / GCP Cloud Run with volume mount, Railway, Render, or a Linux VM running Uvicorn).
- In this model, the backend process runs persistently, supporting:
  1. Long-lived background task execution (`BackgroundTasks` for embedding & vector indexing).
  2. Persistent vector database storage on local or mounted disk (`CHROMA_PERSIST_DIR`, defaulting to `./chroma_db`).
  3. Persistent dataset storage on disk (`DiskStorageEngine` writing Parquet + JSON metadata) or fast in-memory storage (`InMemoryStorageEngine`).
- The Vercel adapter endpoints in `api/` (`api/index.py`, `api/upload.py`, `api/chat.py`, `api/filter.py`) are maintained as compatible serverless entry points. Within a single warm worker or container, they share state via `dataset_manager`. However, **multi-worker serverless scaling** across independent cold lambda containers requires external cloud backing services (detailed in Section 6).

### B. Final Decision: **PASS**
All core contracts—dataset isolation, strict lifecycle enforcement (`PENDING` → `PROCESSING` → `READY` / `FAILED`), persistent disk storage across process restarts, UUID lookup security, deterministic analytics, and RAG retrieval—have been implemented and verified. All **75 backend tests** and **15 frontend tests** pass cleanly with zero failures.

---

## 2. Persistent State Requirements & Lifecycle Trace

| Lifecycle Phase | State Component | Current Storage Mechanism | Persistence Guarantee | Cross-Worker Behavior |
|---|---|---|---|---|
| **Upload** | Raw bytes / DataFrame | `DatasetManager` (`InMemoryStorageEngine` or `DiskStorageEngine`) | Ephemeral in RAM (memory) or persistent Parquet (disk) | Shared if mounted volume; isolated if ephemeral RAM |
| **Registration** | UUID & Dataset Metadata | Stored in `metadata` dict (RAM or `.meta.json` on disk) | Persists with storage engine | Shared if mounted volume; isolated if ephemeral RAM |
| **Ingestion** | `indexing_status` | Starts `PENDING`, updates `PROCESSING` → `READY` or `FAILED` | Persists in metadata | Enforced by `check_dataset_ready()` (returns 409 / 400) |
| **RAG Indexing** | Chunk vectors & metadata | `ChromaVectorStore` (`./chroma_db`) | Persisted to SQLite + HNSW binary on disk | Shared if mounted volume; isolated if ephemeral RAM |
| **Duplicate Prevention** | Vector re-indexing | `vector_store.delete_dataset(dataset_id)` before chunk insert | Idempotent | Prevents orphan vector duplicates on retry |
| **Chat Retrieval** | Dataset lookup & vector query | `dataset_manager.get_dataset()` + `retriever.retrieve()` | Requires dataset & vectors | Enforces `READY` status before query execution |
| **Filtering** | Filtered dataset rows | Computed via `apply_filters(df, filters)` | Stateless calculation | Enforces `READY` status; rejects filename-only lookup |
| **Cleanup** | Dataset & vector deletion | `delete_dataset(id)` + `vector_store.delete_dataset(id)` | Complete disk & RAM purge | Verified via unit & integration tests |

---

## 3. Storage Architecture & Pluggable Engines

### A. Abstract Storage Contract (`BaseStorageEngine`)
Located in [`backend/dataset_manager.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/dataset_manager.py):
```python
class BaseStorageEngine(abc.ABC):
    @abc.abstractmethod
    def store(self, dataset_id: str, df: pd.DataFrame, metadata: Dict[str, Any]) -> None: ...
    @abc.abstractmethod
    def get(self, dataset_id: str) -> Optional[pd.DataFrame]: ...
    @abc.abstractmethod
    def get_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]: ...
    @abc.abstractmethod
    def delete(self, dataset_id: str) -> bool: ...
    @abc.abstractmethod
    def exists(self, dataset_id: str) -> bool: ...
    @abc.abstractmethod
    def list_ids(self) -> List[str]: ...
```

### B. Engines Implemented
1. **`InMemoryStorageEngine`**:
   - Thread-safe in-memory dictionary storage.
   - Ideal for unit testing, CI pipelines, and single-process dev servers.
2. **`DiskStorageEngine` (NEW in Phase 8.2)**:
   - Stores DataFrames as high-performance `.parquet` files (via `pyarrow` / `pandas`).
   - Stores metadata as `.meta.json` in `DATASET_STORAGE_DIR` (default: `./dataset_storage`).
   - Enables datasets and metadata to survive process crashes, Uvicorn reloads, container restarts, or separate worker processes sharing a disk volume.
3. **Pluggable Configuration (`backend/config.py`)**:
   - `STORAGE_ENGINE`: `"memory"` (default) or `"disk"` / `"filesystem"`.
   - `DATASET_STORAGE_DIR`: Path to persistent storage directory.
   - Automatically initializes default singleton via `create_default_dataset_manager()`.

---

## 4. Dataset Lifecycle & Security Enforcement

### A. Lifecycle Enforcement (`check_dataset_ready`)
Centralized in [`backend/api_helpers.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/api_helpers.py) and applied uniformly across `backend/app.py`, `api/chat.py`, and `api/filter.py`:
- **`PENDING` or `PROCESSING`**: Raises **HTTP 409 Conflict** (`"Dataset ingestion is still in progress. Please try again later."`).
- **`FAILED`**: Raises **HTTP 400 Bad Request** (`"Dataset ingestion failed. It cannot be queried."`).
- **`READY`**: Allows query / chat / filter execution.
- **Premature Status Fix**: `api/upload.py` previously injected `extra_meta={"indexing_status": "READY"}`. This was removed so uploaded datasets strictly start in `PENDING` and transition to `READY` only when `ingestion_pipeline.run_ingestion` completes.

### B. Security & UUID Policy Enforcement
- In `api/filter.py`, the dangerous `lookup_key = req.dataset_id or req.filename` fallback was eliminated.
- Requests without a valid `dataset_id` (or inline `data` rows) are rejected with **HTTP 400 Bad Request**.
- Prevents cross-dataset collision and ensures dataset isolation cannot be bypassed via filename guessing.

---

## 5. Verification Evidence & Test Execution

### A. Pytest Suite Collection (`pytest --collect-only backend/tests/`)
```
collected 75 items across 14 test modules:
  - test_analytics.py: 8 tests
  - test_analytics_deep.py: 9 tests
  - test_chat.py: 8 tests
  - test_chat_filters.py: 1 test
  - test_deployment_architecture.py: 3 tests
  - test_filter.py: 6 tests
  - test_index_manager.py: 4 tests
  - test_integration_analytics.py: 8 tests
  - test_limits_and_errors.py: 4 tests
  - test_rag_deep_verification.py: 6 tests
  - test_rag_orchestration.py: 1 test
  - test_retriever.py: 3 tests
  - test_serverless_lifecycle.py: 5 tests (Enhanced Phase 8.2)
  - test_upload.py: 9 tests
```

### B. Pytest Suite Execution (`pytest backend/tests/ -v`)
```
======================= 75 passed, 1 warning in 19.61s =======================
Exit Code: 0
```
Key tests in [`test_serverless_lifecycle.py`](file:///c:/Users/moham/OneDrive/Desktop/AI%20projects/DataLens-Analytics/backend/tests/test_serverless_lifecycle.py):
1. `test_serverless_app_upload_chat_filter_lifecycle`: PASSED (upload → background indexing completes → chat & filter return 200).
2. `test_serverless_indexing_lifecycle_status_enforcement`: PASSED (verifies 409 on PENDING/PROCESSING, 400 on FAILED, 200 on READY).
3. `test_filter_rejects_filename_only_lookup`: PASSED (verifies HTTP 400 when attempting filename-only lookup).
4. `test_serverless_cross_worker_process_isolation`: PASSED (verifies in-memory datasets are isolated per worker process).
5. `test_persistent_disk_storage_across_process_restart`: PASSED (proves `DiskStorageEngine` persists dataset across completely separate process instances and cleans up on deletion).

### C. Frontend Verification
1. **`npm test`**: **15 passed, 0 failed** (475ms, Exit Code: 0)
2. **`npm run lint`**: **0 errors, 0 warnings** (Exit Code: 0)
3. **`npm run build`**: Built in 21.79s (Exit Code: 0)
   - Code-split chunks preserved:
     - `Chatbot-BrTOtc4e.js`: `13.02 kB` (gzip: 3.89 kB)
     - `AIInsightsSection-T4WMCBVV.js`: `24.01 kB` (gzip: 6.99 kB)
     - `Dashboard-tDBtJJJl.js`: `28.80 kB` (gzip: 8.19 kB)
     - `vendor-charts-Ddcf9vfY.js`: `445.77 kB` (gzip: 116.89 kB)

---

## 6. Multi-Worker Serverless Scaling Requirements

For teams seeking to run DataLens Analytics across multi-worker serverless platforms (e.g., AWS Lambda, Vercel Serverless with separate ephemeral micro-VMs per endpoint):
1. **DataFrame Storage**: Implement an S3/R2 or Redis storage engine inheriting from `BaseStorageEngine` to store uploaded DataFrames.
2. **Vector Database**: Point `ChromaVectorStore` to a hosted Chroma Cloud / Pinecone / Qdrant cluster instead of local `./chroma_db`.
3. **Background Jobs**: Serverless runtimes freeze CPU upon HTTP return. Ingestion tasks must be dispatched to an external async worker (e.g. AWS SQS/Lambda, Celery worker, or Inngest/QStash webhook).

---

## 7. Final Decision

### **PASS**

DataLens Analytics achieves full data lifecycle consistency, robust cross-process disk persistence (`DiskStorageEngine`), strict lifecycle enforcement (`PENDING` → `PROCESSING` → `READY` / `FAILED`), and verified security controls. All 75 backend tests and 15 frontend tests are green.
