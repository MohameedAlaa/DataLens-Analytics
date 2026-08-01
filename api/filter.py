import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api_helpers import apply_filters

logger = logging.getLogger(__name__)
router = APIRouter()


class FilterRequest(BaseModel):
    filters: Dict[str, Any]
    data: Optional[List[Dict[str, Any]]] = None
    filename: Optional[str] = None


@router.post("/")
async def filter_data(req: FilterRequest) -> Dict[str, Any]:
    """Serverless API endpoint to apply filtering criteria to dataset rows."""
    if req.data is None:
        if req.filename:
            raise HTTPException(
                status_code=400,
                detail="Stateless API filtering requires dataset 'data' rows to be included in the request body."
            )
        raise HTTPException(status_code=400, detail="Either 'data' or 'filename' with dataset rows must be provided")

    try:
        return apply_filters(req.data, req.filters)
    except Exception as exc:
        logger.exception("Filter processing failed: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to apply filters to the dataset")

