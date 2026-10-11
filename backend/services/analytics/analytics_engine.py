import re
import math
import logging
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """Performs deterministic statistical operations on pandas DataFrames based on user queries."""
    
    def __init__(self):
        # Operations mapped to keywords (regex word boundaries will be used)
        self.op_keywords = {
            "mean": ["average", "mean", "avg"],
            "median": ["median"],
            "sum": ["sum", "total", "summation"],
            "min": ["minimum", "min", "lowest", "smallest"],
            "max": ["maximum", "max", "highest", "largest"],
            "count": ["count", "how many", "number of"],
            "std": ["standard deviation", "std", "stdev"],
            "variance": ["variance", "var"],
            "percentage": ["percentage", "percent", "%"],
            "correlation": ["correlation", "correlate", "corr"],
        }
    
    def _detect_operation(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        
        for op, keywords in self.op_keywords.items():
            for kw in keywords:
                if kw == "%":
                    if "%" in query_lower:
                        return op
                elif re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    return op
        return None
        
    def _is_numeric(self, series: pd.Series) -> bool:
        return pd.api.types.is_numeric_dtype(series)
        
    def _resolve_column(self, query: str, df: pd.DataFrame, numeric_only: bool = False, exclude: list = None) -> Optional[str]:
        query_lower = query.lower()
        cols = list(df.columns)
        if exclude:
            cols = [c for c in cols if c not in exclude]
            
        matched_cols = []
        for col in cols:
            col_lower = str(col).lower()
            if numeric_only and not self._is_numeric(df[col]):
                continue
            pattern = r'(?:^|\W)' + re.escape(col_lower) + r'(?:$|\W)'
            if re.search(pattern, query_lower):
                matched_cols.append(col)
                
        if not matched_cols:
            return None
            
        if len(matched_cols) > 1:
            for col in matched_cols:
                if str(col).lower() == query_lower.strip():
                    return col
            matched_cols.sort(key=len, reverse=True)
            return matched_cols[0]
            
        return matched_cols[0]

    def _resolve_two_columns(self, query: str, df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
        query_lower = query.lower()
        cols = list(df.columns)
        matched_cols = []
        for col in cols:
            col_lower = str(col).lower()
            pattern = r'(?:^|\W)' + re.escape(col_lower) + r'(?:$|\W)'
            if re.search(pattern, query_lower):
                matched_cols.append(col)
                if len(matched_cols) == 2:
                    break
        if len(matched_cols) == 2:
            return matched_cols[0], matched_cols[1]
        elif len(matched_cols) == 1:
            return matched_cols[0], None
        return None, None
        
    def _resolve_group_value(self, query: str, df: pd.DataFrame, col: str) -> Optional[Any]:
        if col not in df.columns:
            return None
        query_lower = query.lower()
        unique_vals = df[col].dropna().unique()
        for val in unique_vals:
            if isinstance(val, str) and val.lower() in query_lower:
                return val
        return None
        
    def _safe_float(self, value: Any) -> Any:
        if pd.isna(value) or math.isinf(value) or math.isnan(value):
            return None
        if isinstance(value, (np.floating, float)):
            return float(round(value, 4))
        if isinstance(value, (np.integer, int)):
            return int(value)
        return value

    def analyze(self, query: str, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {"error": "Dataset is empty."}
            
        operation = self._detect_operation(query)
        if not operation:
            return {"error": "No supported analytical operation detected."}
            
        if operation == "correlation":
            col1, col2 = self._resolve_two_columns(query, df)
            if not col1 or not col2:
                return {"error": "Correlation requires two columns to be identified in the query.", "operation": operation}
            if not self._is_numeric(df[col1]) or not self._is_numeric(df[col2]):
                return {"error": f"Both columns must be numeric.", "operation": operation}
            valid_df = df[[col1, col2]].dropna()
            if len(valid_df) < 2 or valid_df[col1].std() == 0 or valid_df[col2].std() == 0:
                return {"error": "Insufficient valid data for correlation.", "operation": operation}
            return {"operation": operation, "column1": col1, "column2": col2, "value": self._safe_float(valid_df[col1].corr(valid_df[col2]))}
            
        num_required = operation in ["mean", "median", "sum", "min", "max", "std", "variance"]
        col = self._resolve_column(query, df, numeric_only=num_required)
        
        if operation == "count" and not col:
            return {"operation": "count", "value": len(df)}
            
        if operation == "percentage":
            if not col:
                query_lower = query.lower()
                for c in df.columns:
                    unique_vals = df[c].dropna().unique()
                    for val in unique_vals:
                        if isinstance(val, str) and val.lower() in query_lower:
                            col = c
                            break
                    if col: break
            if not col: return {"error": "Target column could not be identified for percentage.", "operation": operation}
            val = self._resolve_group_value(query, df, col)
            if val is not None:
                total_valid = len(df[col].dropna())
                if total_valid == 0: return {"error": "No valid data.", "operation": operation}
                return {"operation": "percentage", "column": col, "target_value": val, "value": self._safe_float((len(df[df[col] == val]) / total_valid) * 100)}
            return {"error": f"Could not determine target value.", "operation": operation}

        if not col:
            return {"error": "Target column could not be identified.", "operation": operation}
            
        # Grouped analytics (e.g. Which country has the highest sales?)
        group_col = self._resolve_column(query, df, exclude=[col])
        if group_col and not self._is_numeric(df[group_col]) and operation in ["max", "min"]:
            agg_df = df.groupby(group_col)[col].sum()
            best_group = agg_df.idxmax() if operation == "max" else agg_df.idxmin()
            best_val = agg_df.max() if operation == "max" else agg_df.min()
            return {
                "operation": f"grouped_{operation}",
                "column": col,
                "group_by": group_col,
                "group_value": str(best_group),
                "value": self._safe_float(best_val)
            }
            
        series = df[col]
        if num_required:
            if not self._is_numeric(series):
                return {"error": f"Column '{col}' is not numeric.", "operation": operation, "column": col}
            series = series.replace([np.inf, -np.inf], np.nan)
            valid_series = series.dropna()
            if len(valid_series) == 0:
                return {"error": f"Column '{col}' has no valid numeric data.", "operation": operation, "column": col}
                
            try:
                if operation == "mean": val = valid_series.mean()
                elif operation == "median": val = valid_series.median()
                elif operation == "sum": val = valid_series.sum()
                elif operation == "min": val = valid_series.min()
                elif operation == "max": val = valid_series.max()
                elif operation == "std":
                    if len(valid_series) < 2: return {"error": "Insufficient data", "operation": operation}
                    val = valid_series.std(ddof=1)
                elif operation == "variance":
                    if len(valid_series) < 2: return {"error": "Insufficient data", "operation": operation}
                    val = valid_series.var(ddof=1)
                else: return {"error": "Unknown operation.", "operation": operation}
                
                return {"operation": operation, "column": col, "value": self._safe_float(val)}
            except Exception as e:
                logger.error("Analytics computation error: %s", e)
                return {"error": "Calculation error.", "operation": operation, "column": col}
                
        if operation == "count":
            return {"operation": "count", "column": col, "value": int(series.count())}

        return {"error": f"Operation '{operation}' not fully implemented.", "operation": operation}

_global_analytics_engine = None

def get_analytics_engine() -> AnalyticsEngine:
    global _global_analytics_engine
    if _global_analytics_engine is None:
        _global_analytics_engine = AnalyticsEngine()
    return _global_analytics_engine
