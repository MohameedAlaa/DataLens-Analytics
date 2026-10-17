import collections
import datetime
import io
import json
import logging
import math
import threading
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException

from services.ai.rag.citation_builder import CitationBuilder
from services.ai.rag.prompt_builder import PromptBuilder
from services.ai.rag.query_router import QueryRouter
from services.ai.rag.retriever import Retriever
from services.ai.rag.llm_service import RagLLMService


def check_dataset_ready(meta: Optional[Dict[str, Any]]) -> None:
    """Enforce dataset lifecycle state before allowing read access."""
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset metadata not found.")
    status = meta.get("indexing_status", "PENDING")
    if status in ("PENDING", "PROCESSING"):
        raise HTTPException(
            status_code=409,
            detail="Dataset ingestion is still in progress. Please try again later."
        )
    if status == "FAILED":
        raise HTTPException(
            status_code=400,
            detail="Dataset ingestion failed. It cannot be queried."
        )
    if status != "READY":
        raise HTTPException(
            status_code=400,
            detail=f"Dataset is in an invalid state: {status}."
        )

import numpy as np
import pandas as pd
try:
    from AI import call_ai, call_ai_async
except ImportError:
    from .AI import call_ai, call_ai_async

try:
    from config import settings
except ImportError:
    try:
        from backend.config import settings
    except ImportError:
        settings = None

# Initialize single orchestrator engine for backend operations
logger = logging.getLogger(__name__)
# (Removed legacy InsightEngine to prevent duplicate RAG paths and mock database queries)

from services.analytics import get_analytics_engine

# RAG orchestration helpers
_query_router = QueryRouter()
_prompt_builder = PromptBuilder()
_citation_builder = CitationBuilder()

def build_analytics_engine():
    return get_analytics_engine()

_MAX_RAG_TOP_K = 3

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit


SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls")


def sanitize_json_value(val: Any) -> Any:
    """Normalize a scalar value for RFC 8259-compliant JSON serialization.

    Converts non-finite floats (NaN, +inf, -inf), pandas NA/NaT, and missing
    values to None (JSON null), while strictly preserving valid numbers (including 0 and 0.0),
    booleans, strings, and collections.
    """
    if val is None:
        return None

    # Handle pandas / numpy missing sentinel types (pd.NA, pd.NaT)
    if val is pd.NA or val is pd.NaT:
        return None

    # Check bool before int, as bool is a subclass of int in Python
    if isinstance(val, (bool, np.bool_)):
        return bool(val)

    # Preserve valid integers
    if isinstance(val, (int, np.integer)):
        return int(val)

    # Handle floating point types and check for NaN, +inf, -inf
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)

    # Check timestamps and datetime objects
    if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
        if pd.isna(val):
            return None
        return val.isoformat() if hasattr(val, "isoformat") else str(val)

    # Catch any remaining pandas NA/null representations
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(val, dict):
        return {str(k): sanitize_json_value(v) for k, v in val.items()}

    if isinstance(val, (list, tuple, set)):
        return [sanitize_json_value(item) for item in val]

    return val


def sanitize_records_for_json(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize a list of row dictionaries so that all non-finite floats,
    missing values (NaN, NaT, pd.NA), and datetime objects are safely JSON-serializable.
    """
    if not records:
        return []
    return [
        {str(k): sanitize_json_value(v) for k, v in record.items()}
        for record in records
    ]


def classify_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Categorize dataframe columns into numeric, categorical, and date groups."""
    numeric = [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    date = [str(c) for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    categorical = [
        str(c) for c in df.columns
        if str(c) not in numeric and str(c) not in date and (
            pd.api.types.is_object_dtype(df[c])
            or pd.api.types.is_string_dtype(df[c])
            or pd.api.types.is_categorical_dtype(df[c])
        )
    ]
    return {
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "date_columns": date,
    }


def calculate_dataset_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate numerical statistics, categorical summaries, and correlation matrix."""
    types = classify_columns(df)
    numeric_cols = types["numeric_columns"]
    categorical_cols = types["categorical_columns"]

    numeric_summary = {}
    if numeric_cols:
        desc = df[numeric_cols].describe().to_dict()
        for col in numeric_cols:
            raw_count = desc[col].get("count", 0)
            numeric_summary[str(col)] = {
                "count": int(raw_count) if isinstance(raw_count, (int, np.integer)) else float(raw_count),
                "mean": sanitize_json_value(desc[col].get("mean")),
                "std": sanitize_json_value(desc[col].get("std")),
                "min": sanitize_json_value(desc[col].get("min")),
                "25%": sanitize_json_value(desc[col].get("25%")),
                "50%": sanitize_json_value(desc[col].get("50%")),
                "75%": sanitize_json_value(desc[col].get("75%")),
                "max": sanitize_json_value(desc[col].get("max")),
            }

    corr_matrix = {}
    if len(numeric_cols) > 1:
        corr_df = df[numeric_cols].corr().replace([np.inf, -np.inf], 0).fillna(0)
        corr_matrix = {
            str(c): {str(k): sanitize_json_value(v) for k, v in corr_df[c].to_dict().items()}
            for c in corr_df.columns
        }

    categorical_summary = {}
    for col in categorical_cols:
        top_vals = df[col].value_counts().head(5).to_dict()
        categorical_summary[str(col)] = {
            "unique_count": int(df[col].nunique()),
            "top_values": {str(k): int(v) for k, v in top_vals.items()},
        }

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "correlation_matrix": corr_matrix,
    }


def compute_filter_options(df: pd.DataFrame, max_categories: int = 50) -> Dict[str, Any]:
    """Derive dataset-wide numeric bounds, categorical options, and date ranges
    from the full DataFrame for frontend filter controls.
    """
    types = classify_columns(df)
    filter_opts: Dict[str, Any] = {}

    for col in types["numeric_columns"]:
        s = df[col].dropna()
        if not s.empty:
            min_v = s.min()
            max_v = s.max()
            if pd.notna(min_v) and pd.notna(max_v) and not np.isinf(min_v) and not np.isinf(max_v):
                min_clean = int(min_v) if isinstance(min_v, (int, np.integer)) else float(min_v)
                max_clean = int(max_v) if isinstance(max_v, (int, np.integer)) else float(max_v)
                filter_opts[str(col)] = {"bounds": [min_clean, max_clean]}
            else:
                filter_opts[str(col)] = {"bounds": None}
        else:
            filter_opts[str(col)] = {"bounds": None}

    for col in types["categorical_columns"]:
        # Count by string label so values with identical representations
        # (e.g. numeric 1 and string "1") form a single option, matching
        # search_category_values and the /filter label semantics.
        s = df[col].dropna().astype(str)
        if not s.empty:
            counts = s.value_counts().head(max_categories)
            top_vals = [
                {"value": str(k), "count": int(v)}
                for k, v in counts.items()
            ]
            filter_opts[str(col)] = {"top_values": top_vals}
        else:
            filter_opts[str(col)] = {"top_values": []}

    for col in types["date_columns"]:
        s = df[col].dropna()
        if not s.empty:
            min_d = str(s.min())
            max_d = str(s.max())
            filter_opts[str(col)] = {"bounds": [min_d, max_d]}
        else:
            filter_opts[str(col)] = {"bounds": None}

    return filter_opts


def search_category_values(
    df: pd.DataFrame,
    column: str,
    query: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    """Search distinct values and their counts in a dataset column.

    Excludes null/NaN values, handles mixed types, and performs case-insensitive
    literal substring matching (regex=False to prevent ReDoS).
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in dataset.")

    limit = max(1, min(limit, 100))
    s = df[column].dropna().astype(str)

    cleaned_query = query.strip() if query else ""
    if cleaned_query:
        mask = s.str.contains(cleaned_query, case=False, regex=False, na=False)
        matched = s[mask]
    else:
        matched = s

    val_counts = matched.value_counts()
    total_matches = int(len(val_counts))
    top_items = val_counts.head(limit)

    values = [
        {"value": str(k), "count": int(v)}
        for k, v in top_items.items()
    ]

    return {
        "column": column,
        "query": cleaned_query,
        "total_matches": total_matches,
        "truncated": total_matches > limit,
        "values": values,
    }


def generate_local_answer(question: str, df: pd.DataFrame) -> str:
    """Generate a simple local text summary of the dataset for fallback situations."""
    rows, cols = df.shape
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    return (
        f"Dataset contains {rows} rows and {cols} columns.\n"
        f"Numeric columns: {', '.join(num_cols) if num_cols else 'None'}.\n"
        f"Sample head:\n{df.head(3).to_string()}"
    )


def validate_file_size(contents: bytes, max_bytes: int = MAX_FILE_SIZE_BYTES) -> None:
    """Validate that file content size does not exceed the allowed threshold."""
    if len(contents) > max_bytes:
        size_mb = len(contents) / (1024 * 1024)
        max_mb = max_bytes / (1024 * 1024)
        logger.warning("Upload size validation failed: %.2f MB exceeds limit of %.0f MB", size_mb, max_mb)
        raise ValueError(f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {max_mb:.0f} MB.")



def detect_csv_encoding(contents: bytes) -> str:
    """Detect text encoding for CSV files by testing against standard candidate encodings."""
    candidate_encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
    sample = contents[:65536]  # 64 KB sample for rapid detection

    for enc in candidate_encodings:
        try:
            sample.decode(enc)
            contents.decode(enc)
            logger.debug("Successfully detected CSV text encoding: '%s'", enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    logger.warning("Could not determine exact CSV encoding; defaulting to utf-8")
    return "utf-8"


def parse_dataset_bytes(
    contents: bytes,
    filename: str,
    preview_limit: int = 100,
    max_bytes: int = MAX_FILE_SIZE_BYTES
) -> Dict[str, Any]:
    """Validate file size, format, encoding, headers, and contents, then parse into structured dictionary."""
    # 1. File extension validation
    if not filename or not filename.lower().endswith(SUPPORTED_EXTENSIONS):
        ext = filename.split(".")[-1] if "." in filename else "unknown"
        logger.warning("Upload rejected: Unsupported file type '.%s' for filename '%s'", ext, filename)
        raise ValueError(f"Unsupported file type '.{ext}'. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.")

    # 2. Maximum upload size check
    validate_file_size(contents, max_bytes=max_bytes)

    # 3. Empty file check
    if not contents or len(contents.strip()) == 0:
        logger.warning("Upload rejected: File '%s' is empty (0 bytes)", filename)
        raise ValueError("Uploaded file is empty (0 bytes).")

    filename_lower = filename.lower()
    encoding = "utf-8"

    # 4. File format and CSV/Excel parsing validation
    try:
        if filename_lower.endswith(".csv"):
            encoding = detect_csv_encoding(contents)
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
            except pd.errors.EmptyDataError:
                logger.warning("Upload rejected: Empty CSV file '%s'", filename)
                raise ValueError("Uploaded CSV file is empty or contains no data rows.")
            except pd.errors.ParserError as parse_err:
                logger.warning("Upload rejected: CSV parsing error in '%s': %s", filename, parse_err)
                raise ValueError("Failed to parse CSV file structure. Please ensure it is a valid CSV formatted file.")
        else:
            try:
                df = pd.read_excel(io.BytesIO(contents))
            except Exception as excel_err:
                logger.warning("Upload rejected: Excel parsing error in '%s': %s", filename, excel_err)
                raise ValueError("Failed to parse Excel file structure. Please ensure it is a valid .xlsx or .xls file.")

    except ValueError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error parsing upload '%s': %s", filename, exc)
        raise ValueError("Could not parse or read the uploaded dataset file.")

    # 5. Empty dataset checks (no rows or no columns)
    if df.empty or df.shape[0] == 0:
        logger.warning("Upload rejected: Dataset '%s' contains 0 data rows", filename)
        raise ValueError("Uploaded file contains no data rows.")

    if df.shape[1] == 0:
        logger.warning("Upload rejected: Dataset '%s' contains 0 columns", filename)
        raise ValueError("Uploaded file contains no column headers.")

    # 6. Duplicate column detection
    duplicates: List[str] = []
    if filename_lower.endswith(".csv"):
        try:
            first_line = contents.decode(encoding, errors="ignore").splitlines()[0]
            raw_headers = [c.strip().strip('"').strip("'") for c in first_line.split(",") if c.strip()]
            seen_headers = set()
            for header in raw_headers:
                if header in seen_headers and header not in duplicates:
                    duplicates.append(header)
                seen_headers.add(header)
        except Exception:
            pass

    if not duplicates:
        col_names = [str(c) for c in df.columns]
        seen_cols = set()
        for c in col_names:
            base_col = c.split(".")[0] if "." in c and c.split(".")[-1].isdigit() else c
            if c in seen_cols:
                duplicates.append(c)
            seen_cols.add(c)

    if duplicates:
        dups_formatted = ", ".join([f"'{d}'" for d in set(duplicates)])
        logger.warning("Upload rejected: Duplicate column names in '%s': %s", filename, dups_formatted)
        raise ValueError(f"Duplicate column names detected in dataset: {dups_formatted}. All column headers must be unique.")

    logger.info(
        "Successfully validated and parsed '%s': %d rows, %d columns (size: %.2f KB, encoding: %s)",
        filename, df.shape[0], df.shape[1], len(contents) / 1024, encoding
    )

    cols = [str(c) for c in df.columns]
    dtypes = {str(c): str(df[c].dtype) for c in df.columns}

    preview_df = df.head(preview_limit).copy()
    for col in preview_df.select_dtypes(include=["datetime", "datetime64"]).columns:
        preview_df[col] = preview_df[col].astype(str)

    preview = sanitize_records_for_json(preview_df.to_dict(orient="records"))
    types = classify_columns(df)
    filter_options = compute_filter_options(df)
    dataset_id = str(uuid.uuid4())

    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "columns": cols,
        "dtypes": dtypes,
        "shape": list(df.shape),
        "preview": preview,
        "filter_options": filter_options,
        **types,
    }




# ---------------------------------------------------------------------------
# Typed error classes for AI chat failures
# ---------------------------------------------------------------------------

class AIUnavailableError(RuntimeError):
    """AI backend is unreachable or returned a 5xx server error."""


class AIRateLimitError(RuntimeError):
    """AI backend enforced rate limiting (HTTP 429)."""


# ---------------------------------------------------------------------------
# Dataset context cache
#
# Building the system-prompt context (column stats + representative sample)
# is CPU-intensive for large datasets. We cache the result per dataset_id
# so it is computed exactly once and reused across every chat turn.
#
# Eviction: LRU with an explicit upper bound (default 100 entries, configurable
# via settings.dataset_context_cache_size or DATASET_CONTEXT_CACHE_SIZE env var).
# Thread safety: synchronized with an internal lock to protect OrderedDict
# mutations across concurrent worker threads.
# Lifecycle: invalidated when a dataset is deleted or re-registered with new data.
# ---------------------------------------------------------------------------

_CONTEXT_CACHE_LOCK = threading.Lock()


def _get_context_cache_max() -> int:
    """Retrieve maximum dataset context cache entries from application settings."""
    try:
        from config import settings
        return getattr(settings, "dataset_context_cache_size", 100)
    except Exception:
        return 100


_CONTEXT_CACHE_MAX = _get_context_cache_max()
_context_cache: collections.OrderedDict = collections.OrderedDict()  # dataset_id -> context str
_DATASET_CONTEXT_CACHE = _context_cache  # Canonical alias for AI-01 audit finding compatibility


def invalidate_dataset_context(dataset_id: Optional[str] = None) -> bool:
    """Invalidate cached dataset context for a given dataset_id, or clear all if None.

    Args:
        dataset_id: Optional UUID of the dataset whose context to purge. If None,
                    the entire context cache is cleared.

    Returns:
        True if an entry was removed or cache was non-empty, False otherwise.
    """
    with _CONTEXT_CACHE_LOCK:
        if dataset_id is None:
            had_items = len(_context_cache) > 0
            _context_cache.clear()
            return had_items
        if dataset_id in _context_cache:
            del _context_cache[dataset_id]
            return True
        return False


# Maximum number of conversation turns kept in the prompt.
# Older turns are dropped to prevent unbounded prompt growth.
_MAX_HISTORY_TURNS = 10


# ---------------------------------------------------------------------------
# Legacy build_system_prompt (kept for callers that don't have a dataset_id)
# ---------------------------------------------------------------------------

def build_system_prompt(filename: str, df: pd.DataFrame) -> str:
    """Build system prompt from schema + 10-row sample (legacy, no caching).

    Prefer ``build_dataset_context`` / ``_build_system_prompt_v2`` for new
    code — they cache the expensive stats computation per dataset_id.
    """
    rows, cols = df.shape
    column_info = ", ".join([f"{c} ({str(df[c].dtype)})" for c in df.columns])
    sample = df.head(10).to_dict(orient="records")
    return (
        "You are a data analyst assistant for 'DataLens Analytics'.\n"
        f"The user has uploaded a dataset: '{filename or 'dataset'}'\n"
        f"- Dimensions: {rows} rows, {cols} columns\n"
        f"- Columns: {column_info}\n"
        f"- Data Sample: {json.dumps(sample, default=str)}\n\n"
        "Instructions:\n"
        "1. Be concise, professional, and helpful.\n"
        "2. Use the provided sample and metadata to answer questions.\n"
        "3. If you need to perform calculations not evident from the sample, explain how you would do it.\n"
        "4. If you don't know the answer or the data doesn't support it, say so."
    )


# ---------------------------------------------------------------------------
# Smart context helpers (used by the cached v2 prompt builder)
# ---------------------------------------------------------------------------

def _build_column_stats(df: pd.DataFrame) -> str:
    """Build a compact per-column statistics block for the AI context.

    Numeric columns:  min / max / mean / null count
    Datetime columns: min / max / null count
    Categorical cols: unique count / top-3 values / null count
    """
    parts: List[str] = []
    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        dtype_str = str(series.dtype)

        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            if len(non_null):
                parts.append(
                    f"  {col} ({dtype_str}): "
                    f"min={non_null.min():.4g}, max={non_null.max():.4g}, "
                    f"mean={non_null.mean():.4g}, nulls={null_count}"
                )
            else:
                parts.append(f"  {col} ({dtype_str}): all null")

        elif pd.api.types.is_datetime64_any_dtype(series):
            non_null = series.dropna()
            if len(non_null):
                parts.append(
                    f"  {col} (datetime): "
                    f"min={non_null.min()}, max={non_null.max()}, nulls={null_count}"
                )
            else:
                parts.append(f"  {col} (datetime): all null")

        else:  # object / categorical
            unique_count = series.nunique()
            top = series.value_counts().head(3).index.tolist()
            top_str = ", ".join([repr(v) for v in top])
            parts.append(
                f"  {col} ({dtype_str}): "
                f"{unique_count} unique, top=[{top_str}], nulls={null_count}"
            )

    return "\n".join(parts)


def _build_representative_sample(
    df: pd.DataFrame, max_rows: int = 20
) -> List[Dict[str, Any]]:
    """Return a representative sample: head rows + random middle rows + tail rows.

    For datasets smaller than max_rows, all rows are returned.
    This gives the AI a better picture of data distribution than a plain
    ``head()`` call, without sending the whole dataset.
    """
    n = len(df)
    if n <= max_rows:
        sample_df = df
    else:
        head_n = min(5, max_rows // 4)
        tail_n = min(5, max_rows // 4)
        mid_n = max_rows - head_n - tail_n
        middle = df.iloc[head_n: n - tail_n]
        if len(middle) > mid_n:
            middle = middle.sample(mid_n, random_state=42)
        sample_df = pd.concat([df.head(head_n), middle, df.tail(tail_n)])

    # Serialize datetime columns so json.dumps doesn't fail
    out = sample_df.copy()
    for col in out.select_dtypes(include=["datetime", "datetime64"]).columns:
        out[col] = out[col].astype(str)
    return out.to_dict(orient="records")


def build_dataset_context(dataset_id: str, df: pd.DataFrame, filename: str) -> str:
    """Build and LRU-cache the dataset context string for the AI system prompt.

    The context is keyed by ``dataset_id`` (UUID).  To prevent memory leaks and
    stale context, entries are bounded by an explicit LRU capacity and automatically
    invalidated when a dataset is deleted or replaced.

    Args:
        dataset_id: UUID assigned at upload time.
        df:         Full dataset DataFrame (used only on cache miss or reconstruction).
        filename:   Original filename for display in the prompt.

    Returns:
        A multi-line string describing the dataset schema, column statistics,
        and a representative row sample.
    """
    if dataset_id:
        with _CONTEXT_CACHE_LOCK:
            if dataset_id in _context_cache:
                _context_cache.move_to_end(dataset_id)   # refresh LRU position
                return _context_cache[dataset_id]

    # Compute expensive column statistics and sampling outside the lock to prevent
    # serializing unrelated worker requests.
    rows, cols = df.shape
    col_stats = _build_column_stats(df)
    sample = _build_representative_sample(df, max_rows=20)

    context = (
        f"Dataset: '{filename}'\n"
        f"Dimensions: {rows:,} rows × {cols} columns\n\n"
        f"Column statistics:\n{col_stats}\n\n"
        f"Representative sample ({len(sample)} rows):\n"
        f"{json.dumps(sample, default=str)}"
    )

    if dataset_id:
        max_size = _get_context_cache_max()
        with _CONTEXT_CACHE_LOCK:
            _context_cache[dataset_id] = context
            _context_cache.move_to_end(dataset_id)
            while len(_context_cache) > max_size:
                _context_cache.popitem(last=False)   # evict oldest entry

    logger.debug(
        "Built dataset context for dataset_id='%s' (%.1f KB, cached)",
        dataset_id, len(context) / 1024,
    )
    return context


def _build_system_prompt_v2(dataset_id: str, df: pd.DataFrame, filename: str) -> str:
    """Build the full system prompt using the cached dataset context."""
    context = build_dataset_context(dataset_id, df, filename)
    return (
        "You are a precise data analyst assistant for DataLens Analytics.\n"
        "Answer questions about the dataset below using its column statistics and sample rows.\n"
        "Be concise, professional, and grounded in the data. "
        "When a question requires analysis beyond the visible sample, clearly explain your methodology.\n"
        "If the data does not support a confident answer, say so explicitly.\n\n"
        f"--- DATASET CONTEXT ---\n{context}\n--- END CONTEXT ---"
    )


def _format_history(history: List[Dict[str, str]], max_turns: int = _MAX_HISTORY_TURNS) -> str:
    """Format conversation history as a role-labelled string, bounded by max_turns.

    Older turns beyond the limit are silently dropped.  This keeps the prompt
    within a predictable token budget regardless of conversation length.
    """
    if not history:
        return ""
    truncated = history[-max_turns:]
    lines: List[str] = []
    for msg in truncated:
        role = msg.get("role", "user")
        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {msg.get('content', '').strip()}")
    return "\n".join(lines) + "\n"


def build_query_router() -> QueryRouter:
    return _query_router


def build_retriever() -> Retriever:
    from services.data.vector_store import get_vector_store
    from services.ai.embeddings.embedding_service import get_embedding_service
    try:
        return Retriever(
            vector_store=get_vector_store(),
            embedding_service=get_embedding_service(),
        )
    except Exception as exc:
        logger.warning("Unable to initialize retriever: %s", exc)
        return Retriever(vector_store=get_vector_store(), embedding_service=get_embedding_service())


def build_prompt_builder() -> PromptBuilder:
    return _prompt_builder


def build_citation_builder() -> CitationBuilder:
    return _citation_builder


def build_llm_service() -> RagLLMService:
    return RagLLMService()


# ---------------------------------------------------------------------------
# Filter helper (unrelated to chat — kept in place)
# ---------------------------------------------------------------------------

def _categorical_label_mask(series: pd.Series, condition: List[Any]) -> pd.Series:
    """Boolean mask selecting rows whose value is in ``condition``.

    Numeric/boolean/datetime columns keep exact ``isin`` semantics. For
    object/string/categorical columns, values are compared by string label so a
    selected label such as "1" matches both numeric 1 and string "1" (the same
    label grouping used by compute_filter_options and search_category_values).
    Nulls never match. The input series is not modified.
    """
    if (
        pd.api.types.is_numeric_dtype(series)
        or pd.api.types.is_bool_dtype(series)
        or pd.api.types.is_datetime64_any_dtype(series)
    ):
        return series.isin(condition)
    labels = {str(c) for c in condition}
    return series.notna() & series.astype(str).isin(labels)


def filter_dataframe(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply dictionary filtering criteria to a DataFrame and return filtered DataFrame."""
    if df.empty or not filters:
        return df

    res = df.copy()
    for col, condition in filters.items():
        if col not in res.columns:
            continue
        if isinstance(condition, dict):
            if "range" in condition:
                lo, hi = condition["range"]
                if pd.api.types.is_object_dtype(res[col]):
                    res[col] = pd.to_numeric(res[col], errors="coerce")
                res = res[(res[col] >= lo) & (res[col] <= hi)]
            else:
                if pd.api.types.is_object_dtype(res[col]):
                    res[col] = pd.to_numeric(res[col], errors="coerce")
                if "min" in condition:
                    res = res[res[col] >= condition["min"]]
                if ">=" in condition:
                    res = res[res[col] >= condition[">="]]
                if ">" in condition:
                    res = res[res[col] > condition[">"]]
                if "max" in condition:
                    res = res[res[col] <= condition["max"]]
                if "<=" in condition:
                    res = res[res[col] <= condition["<="]]
                if "<" in condition:
                    res = res[res[col] < condition["<"]]
                if "==" in condition:
                    res = res[res[col] == condition["=="]]
                if "!=" in condition:
                    res = res[res[col] != condition["!="]]
        else:
            if isinstance(condition, list):
                res = res[_categorical_label_mask(res[col], condition)]
            else:
                res = res[res[col] == condition]
    return res


def apply_filters(
    data_or_df: Union[pd.DataFrame, List[Dict[str, Any]]],
    filters: Dict[str, Any],
    limit: Optional[int] = None,
    offset: int = 0,
) -> Dict[str, Any]:
    """Apply dictionary filtering criteria to a DataFrame or row dictionaries.

    Supports bounded pagination via `limit` and `offset`.
    If `limit` is None, matching rows are returned up to `settings.max_filter_limit`.
    """
    if isinstance(data_or_df, pd.DataFrame):
        df = data_or_df.copy()
    else:
        df = pd.DataFrame(data_or_df)

    safe_offset = max(0, offset) if offset is not None else 0
    max_cap = getattr(settings, "max_filter_limit", 50000) if settings else 50000

    if df.empty:
        return {
            "row_count": 0,
            "total": 0,
            "filtered_data": [],
            "limit": limit if limit is not None else max_cap,
            "offset": safe_offset,
            "has_more": False,
            "page": 1,
            "total_pages": 0,
        }

    filtered_df = filter_dataframe(df, filters)
    total_matching = len(filtered_df)

    if limit is not None:
        effective_limit = max(1, min(limit, max_cap))
        is_capped = False
    else:
        if total_matching > max_cap:
            effective_limit = max_cap
            is_capped = True
            logger.warning(
                "Filter response exceeded max_filter_limit (%d > %d); truncating with has_more=True",
                total_matching, max_cap,
            )
        else:
            effective_limit = total_matching
            is_capped = False

    # Deterministic slice
    sliced_df = filtered_df.iloc[safe_offset : safe_offset + effective_limit]
    has_more = (safe_offset + len(sliced_df)) < total_matching

    # Sanitize and serialize only the sliced records
    records = sanitize_records_for_json(sliced_df.to_dict(orient="records"))

    total_pages = (total_matching + effective_limit - 1) // effective_limit if effective_limit > 0 else 0
    current_page = (safe_offset // effective_limit) + 1 if effective_limit > 0 else 1

    resp: Dict[str, Any] = {
        "row_count": total_matching,  # Retained for 100% backward compatibility
        "total": total_matching,
        "filtered_data": records,
        "limit": effective_limit if limit is not None else (max_cap if is_capped else total_matching),
        "offset": safe_offset,
        "has_more": has_more,
        "page": current_page,
        "total_pages": total_pages,
    }
    if is_capped:
        resp["is_truncated"] = True

    return resp


# ---------------------------------------------------------------------------
# Chat response generators
# ---------------------------------------------------------------------------

async def generate_chat_response_async(
    question: str,
    history: List[Dict[str, str]],
    data_or_df: Union[pd.DataFrame, List[Dict[str, Any]]],
    filename: Optional[str] = None,
    dataset_id: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Asynchronously generate a chat response using the AI backend.

    When ``dataset_id`` is supplied the dataset context (column statistics +
    representative sample) is built once and reused on every subsequent call
    for the same dataset — no repeated DataFrame traversal per turn.

    Conversation history is bounded to the last ``_MAX_HISTORY_TURNS`` items
    so the prompt stays within a predictable token budget.

    Args:
        question:    The user's current question.
        history:     Prior conversation turns as {role, content} dicts.
        data_or_df:  Full dataset as a DataFrame or list of row dicts.
        filename:    Original filename shown in the AI context (display only).
        dataset_id:  UUID key for context caching.  Always pass this when the
                     dataset was loaded from the DatasetManager.

    Returns:
        ``{"answer": str}`` dict.

    Raises:
        AIUnavailableError: AI backend returned a 5xx or connection error.
        AIRateLimitError:   AI backend enforced rate limiting (429).
        ValueError:         Called with an empty dataset.
    """
    if isinstance(data_or_df, pd.DataFrame):
        df = data_or_df
    else:
        if not data_or_df:
            raise ValueError("Dataset rows must be provided for chat.")
        df = pd.DataFrame(data_or_df)

    # Choose prompt strategy: v2 (cached context) when dataset_id is available,
    # otherwise fall back to the legacy head(10) prompt.
    if dataset_id:
        system_prompt = _build_system_prompt_v2(
            dataset_id=dataset_id,
            df=df,
            filename=filename or "dataset",
        )
    else:
        system_prompt = build_system_prompt(filename or "dataset", df)

    conversation = _format_history(history)
    full_prompt = f"{system_prompt}\n\n{conversation}User: {question}\nAssistant:"

    session_key = dataset_id or str(uuid.uuid4())
    try:
        router = build_query_router()
        routing = router.route(question=question, df=df, history=history, filename=filename)

        use_rag_flag = bool(routing.get("needs_retrieval"))
        # Apply filters if provided
        filtered_df = filter_dataframe(df, filters) if filters else df
        if filters:
            logger.info("Applied filters: %s. Rows remaining: %d", filters, len(filtered_df))

        use_stats_flag = bool(routing.get("needs_stats"))
        
        analytics_result = None
        if use_stats_flag:
            analytics_engine = build_analytics_engine()
            res = analytics_engine.analyze(question, filtered_df)
            if res and "error" not in res:
                analytics_result = res
                logger.info("Deterministic analytics matched: %s", res)
                # If analytics fully answers it, optionally disable RAG unless router asked for both
                if routing.get("reason") == "analytics":
                    use_rag_flag = False

        if use_rag_flag and dataset_id:
            logger.info("Routing requested retrieval; using RAG orchestration for dataset '%s'.", dataset_id)
        elif use_rag_flag and not dataset_id:
            logger.info("Routing requested retrieval but no dataset_id provided. Falling back to basic chat.")
            use_rag_flag = False

        retrieved_chunks = []
        citations = []
        
        if use_rag_flag:
            try:
                retriever = build_retriever()
                retrieved_chunks = retriever.retrieve(
                    query=question,
                    dataset_id=dataset_id or session_key,
                    top_k=routing.get("retrieval_top_k", _MAX_RAG_TOP_K),
                )
                citation_builder = build_citation_builder()
                citations = citation_builder.build(retrieved_chunks)
            except Exception as exc:
                logger.warning("RAG retrieval failed for dataset '%s': %s", dataset_id or session_key, exc)
                # Fail gracefully by providing no chunks, falling back to basic prompt

        prompt_builder = build_prompt_builder()
        llm_service = build_llm_service()
        
        # Inject deterministic analytics results if any
        if analytics_result:
            import json
            system_prompt += f"\n\nCRITICAL DETERMINISTIC ANALYTICS RESULT:\n{json.dumps(analytics_result)}\n\nThe user's question MUST be answered using this exact deterministic calculation. DO NOT recalculate this value yourself. Just explain this result clearly to the user."

        prompt = prompt_builder.build(
            question=question,
            system_prompt=system_prompt,
            history=history,
            retrieved_chunks=retrieved_chunks,
            citations=citations,
            dataset_context=build_dataset_context(
                None if filters else dataset_id,
                filtered_df if filters else df,
                filename or "dataset"
            ) if dataset_id else None,
        )
        
        answer = await llm_service.generate(prompt)
        if not answer:
            answer = generate_local_answer(question, df)
            
        resp = {"answer": answer, "citations": citations}
        if analytics_result:
            resp["analytics"] = analytics_result
            
        return resp

    except RuntimeError as exc:
        msg = str(exc)
        logger.warning(
            "AI call failed for dataset_id='%s': %s",
            dataset_id or "(no id)", msg,
        )
        if analytics_result:
            op = analytics_result.get("operation", "calculation")
            col = analytics_result.get("column", "")
            val = analytics_result.get("value", "")
            ans = f"Based on deterministic analysis, the {op} of {col} is {val}."
            return {"answer": ans, "citations": citations, "analytics": analytics_result}

        # Map to typed errors so the endpoint can return the correct HTTP code
        if "429" in msg or "rate" in msg.lower():
            raise AIRateLimitError(msg) from exc
        if any(code in msg for code in ("500", "502", "503")) or "connect" in msg.lower():
            raise AIUnavailableError(msg) from exc
        # Non-network generic failure: return a local fallback answer instead
        fallback = generate_local_answer(question, df)
        answer = (
            "The AI assistant is temporarily unavailable. "
            f"Here is a local dataset summary instead:\n\n{fallback}"
        )
        return {"answer": answer}

    except Exception as exc:
        logger.warning(
            "Unexpected AI error for dataset_id='%s': %s",
            dataset_id or "(no id)", exc,
        )
        if analytics_result:
            op = analytics_result.get("operation", "calculation")
            col = analytics_result.get("column", "")
            val = analytics_result.get("value", "")
            ans = f"Based on deterministic analysis, the {op} of {col} is {val}."
            return {"answer": ans, "citations": citations, "analytics": analytics_result}

        fallback = generate_local_answer(question, df)
        answer = (
            "The AI assistant encountered an unexpected error. "
            f"Here is a local dataset summary instead:\n\n{fallback}"
        )
        return {"answer": answer}


def generate_chat_response(
    question: str,
    history: List[Dict[str, str]],
    data: List[Dict[str, Any]],
    filename: Optional[str] = None,
) -> Dict[str, str]:
    """Synchronous chat response generator — kept for backward compatibility.

    New code should use ``generate_chat_response_async`` via ``await``.
    """
    if not data:
        raise ValueError("Dataset rows must be provided for chat.")

    df = pd.DataFrame(data)
    system_prompt = build_system_prompt(filename or "dataset", df)
    conversation = _format_history(history)
    full_prompt = f"{system_prompt}\n\n{conversation}User: {question}\nAssistant:"

    try:
        answer = call_ai(full_prompt)
    except Exception as exc:
        logger.warning("Synchronous LLM call failed, using local fallback: %s", exc)
        fallback = generate_local_answer(question, df)
        answer = (
            "The AI assistant is temporarily unavailable. "
            f"Here is a local dataset summary instead:\n\n{fallback}"
        )

    return {"answer": answer}

