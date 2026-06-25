from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from backend.api_helpers import apply_filters

router = APIRouter()

class FilterRequest(BaseModel):
    filters: Dict[str, Any]
    data: Optional[List[Dict[str, Any]]] = None
    filename: Optional[str] = None  # Support both patterns

@router.post('/')
async def filter_data(req: FilterRequest):
    # Validate that we have either data or filename
    if not req.data and not req.filename:
        raise HTTPException(status_code=400, detail="Either 'data' or 'filename' must be provided")
    
    try:
        result = apply_filters(req.data, req.filters)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Failed to apply filters: {exc}') from exc
    return result
