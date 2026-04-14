from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend.services.voice_service import process_audio, record_and_save_audio

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/record")
async def voice_record(
    duration_seconds: int = Query(5, ge=1, le=60, description="Recording length in seconds"),
    sample_rate: int = Query(44100, ge=8000, le=96000, description="Audio sample rate"),
):
    try:
        result = await record_and_save_audio(
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
        )
        return {
            "type": "record",
            "status": "success",
            "message": "Audio recorded and saved.",
            "data": result,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Audio recording failed: {exc}") from exc


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
