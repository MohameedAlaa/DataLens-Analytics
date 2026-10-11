import io
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
import pandas as pd

try:
    from backend.api_helpers import detect_csv_encoding, parse_dataset_bytes
    from backend.dataset_manager import dataset_manager
except ImportError:
    from api_helpers import detect_csv_encoding, parse_dataset_bytes
    from dataset_manager import dataset_manager

try:
    from backend.services.ai.rag.ingestion_pipeline import ingestion_pipeline
except ImportError:
    try:
        from services.ai.rag.ingestion_pipeline import ingestion_pipeline
    except ImportError:
        ingestion_pipeline = None

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/")
async def upload(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Dict[str, Any]:
    """Serverless API endpoint to validate, parse, and register uploaded CSV or Excel dataset files."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload request.")

    logger.info("Serverless upload request received for '%s'", file.filename)

    try:
        contents = await file.read()
        parsed_result = parse_dataset_bytes(contents, file.filename, preview_limit=1000)

        # Parse full DataFrame for dataset_manager registration
        if file.filename.lower().endswith(".csv"):
            encoding = detect_csv_encoding(contents)
            df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
        else:
            df = pd.read_excel(io.BytesIO(contents))

        dataset_id = parsed_result["dataset_id"]
        dataset_manager.register_dataset(
            df=df,
            filename=file.filename,
            dataset_id=dataset_id,
        )

        if background_tasks is not None and ingestion_pipeline is not None:
            background_tasks.add_task(
                ingestion_pipeline.run_ingestion,
                dataset_id,
                df,
                file.filename,
                dataset_manager,
            )

        return parsed_result
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


