from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

from backend.api_helpers import apply_filters

app = FastAPI()

class FilterRequest(BaseModel):
    filters: Dict[str, Any]
    data: List[Dict[str, Any]]

@app.post('/')
async def filter_data(req: FilterRequest):
    try:
        result = apply_filters(req.data, req.filters)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Failed to apply filters: {exc}') from exc
    return result
