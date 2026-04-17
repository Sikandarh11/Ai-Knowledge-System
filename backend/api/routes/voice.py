from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.services.chat_service import ChatService, GLOBAL_CHAT_WORKSPACE_TOKEN
from backend.services.voice_service import (
    analyze_audio,
    create_voice_message,
    execute_intent,
    get_voice_message_status,
    record_and_save_audio,
    store_uploaded_audio,
    transcribe_voice_message_task,
)
from backend.storage.database import get_db
from backend.storage.models import User

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/upload")
async def voice_upload(
    background_tasks: BackgroundTasks,
    workspace_id: str = Form(
        default=GLOBAL_CHAT_WORKSPACE_TOKEN,
        description="Workspace id/uuid. Leave empty to use global chat.",
    ),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requested_workspace = (workspace_id or GLOBAL_CHAT_WORKSPACE_TOKEN).strip() or GLOBAL_CHAT_WORKSPACE_TOKEN
    chat_service = ChatService(db)

    try:
        resolved_workspace_id = chat_service.resolve_workspace_db_id(
            requested_workspace,
            user_id=str(current_user.id),
            create_if_missing=requested_workspace == GLOBAL_CHAT_WORKSPACE_TOKEN,
        )
        if resolved_workspace_id is None:
            raise HTTPException(status_code=400, detail="workspace_id is required")

        audio_info = await store_uploaded_audio(file)
        try:
            message = create_voice_message(
                db,
                user_id=str(current_user.id),
                workspace_id=resolved_workspace_id,
                audio_info=audio_info,
            )
        except Exception:
            Path(audio_info["file_path"]).unlink(missing_ok=True)
            raise

        background_tasks.add_task(
            transcribe_voice_message_task,
            int(message["id"]),
            str(audio_info["file_path"]),
        )

        return {
            "type": "voice_message",
            "status": "processing",
            "message": "Audio uploaded. Transcription is running in the background.",
            "data": {
                "message_id": message["id"],
                "workspace_id": resolved_workspace_id,
                "voice_status": "processing",
            },
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Voice upload failed: {exc}") from exc


@router.get("/status/{message_id}")
def voice_status(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status_payload = get_voice_message_status(
        db,
        message_id=message_id,
        user_id=str(current_user.id),
    )
    if status_payload is None:
        raise HTTPException(status_code=404, detail="Voice message not found")

    return {
        "type": "voice_message_status",
        "status": "success",
        "message": "Voice message status fetched.",
        "data": status_payload,
    }


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
async def voice_process(
    file: UploadFile = File(...),
    approve_action: bool = Query(
        False,
        description="If false, only preview transcript/intent. If true, execute the detected action.",
    ),
):
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")

    try:
        analysis = await analyze_audio(file)
        text = analysis.get("text", "")
        intent = analysis.get("intent", {})

        if not approve_action:
            return {
                "type": "voice_preview",
                "status": "pending_approval",
                "message": "Transcript and intent extracted. Re-submit with approve_action=true to execute.",
                "data": {
                    "transcript": text,
                    "intent": intent,
                    "approved": False,
                },
            }

        result = await execute_intent(intent, text)
        if isinstance(result, dict):
            result["preview"] = {
                "transcript": text,
                "intent": intent,
                "approved": True,
            }
        return result
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {exc}") from exc
