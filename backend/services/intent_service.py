from __future__ import annotations

import json
import os
from pathlib import Path

from openai import AsyncOpenAI


class IntentExtractionError(Exception):
    """Raised when intent extraction fails or returns invalid JSON."""


def _load_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "intent_prompt.txt"
    if not prompt_path.exists():
        raise IntentExtractionError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _build_prompt(template: str, text: str) -> str:
    return template.replace("{{input}}", text)


async def _call_llm(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise IntentExtractionError("OPENAI_API_KEY is not configured.")

    model = os.getenv("INTENT_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    client = AsyncOpenAI(api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise IntentExtractionError(f"LLM request failed: {exc}") from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise IntentExtractionError("LLM returned an empty response.")
    return content


async def extract_intent(text: str) -> dict:
    prompt_template = _load_prompt()
    prompt = _build_prompt(prompt_template, text)
    response_text = await _call_llm(prompt)

    try:
        intent_json = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise IntentExtractionError(f"Invalid JSON response from LLM: {response_text}") from exc

    if not isinstance(intent_json, dict):
        raise IntentExtractionError("Invalid response type from LLM. Expected JSON object.")

    if "intent" not in intent_json or "action" not in intent_json or "params" not in intent_json:
        raise IntentExtractionError("Invalid response schema from LLM. Required keys: intent, action, params.")

    if not isinstance(intent_json.get("params"), dict):
        raise IntentExtractionError("Invalid response schema from LLM. 'params' must be a JSON object.")

    return intent_json

    return {
        "intent": "unknown",
        "action": "none",
        "params": {},
    }
