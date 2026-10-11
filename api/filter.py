import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from backend.api_helpers import apply_filters, check_dataset_ready
    from backend.dataset_manager import dataset_manager
except ImportError:
    from api_helpers import apply_filters, check_dataset_ready
    from dataset_manager import dataset_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class FilterRequest(BaseModel):
    filters: Dict[str, Any]
    dataset_id: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None


@router.post("/")
async def filter_data(req: FilterRequest) -> Dict[str, Any]:
    """Serverless API endpoint to apply filtering criteria to dataset rows."""
    if req.dataset_id:
        meta = dataset_manager.get_metadata(req.dataset_id)
        check_dataset_ready(meta)

        df = dataset_manager.get_dataset(req.dataset_id)
        if df is None:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{req.dataset_id}' not found. Upload a file first and use the returned dataset_id."
            )
        target_data = df
    elif req.data is not None:
        target_data = req.data
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide 'dataset_id' or inline 'data' rows to filter."
        )

    try:
        return apply_filters(target_data, req.filters)
    except Exception as exc:
        logger.exception("Filter processing failed: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to apply filters to the dataset")

