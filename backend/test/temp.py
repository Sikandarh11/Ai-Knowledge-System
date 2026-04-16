import sounddevice as sd
import numpy as np
import wave
import os
from openai import OpenAI

import argparse
import logging
import os
import sys
from pathlib import Path
from pprint import pformat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.agents.scheduling_agent import SchedulingAgent
agent = SchedulingAgent()

# CONFIG
DURATION = 5
SAMPLE_RATE = 16000
FILENAME = "temp_audio.wav"
OPENAI_API_KEY="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"

client = OpenAI(api_key=OPENAI_API_KEY)


def record_audio():
    print("🎤 Speak now...")

    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
    sd.wait()

    print("✅ Recording done")

    with wave.open(FILENAME, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())


def transcribe_audio():
    print("🧠 Converting speech to text...")

    with open(FILENAME, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f
        )

    print("\n📝 You said:", transcript.text)
    return transcript.text


def cleanup():
    if os.path.exists(FILENAME):
        os.remove(FILENAME)


if __name__ == "__main__":
    record_audio()
    text = transcribe_audio()
    result = agent.run("Book a meeting tomorrow at 10 am for 1 hour")
    print(result["message"])
    cleanup()