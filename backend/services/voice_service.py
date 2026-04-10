from __future__ import annotations

from typing import Any

from backend.tools.stt_tool import transcribe
from backend.services.intent_service import extract_intent
from backend.services.router_service import route_intent


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
