import logging
from typing import Any, Dict
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.api_helpers import parse_dataset_bytes

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/")
async def upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Serverless API endpoint to validate and parse uploaded CSV or Excel dataset files."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload request.")

    logger.info("Serverless upload request received for '%s'", file.filename)

    try:
        contents = await file.read()
        return parse_dataset_bytes(contents, file.filename, preview_limit=1000)
    except ValueError as exc:
        err_msg = str(exc)
        logger.warning("Upload validation failed for '%s': %s", file.filename, err_msg)
        if "exceeds maximum allowed limit" in err_msg:
            raise HTTPException(status_code=413, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload processing failed for '%s': %s", file.filename, exc)
        raise HTTPException(status_code=500, detail="Failed to process dataset upload due to an internal server error.")


