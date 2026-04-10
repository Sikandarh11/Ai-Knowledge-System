from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.services.voice_service import process_audio

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/process")
async def voice_process(file: UploadFile = File(...)):
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")

    try:
        result = await process_audio(file)
        return result
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {exc}") from exc
