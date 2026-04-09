from fastapi import APIRouter, File, UploadFile

from backend.ingestion.uploader import handle_upload

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    return await handle_upload(file)
