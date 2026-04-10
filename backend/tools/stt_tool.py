from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from openai import AsyncOpenAI
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class STTError(Exception):
    """Raised when speech-to-text processing fails."""


def _get_openai_client() -> AsyncOpenAI:
    api_key = (
        os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("OPENAI_KEY", "").strip()
        or os.getenv("OPENAI_API_TOKEN", "").strip()
    )
    api_key = api_key.strip().strip('"').strip("'")
    if not api_key:
        raise STTError(
            "OpenAI API key is not configured. Set OPENAI_API_KEY in environment or .env."
        )
    return AsyncOpenAI(api_key=api_key)


def _resolve_audio_meta(file: UploadFile) -> tuple[str, str]:
    filename = (file.filename or "audio.wav").strip()
    content_type = (file.content_type or "application/octet-stream").strip()
    return filename, content_type


async def _read_audio_bytes(file: UploadFile) -> bytes:
    data = await file.read()
    if not data:
        raise STTError("Uploaded audio file is empty.")
    return data


async def transcribe(file: UploadFile) -> str:
    """Convert an uploaded audio file into text via Whisper API."""
    if file is None:
        raise STTError("Audio file is required.")

    model = os.getenv("STT_MODEL", "whisper-1").strip() or "whisper-1"
    language = os.getenv("STT_LANGUAGE", "").strip() or None

    filename, _ = _resolve_audio_meta(file)
    audio_bytes = await _read_audio_bytes(file)
    client = _get_openai_client()
    suffix = os.path.splitext(filename)[1] or ".wav"
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_bytes)

        kwargs: dict[str, Any] = {"model": model}
        if language:
            kwargs["language"] = language

        with open(temp_path, "rb") as audio_file:
            result = await client.audio.transcriptions.create(file=audio_file, **kwargs)
    except Exception as exc:  # noqa: BLE001
        raise STTError(f"Transcription failed: {exc}") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as exc:
                raise STTError(f"Failed to clean up temp audio file: {exc}") from exc

    text = (getattr(result, "text", "") or "").strip()
    if not text:
        raise STTError("Transcription completed but returned empty text.")

    return text
