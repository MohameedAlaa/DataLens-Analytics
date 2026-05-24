import io
import json
from typing import Any, Dict, List

import pandas as pd
from .AI import call_qwen


def classify_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [c for c in df.columns if pd.api.types.is_object_dtype(df[c])]
    date = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    return {
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "date_columns": date,
    }


def format_numeric(value: Any) -> str:
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


def parse_dataset_bytes(contents: bytes, filename: str) -> Dict[str, Any]:
    if filename.lower().endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    else:
        df = pd.read_excel(io.BytesIO(contents))

    cols = list(df.columns)
    dtypes = {c: str(df[c].dtype) for c in cols}
    preview = df.head(1000).to_dict(orient='records')
    types = classify_columns(df)
    return {
        'filename': filename,
        'columns': cols,
        'dtypes': dtypes,
        'shape': df.shape,
        'preview': preview,
        **types,
    }


def build_system_prompt(filename: str, df: pd.DataFrame) -> str:
    rows, cols = df.shape
    column_info = ", ".join([f"{c} ({str(df[c].dtype)})" for c in df.columns])
    sample = df.head(10).to_dict(orient='records')
    return (
        f"You are a data analyst assistant for 'DataLens Analytics'.\n"
        f"The user has uploaded a dataset: '{filename or 'dataset'}'\n"
        f"- Dimensions: {rows} rows, {cols} columns\n"
        f"- Columns: {column_info}\n"
        f"- Data Sample: {json.dumps(sample)}\n\n"
        f"Instructions:\n"
        f"1. Be concise, professional, and helpful.\n"
        f"2. Use the provided sample and metadata to answer questions.\n"
        f"3. If you need to perform calculations not evident from the sample, explain how you would do it.\n"
        f"4. If you don't know the answer or the data doesn't support it, say so."
    )


def apply_filters(data: List[Dict[str, Any]], filters: Dict[str, Any]) -> Dict[str, Any]:
    df = pd.DataFrame(data)
    if df.empty:
        return {'row_count': 0, 'filtered_data': []}

    for col, condition in filters.items():
        if col not in df.columns:
            continue
        if isinstance(condition, dict) and 'range' in condition:
            lo, hi = condition['range']
            if pd.api.types.is_object_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df[(df[col] >= lo) & (df[col] <= hi)]
        else:
            if isinstance(condition, list):
                df = df[df[col].isin(condition)]
            else:
                df = df[df[col] == condition]

    filtered = df.to_dict(orient='records')
    return {'row_count': len(df), 'filtered_data': filtered}


def generate_chat_response(question: str, history: List[Dict[str, str]], data: List[Dict[str, Any]], filename: str | None = None) -> Dict[str, str]:
    if not data:
        raise ValueError('Dataset rows must be provided for chat.')

    df = pd.DataFrame(data)
    system_prompt = build_system_prompt(filename or 'dataset', df)
    conversation = ''
    for msg in history or []:
        role_label = 'User' if msg.get('role') == 'user' else 'Assistant'
        conversation += f"{role_label}: {msg.get('content')}\n"

    full_prompt = f"{system_prompt}\n\n{conversation}User: {question}\nAssistant:"

    try:
        answer = call_qwen(full_prompt)
    except Exception:
        answer = (
            "The AI assistant backend is currently unavailable, so I am returning a local dataset response instead. "
            f"\n\n{generate_local_answer(question, df)}"
        )
    return {'answer': answer}
