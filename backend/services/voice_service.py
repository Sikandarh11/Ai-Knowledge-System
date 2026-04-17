from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from uuid import uuid4
from typing import Any

from anyio import to_thread
from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.storage.database import SessionLocal
from backend.storage.repositories.chat import ChatRepository
from backend.tools.stt_tool import transcribe
from backend.services.intent_service import extract_intent
from backend.services.router_service import route_intent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIO_SAVE_DIR = PROJECT_ROOT / "backend" / "test" / "saved_audio"


class _LocalUploadFile:
    def __init__(self, path: Path, content_type: str = "audio/wav") -> None:
        self.path = path
        self.filename = path.name
        self.content_type = content_type

    async def read(self) -> bytes:
        return self.path.read_bytes()


def _load_json(value: str | None, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if default is None:
        default = {}
    if not value:
        return default
    try:
        import json

        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else default
    except Exception:  # noqa: BLE001
        return default


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "audio").strip())
    return cleaned.strip("._") or "audio"


def _record_audio_sync(output_path: Path, duration_seconds: int, sample_rate: int) -> None:
    try:
        import sounddevice as sd
        from scipy.io.wavfile import write
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Audio recording dependencies are missing. Install sounddevice and scipy."
        ) from exc

    frames = int(duration_seconds * sample_rate)
    audio_data = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()
    write(str(output_path), sample_rate, audio_data)


async def record_and_save_audio(
    duration_seconds: int = 5,
    sample_rate: int = 44100,
    filename_prefix: str = "recorded_audio",
    target_dir: Path | None = None,
) -> dict[str, Any]:
    save_dir = target_dir or DEFAULT_AUDIO_SAVE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    safe_prefix = _safe_name(filename_prefix)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_prefix}_{timestamp}.wav"
    output_path = save_dir / filename

    await to_thread.run_sync(_record_audio_sync, output_path, duration_seconds, sample_rate)

    return {
        "saved": True,
        "filename": filename,
        "duration_seconds": duration_seconds,
        "sample_rate": sample_rate,
        "content_type": "audio/wav",
        "path": str(output_path),
    }


async def process_audio(file) -> dict[str, Any]:
    text = await transcribe(file)
    if not text or not str(text).strip():
        raise ValueError("Transcription returned empty text.")

    intent_json = await extract_intent(text)
    if not isinstance(intent_json, dict):
        raise ValueError("Intent extraction returned an invalid payload.")

    result = await route_intent(intent_json, text)
    if not isinstance(result, dict):
        raise ValueError("Intent router returned an invalid payload.")

    return result


async def analyze_audio(file) -> dict[str, Any]:
    text = await transcribe(file)
    if not text or not str(text).strip():
        raise ValueError("Transcription returned empty text.")

    intent_json = await extract_intent(text)
    if not isinstance(intent_json, dict):
        raise ValueError("Intent extraction returned an invalid payload.")

    return {
        "text": text,
        "intent": intent_json,
    }


async def execute_intent(intent_json: dict[str, Any], text: str) -> dict[str, Any]:
    if not text or not str(text).strip():
        raise ValueError("Transcription returned empty text.")

    if not isinstance(intent_json, dict):
        raise ValueError("Intent extraction returned an invalid payload.")

    result = await route_intent(intent_json, text)
    if not isinstance(result, dict):
        raise ValueError("Intent router returned an invalid payload.")

    return result


async def store_uploaded_audio(file: UploadFile, *, target_dir: Path | None = None) -> dict[str, Any]:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("audio/"):
        raise ValueError("Invalid file type. Please upload an audio file.")

    filename = _safe_name((file.filename or "voice_message").strip())
    suffix = Path(filename).suffix or ".webm"
    save_dir = target_dir or DEFAULT_AUDIO_SAVE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{suffix}"
    file_path = save_dir / stored_name

    data = await file.read()
    if not data:
        raise ValueError("Uploaded audio file is empty.")

    file_path.write_bytes(data)
    return {
        "filename": file.filename or stored_name,
        "stored_filename": stored_name,
        "file_path": str(file_path),
        "content_type": content_type,
        "size_bytes": len(data),
    }


def create_voice_message(
    db: Session,
    *,
    user_id: str,
    workspace_id: int,
    audio_info: dict[str, Any],
) -> dict[str, Any]:
    repo = ChatRepository(db)
    metadata = {
        "message_type": "voice",
        "voice": {
            "status": "processing",
            "transcript": "",
            "error": None,
            "audio": {
                "filename": audio_info.get("filename"),
                "stored_filename": audio_info.get("stored_filename"),
                "content_type": audio_info.get("content_type"),
                "size_bytes": audio_info.get("size_bytes"),
            },
        },
    }
    message = repo.create_message(
        user_id=user_id,
        workspace_id=workspace_id,
        role="user",
        content="",
        metadata=metadata,
    )
    return repo.serialize_message(message)


async def transcribe_voice_message_task(message_id: int, audio_path: str) -> None:
    db = SessionLocal()
    repo = ChatRepository(db)
    message = repo.get_message_by_id(message_id=message_id)

    try:
        if message is None:
            return

        meta = _load_json(message.metadata_json, {})
        voice_meta = meta.get("voice") if isinstance(meta.get("voice"), dict) else {}
        audio_meta = voice_meta.get("audio") if isinstance(voice_meta.get("audio"), dict) else {}

        file_path = Path(audio_path)
        local_file = _LocalUploadFile(
            file_path,
            content_type=str(audio_meta.get("content_type") or "audio/wav"),
        )
        transcript = (await transcribe(local_file)).strip()
        voice_meta["status"] = "needs_review"
        voice_meta["transcript"] = transcript
        voice_meta["error"] = None
        meta["voice"] = voice_meta

        repo.update_message(message, metadata=meta)
    except Exception as exc:  # noqa: BLE001
        if message is not None:
            meta = _load_json(message.metadata_json, {})
            voice_meta = meta.get("voice") if isinstance(meta.get("voice"), dict) else {}
            voice_meta["status"] = "error"
            voice_meta["error"] = str(exc)
            meta["voice"] = voice_meta
            repo.update_message(message, metadata=meta)
    finally:
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass
        db.close()


def get_voice_message_status(
    db: Session,
    *,
    message_id: int,
    user_id: str,
) -> dict[str, Any] | None:
    repo = ChatRepository(db)
    message = repo.get_message_for_user(message_id=message_id, user_id=user_id)
    if message is None:
        return None

    serialized = repo.serialize_message(message)
    metadata = serialized.get("metadata") if isinstance(serialized.get("metadata"), dict) else {}
    voice_meta = metadata.get("voice") if isinstance(metadata.get("voice"), dict) else {}

    return {
        "message_id": serialized.get("id"),
        "status": voice_meta.get("status") or "unknown",
        "transcript": voice_meta.get("transcript") or "",
        "error": voice_meta.get("error"),
        "workspace_id": serialized.get("workspace_id"),
        "message_type": metadata.get("message_type") or "voice",
    }
