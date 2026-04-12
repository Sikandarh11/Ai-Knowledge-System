import asyncio
import os
from pathlib import Path
import sys

import sounddevice as sd
from scipy.io.wavfile import write

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.tools.stt_tool import transcribe

SAMPLE_RATE = 44100
DURATION = 5
OUTPUT_FILE = Path("recorded_audio.wav")


class LocalUploadFile:
    def __init__(self, path: Path, content_type: str = "audio/wav") -> None:
        self.path = path
        self.filename = path.name
        self.content_type = content_type

    async def read(self) -> bytes:
        return self.path.read_bytes()


def record_audio() -> Path:
    print(f"Recording for {DURATION} seconds... Speak now")

    audio_data = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )

    sd.wait()  # wait until recording is finished

    write(OUTPUT_FILE, SAMPLE_RATE, audio_data)

    print(f"Audio saved as: {OUTPUT_FILE}")
    print(f"File path: {os.path.abspath(OUTPUT_FILE)}")
    return OUTPUT_FILE


async def transcribe_saved_audio(audio_path: Path) -> str:
    upload_file = LocalUploadFile(audio_path)
    return await transcribe(upload_file)


async def main() -> None:
    audio_path = record_audio()
    text = await transcribe_saved_audio(audio_path)
    print("Transcribed text:")
    print(text)


if __name__ == "__main__":
    asyncio.run(main())