from fastapi import APIRouter, File, HTTPException, UploadFile
from backend.api_helpers import parse_dataset_bytes

router = APIRouter()

@router.post('/')
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail='Unsupported file type')

    try:
        contents = await file.read()
        result = parse_dataset_bytes(contents, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Failed to parse file: {exc}') from exc

    return result
