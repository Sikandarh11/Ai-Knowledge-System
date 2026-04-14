from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

from anyio import to_thread

from backend.tools.stt_tool import transcribe
from backend.services.intent_service import extract_intent
from backend.services.router_service import route_intent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIO_SAVE_DIR = PROJECT_ROOT / "backend" / "test" / "saved_audio"


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
