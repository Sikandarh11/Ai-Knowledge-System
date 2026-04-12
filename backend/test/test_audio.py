import sounddevice as sd
import numpy as np
import wave
import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
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

# -----------------------------
# ✅ PATH FIX (IMPORTANT)
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ✅ Correct import
from backend.agents.scheduling_agent import run_agent as scheduling_run

# -----------------------------
# ENV + CLIENT
# -----------------------------
load_dotenv()
client = OpenAI()

# -----------------------------
# CONFIG
# -----------------------------
DURATION = 5
SAMPLE_RATE = 16000
FILENAME = "temp_audio.wav"


# -----------------------------
# 🎤 RECORD AUDIO
# -----------------------------
def record_audio():
    print("🎤 Speak now...")

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    print("✅ Recording done")

    with wave.open(FILENAME, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())


# -----------------------------
# 🧠 TRANSCRIBE
# -----------------------------
def transcribe_audio():
    print("🧠 Transcribing...")

    with open(FILENAME, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f,
        )

    return transcript.text


# -----------------------------
# ⚙️ STRUCTURE (OPTIONAL)
# -----------------------------
from datetime import datetime, timezone

def extract_structured_query(text):
    print("⚙️ Structuring query...")

    today = datetime.now(timezone.utc).date().isoformat()

    prompt = f"""
    You are a scheduling parser.

    Today is: {today} (UTC)

    Convert the user input into JSON.

    IMPORTANT RULES:
    - Resolve relative dates like "today", "tomorrow", "next Friday"
    - Use REAL current date (above)
    - Always return UTC ISO format
    - DO NOT guess random past dates
    - If unsure, leave fields null

    Text: "{text}"

    Return ONLY JSON:

    {{
    "intent": "create | check | suggest | other",
    "title": "",
    "date": "YYYY-MM-DD",
    "time": "HH:MM:SS",
    "duration_minutes": 30,
    "notes": ""
    }}
    """
    return prompt

# -----------------------------
# 🤖 RUN SCHEDULING AGENT
# -----------------------------

from backend.agents.scheduling_agent import SchedulingAgent, ParsedQuery, Intent

def run_scheduling(text):
    print("🤖 Running scheduling agent...")

    result = scheduling_run(text)

    print("\n📅 Calendar Response:")
    print(result.message)

    return result
# -----------------------------
# 🧹 CLEANUP
# -----------------------------
def cleanup():
    if os.path.exists(FILENAME):
        os.remove(FILENAME)
        print("🧹 Temp file deleted")


# -----------------------------
# 🚀 MAIN FLOW
# -----------------------------
if __name__ == "__main__":
    record_audio()

    text = transcribe_audio()
    print("\n📝 You said:", text)
    result = agent.run(text)
    print(result["message"])
    # # OPTIONAL (debug view only)
    # structured = extract_structured_query(text)
    # print("\n📦 Structured:", structured)

    # # ✅ IMPORTANT: pass ORIGINAL TEXT (not structured)
    # run_scheduling(text)
    cleanup()