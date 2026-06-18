# FastAPI backend for DataLens Analytics

import io
import json
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import httpx
import os
from AI import call_qwen

app = FastAPI()

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In‑memory store for uploaded dataframes: filename -> DataFrame
DATASTORE: Dict[str, pd.DataFrame] = {}

# The chat assistant uses Google Gemini 1.5 Flash via the Google Generative Language API (see AI.py)

# Helper to detect column types
def classify_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [c for c in df.columns if pd.api.types.is_object_dtype(df[c])]
    date = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    return {
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "date_columns": date,
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Unsupported file type")
        contents = await file.read()
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        # Store dataframe in memory
        DATASTORE[file.filename] = df
        # Basic info
        cols = list(df.columns)
        dtypes = {c: str(df[c].dtype) for c in cols}
        shape = df.shape
        # Prepare safe preview
        preview_df = df.head(100).copy()
        for col in preview_df.select_dtypes(include=["datetime", "datetime64"]).columns:
            preview_df[col] = preview_df[col].astype(str)
        preview = preview_df.to_dict(orient="records")
        types = classify_columns(df)
        return {
            "filename": file.filename,
            "columns": cols,
            "dtypes": dtypes,
            "shape": shape,
            "preview": preview,
            **types,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback, sys
        print(f"Upload endpoint unexpected error:\n{traceback.format_exc()}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="Internal server error during file upload")

class FilterRequest(BaseModel):
    filters: Dict[str, Any]
    filename: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None

@app.post("/filter")
async def filter_data(req: FilterRequest):
    # Support both patterns: filename (with DATASTORE) or data (direct)
    if req.filename:
        if req.filename not in DATASTORE:
            raise HTTPException(status_code=404, detail="File not found")
        df = DATASTORE[req.filename]
    elif req.data:
        df = pd.DataFrame(req.data)
    else:
        raise HTTPException(status_code=400, detail="Either 'filename' or 'data' must be provided")
    
    for col, condition in req.filters.items():
        if col not in df.columns:
            continue
        if isinstance(condition, dict) and "range" in condition:
            lo, hi = condition["range"]
            df = df[(df[col] >= lo) & (df[col] <= hi)]
        else:
            # equality or inclusion list
            if isinstance(condition, list):
                df = df[df[col].isin(condition)]
            else:
                df = df[df[col] == condition]
    filtered = df.to_dict(orient="records")
    summary = {
        "row_count": len(df),
        "filtered_data": filtered,
    }
    return JSONResponse(content=summary)

@app.get("/stats/{filename}")
async def get_stats(filename: str):
    if filename not in DATASTORE:
        raise HTTPException(status_code=404, detail="File not found")
    df = DATASTORE[filename]
    stats = {}
    for col in df.columns:
        col_series = df[col]
        stats[col] = {
            "nulls": int(col_series.isnull().sum()),
            "unique": int(col_series.nunique()),
            "top": col_series.mode().iloc[0] if not col_series.mode().empty else None,
        }
        if pd.api.types.is_numeric_dtype(col_series):
            stats[col].update({
                "mean": col_series.mean(),
                "std": col_series.std(),
                "min": col_series.min(),
                "max": col_series.max(),
            })
    # Correlations among numeric columns only
    numeric_cols = df.select_dtypes(include='number').columns
    corr = df[numeric_cols].corr().fillna(0).to_dict()
    return {"per_column_stats": stats, "correlations": corr}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    filename: str
    history: List[ChatMessage] = Field(default_factory=list)
    context_data: Dict[str, Any] | None = None


def format_numeric(value: float) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def generate_local_answer(question: str, df: pd.DataFrame) -> str:
    question_text = question.lower()
    if 'summarize' in question_text or 'summary' in question_text:
        return (
            f"Dataset summary:\n- Rows: {df.shape[0]}\n- Columns: {df.shape[1]}\n"
            f"- Column names: {', '.join(df.columns)}\n"
            f"- Numeric columns: {', '.join([c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]) or 'none'}\n"
            f"- Categorical columns: {', '.join([c for c in df.columns if pd.api.types.is_object_dtype(df[c])]) or 'none'}."
        )

    for col in df.columns:
        if col.lower() in question_text:
            if 'average' in question_text or 'mean' in question_text:
                if pd.api.types.is_numeric_dtype(df[col]):
                    return f"The average of '{col}' is {format_numeric(df[col].mean())}."
                return f"Column '{col}' is not numeric, so its average cannot be calculated."

            if 'top' in question_text or 'most common' in question_text or 'highest' in question_text:
                values = df[col].value_counts().head(5)
                if values.empty:
                    return f"No values found for column '{col}'."
                formatted = ', '.join([f"{idx} ({count})" for idx, count in values.items()])
                return f"Top values for '{col}': {formatted}."

            if 'count' in question_text or 'how many' in question_text:
                return f"Column '{col}' has {df[col].nunique()} unique values and {df[col].count()} non-null entries."

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if 'average' in question_text or 'mean' in question_text:
        if len(numeric_cols) == 1:
            col = numeric_cols[0]
            return f"The average of '{col}' is {format_numeric(df[col].mean())}."
        if len(numeric_cols) > 1:
            values = ', '.join([f"{c}: {format_numeric(df[c].mean())}" for c in numeric_cols])
            return f"Averages by numeric column: {values}."

    if 'top' in question_text or 'most common' in question_text:
        target_columns = [c for c in df.columns if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_numeric_dtype(df[c])]
        if target_columns:
            top_cols = ', '.join(target_columns[:3])
            return f"I can highlight the most common values for columns like: {top_cols}. Please specify one of them."

    return (
        "I couldn't fully answer this question without the configured AI service, "
        "but here is some dataset context you can use:\n"
        f"- Rows: {df.shape[0]}\n- Columns: {df.shape[1]}\n"
        f"- Columns: {', '.join(df.columns)}"
    )

@app.post("/chat")
async def chat(req: ChatRequest):
    if req.filename not in DATASTORE:
        raise HTTPException(status_code=404, detail="File not found")
    df = DATASTORE[req.filename]
    # Build system prompt
    rows, cols = df.shape
    column_info = ", ".join([f"{c} ({str(df[c].dtype)})" for c in df.columns])
    sample = df.head(10).to_dict(orient="records")
    system_prompt = (
        f"You are a data analyst assistant for 'DataLens Analytics'.\n"
        f"The user has uploaded a dataset: '{req.filename}'\n"
        f"- Dimensions: {rows} rows, {cols} columns\n"
        f"- Columns: {column_info}\n"
        f"- Data Sample: {json.dumps(sample)}\n\n"
        f"Instructions:\n"
        f"1. Be concise, professional, and helpful.\n"
        f"2. Use the provided sample and metadata to answer questions.\n"
        f"3. If you need to perform calculations not evident from the sample, explain how you would do it.\n"
        f"4. If you don't know the answer or the data doesn't support it, say so."
    )

    # Construct the full prompt with history
    conversation = ""
    for msg in req.history:
        role_label = "User" if msg.role == "user" else "Assistant"
        conversation += f"{role_label}: {msg.content}\n"
    
    full_prompt = f"{system_prompt}\n\n{conversation}User: {req.question}\nAssistant:"

    try:
        answer = call_qwen(full_prompt)
    except Exception as e:
        fallback = generate_local_answer(req.question, df)
        print(f"LLM fallback: {e}")
        return {
            "answer": (
                "The AI assistant backend is currently unavailable, so I am returning a local dataset response instead. "
                f"\n\n{fallback}"
            )
        }
    return {"answer": answer}
