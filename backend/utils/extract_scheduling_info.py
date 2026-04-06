"""
extract_scheduling_info.py

Extract structured scheduling information from natural language text.

Provides two parsing strategies:
    - RegexParser  : fast, zero-dependency, offline-safe
    - LLMParser    : higher accuracy via OpenAI API (gpt-4o-mini by default)

Both implement the same SchedulingParser protocol and return a SchedulingInfo
dataclass that serialises cleanly to a JSON-friendly dict.

Typical usage
-------------
    # Regex (no API key needed)
    from extract_scheduling_info import extract_scheduling_info
    info = extract_scheduling_info("schedule meeting tomorrow at 3pm for 1 hour")
    print(info)
    # {'date': '2024-06-02', 'time': '15:00', 'duration': 60, 'summary': 'meeting', ...}

    # LLM (requires OPENAI_API_KEY env var or explicit api_key=)
    from extract_scheduling_info import extract_scheduling_info
    info = extract_scheduling_info("catch-up next Monday evening", parser="llm")
    print(info)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, Protocol, runtime_checkable
from zoneinfo import ZoneInfo
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

@dataclass
class SchedulingInfo:
    """
    Structured scheduling data extracted from a natural-language string.

    Attributes:
        date:             ISO-8601 date string (``YYYY-MM-DD``) or ``None``.
        time:             24-hour time string (``HH:MM``) or ``None``.
        duration:         Meeting length in minutes (default 30).
        summary:          Short title / subject of the meeting.
        raw_text:         The original input string.
        parser_used:      Which parser produced this result (``"regex"`` / ``"llm"``).
        confidence:       ``"high"`` | ``"medium"`` | ``"low"`` — parsing confidence.
        warnings:         Any ambiguity or fallback notes.
    """
    date:        str | None  = None
    time:        str | None  = None
    duration:    int         = 30
    summary:     str         = "Meeting"
    raw_text:    str         = ""
    parser_used: str         = "regex"
    confidence:  str         = "high"
    warnings:    list[str]   = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain JSON-serialisable dictionary."""
        return asdict(self)

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Parser protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class SchedulingParser(Protocol):
    """Common interface for all parser implementations."""

    def parse(self, text: str) -> SchedulingInfo:
        """
        Parse *text* and return a :class:`SchedulingInfo`.

        Args:
            text: Raw natural-language input (e.g. ``"meeting tomorrow at 3pm"``).

        Returns:
            Populated :class:`SchedulingInfo` instance.
        """
        ...


# ---------------------------------------------------------------------------
# Shared resolution helpers
# ---------------------------------------------------------------------------

_WEEKDAY_MAP: dict[str, int] = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_TIME_OF_DAY: dict[str, str] = {
    "morning":   "09:00",
    "noon":      "12:00",
    "afternoon": "14:00",
    "evening":   "18:00",
    "night":     "20:00",
    "midnight":  "00:00",
}


def _today_utc() -> date:
    return datetime.now(ZoneInfo("Asia/Karachi")).date()


def _resolve_relative_date(token: str) -> str | None:
    """
    Convert a relative date token to an ISO ``YYYY-MM-DD`` string.

    Handles: today, tomorrow, yesterday, next <weekday>, this <weekday>,
    <weekday> (assumed to be the *next* occurrence).
    """
    token = token.strip().lower()
    today = _today_utc()

    if token in ("today", "now"):
        return today.isoformat()
    if token == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if token == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    # "next Monday" / "this Friday" / bare "Monday"
    is_next = token.startswith("next ")
    is_this = token.startswith("this ")
    bare = token.removeprefix("next ").removeprefix("this ").strip()

    if bare in _WEEKDAY_MAP:
        target_wd = _WEEKDAY_MAP[bare]
        days_ahead = (target_wd - today.weekday()) % 7
        if days_ahead == 0 and is_next:
            days_ahead = 7
        elif days_ahead == 0 and not is_this:
            days_ahead = 7   # bare weekday = next occurrence
        return (today + timedelta(days=days_ahead)).isoformat()

    return None


def _resolve_time_of_day(phrase: str) -> str | None:
    """Map a fuzzy time phrase (morning / evening / noon …) to ``HH:MM``."""
    return _TIME_OF_DAY.get(phrase.strip().lower())


def _parse_clock(raw: str) -> str | None:
    """
    Parse a clock expression to ``HH:MM`` (24-hour).

    Accepts: ``9am``, ``9:30 PM``, ``14:00``, ``9:00:00``.
    Returns ``None`` when parsing fails.
    """
    raw = raw.strip().lower().replace(" ", "")
    meridiem: str | None = None

    if raw.endswith("am"):
        meridiem = "am"
        raw = raw[:-2]
    elif raw.endswith("pm"):
        meridiem = "pm"
        raw = raw[:-2]

    parts = raw.split(":")
    try:
        hour   = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return None

    if meridiem == "am" and hour == 12:
        hour = 0
    elif meridiem == "pm" and hour != 12:
        hour += 12

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    return f"{hour:02d}:{minute:02d}"


def _parse_duration(text: str) -> int | None:
    """
    Extract duration in minutes from *text*.

    Handles: ``1 hour``, ``2 hours``, ``90 minutes``, ``1h``, ``30 min``,
    ``1 hour 30 minutes``, ``1.5 hours``.
    Returns ``None`` when no duration is found.
    """
    total = 0
    found = False

    # Float hours: "1.5 hours"
    for m in re.finditer(r"(\d+(?:\.\d+))\s*(?:hours?|hrs?|h)\b", text, re.I):
        total += int(float(m.group(1)) * 60)
        found = True

    # Integer hours: "2 hours"
    for m in re.finditer(r"(\d+)\s*(?:hours?|hrs?|h)\b", text, re.I):
        total += int(m.group(1)) * 60
        found = True

    # Minutes: "30 minutes"
    for m in re.finditer(r"(\d+)\s*(?:minutes?|mins?|m)\b", text, re.I):
        total += int(m.group(1))
        found = True

    return total if found else None


# ---------------------------------------------------------------------------
# 1. Regex parser
# ---------------------------------------------------------------------------

class RegexParser:
    """
    Rule-based scheduling extractor using regular expressions.

    Fast, dependency-free, and works offline.  Handles the most common
    English scheduling patterns reliably; may miss exotic phrasings.

    Usage::

        parser = RegexParser()
        info = parser.parse("meeting next Monday at 9am for 2 hours")
    """

    # --- compiled patterns (class-level, compiled once) -------------------

    # Relative date tokens (order matters — longer phrases first)
    _REL_DATE = re.compile(
        r"\b(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"|this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"|tomorrow|today|yesterday"
        r"|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        re.I,
    )
    # ISO date: 2024-06-01
    _ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
    # Slash/dash short date: 6/1/2024, 1-6-24
    _SHORT_DATE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")

    # Clock time: 3pm, 9:30 AM, 14:00, 9:00:00
    _CLOCK = re.compile(
        r"\b(\d{1,2}(?::\d{2}(?::\d{2})?)?)\s*(am|pm)\b"
        r"|\b(\d{2}:\d{2}(?::\d{2})?)\b",
        re.I,
    )
    # Time-of-day phrases
    _TOD = re.compile(
        r"\b(morning|noon|afternoon|evening|night|midnight)\b", re.I
    )
    # "at <time>" anchor
    _AT_TIME = re.compile(
        r"\bat\s+(\d{1,2}(?::\d{2})?(?:\s*(?:am|pm))?)\b", re.I
    )

    # Summary hints
    _SUMMARY = re.compile(
        r"\b(?:called|titled|named|for|about|re:?)\s+[\"']?([a-z][^\"']{2,40}?)[\"']?"
        r"(?=\s+(?:on|at|tomorrow|next|this|today|\d)|$)",
        re.I,
    )
    _MEETING_TYPES = re.compile(
        r"\b(standup|stand-up|sync|call|interview|review|retrospective|retro"
        r"|one-on-one|1:1|kickoff|check-in|demo|workshop|training|webinar"
        r"|meeting|appointment|catch-up|catchup)\b",
        re.I,
    )

    # ---------------------------------------------------------------------------

    def parse(self, text: str) -> SchedulingInfo:
        """
        Extract scheduling fields from *text* using regex rules.

        Args:
            text: Raw natural-language scheduling request.

        Returns:
            :class:`SchedulingInfo` with extracted fields (``None`` where not found).
        """
        info = SchedulingInfo(raw_text=text, parser_used="regex")
        lowered = text.lower()
        warnings: list[str] = []

        # --- Date -----------------------------------------------------------
        # 1. ISO date
        iso_m = self._ISO_DATE.search(text)
        if iso_m:
            info.date = iso_m.group(1)
        else:
            # 2. Relative date
            rel_m = self._REL_DATE.search(lowered)
            if rel_m:
                resolved = _resolve_relative_date(rel_m.group(1))
                if resolved:
                    info.date = resolved
                else:
                    warnings.append(f"Could not resolve relative date: '{rel_m.group(1)}'")
            else:
                # 3. Short date (M/D/YYYY)
                short_m = self._SHORT_DATE.search(text)
                if short_m:
                    parts = re.split(r"[/-]", short_m.group(1))
                    try:
                        m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
                        if y < 100:
                            y += 2000
                        info.date = date(y, m, d).isoformat()
                    except (ValueError, IndexError):
                        warnings.append(f"Could not parse date: '{short_m.group(1)}'")
                else:
                    warnings.append("No date found in text.")
                    info.confidence = "low"

        # --- Time -----------------------------------------------------------
        # 1. "at <time>" anchor (highest precision)
        at_m = self._AT_TIME.search(text)
        if at_m:
            resolved = _parse_clock(at_m.group(1))
            if resolved:
                info.time = resolved

        # 2. Standalone clock if no "at" match
        if not info.time:
            clock_m = self._CLOCK.search(text)
            if clock_m:
                raw_clock = (clock_m.group(1) or clock_m.group(3) or "")
                suffix    = clock_m.group(2) or ""
                resolved  = _parse_clock(raw_clock + suffix)
                if resolved:
                    info.time = resolved

        # 3. Time-of-day phrase fallback
        if not info.time:
            tod_m = self._TOD.search(lowered)
            if tod_m:
                info.time = _resolve_time_of_day(tod_m.group(1))
                if info.time:
                    warnings.append(
                        f"Fuzzy time '{tod_m.group(1)}' resolved to {info.time}."
                    )
                    info.confidence = "medium"
            else:
                warnings.append("No time found in text.")
                if info.confidence != "low":
                    info.confidence = "medium"

        # --- Duration -------------------------------------------------------
        duration = _parse_duration(text)
        if duration:
            info.duration = duration
        else:
            warnings.append("No duration found; defaulting to 30 minutes.")

        # --- Summary --------------------------------------------------------
        summary_m = self._SUMMARY.search(text)
        if summary_m:
            info.summary = summary_m.group(1).strip().title()
        else:
            meeting_m = self._MEETING_TYPES.search(text)
            if meeting_m:
                info.summary = meeting_m.group(1).title()

        info.warnings = warnings
        logger.debug("RegexParser result: %s", info.to_dict())
        return info


# ---------------------------------------------------------------------------
# 2. LLM parser (Anthropic API)
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """\
You are a scheduling assistant that extracts structured information from natural language.

Today's date (UTC): {today}

Extract the following fields from the user's message and return ONLY a valid JSON object
with exactly these keys (no markdown, no extra text, no code fences):

{{
  "date":       "<YYYY-MM-DD or null>",
  "time":       "<HH:MM in 24-hour UTC or null>",
  "duration":   <integer minutes, default 30>,
  "summary":    "<short meeting title>",
  "confidence": "<high|medium|low>",
  "warnings":   ["<any ambiguity or assumption made>"]
}}

Rules:
- Resolve relative expressions ("tomorrow", "next Monday", "evening") using today's date.
- Time-of-day mappings: morning=09:00, noon=12:00, afternoon=14:00, evening=18:00, night=20:00, midnight=00:00.
- Convert any hour-based duration to minutes (e.g. "1 hour" → 60).
- If a field cannot be determined set it to null (date/time) or use the default (duration=30).
- Return ONLY the raw JSON object. No explanation, no markdown, no extra keys.
"""


class LLMParser:
    """
    LLM-based scheduling extractor using the OpenAI Chat Completions API.

    Falls back gracefully to :class:`RegexParser` when:
    - The ``openai`` package is not installed (``pip install openai``).
    - ``OPENAI_API_KEY`` environment variable is not set and no *api_key* is given.
    - The API call fails for any reason.

    Args:
        api_key: OpenAI API key.  Defaults to ``OPENAI_API_KEY`` env var.
        model:   Model name (default ``"gpt-4o-mini"`` — fast and cheap).
                 Use ``"gpt-4o"`` for maximum accuracy.
        timeout: HTTP timeout in seconds (default 15).

    Usage::

        parser = LLMParser()
        info = parser.parse("catch-up with Sarah next Wednesday evening for 45 minutes")

        # Explicit key / model
        parser = LLMParser(api_key="sk-...", model="gpt-4o")
        info = parser.parse("board meeting next Friday at noon")
    """

    def __init__(
        self,
        api_key: str | None = None,
        model:   str        = "gpt-4o-mini",
        timeout: int        = 15,
    ) -> None:
        self._model    = model
        self._timeout  = timeout
        self._api_key  = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._fallback = RegexParser()
        self._client   = self._build_client()

    def _build_client(self) -> Any | None:
        """Return an OpenAI client, or None if unavailable."""
        if not self._api_key:
            logger.warning(
                "LLMParser: OPENAI_API_KEY not set — will fall back to RegexParser."
            )
            return None
        try:
            import openai  # type: ignore
            return openai.OpenAI(api_key=self._api_key, timeout=self._timeout)
        except ImportError:
            logger.warning(
                "LLMParser: 'openai' package not installed — "
                "run `pip install openai`. Falling back to RegexParser."
            )
            return None

    def parse(self, text: str) -> SchedulingInfo:
        """
        Extract scheduling info using OpenAI, with regex fallback on any failure.

        Uses ``response_format={"type": "json_object"}`` so the model is
        constrained to return valid JSON without markdown fences.

        Args:
            text: Raw natural-language scheduling request.

        Returns:
            :class:`SchedulingInfo` populated from the model response.
        """
        if self._client is None:
            logger.info("LLMParser: using regex fallback (no client).")
            result = self._fallback.parse(text)
            result.parser_used = "regex-fallback"
            return result

        today_str = _today_utc().isoformat()
        system_content = _LLM_SYSTEM_PROMPT.format(today=today_str)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},   # guaranteed JSON output
                temperature=0,                              # deterministic extraction
                max_tokens=512,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user",   "content": text},
                ],
            )
            raw_json: str = response.choices[0].message.content.strip()
            # Defensive strip of any accidental fences (older model versions)
            raw_json = re.sub(r"^```(?:json)?|```$", "", raw_json, flags=re.M).strip()
            payload: dict[str, Any] = json.loads(raw_json)

        except json.JSONDecodeError as exc:
            logger.warning("LLMParser: JSON decode error — %s. Using regex fallback.", exc)
            result = self._fallback.parse(text)
            result.parser_used = "regex-fallback"
            result.warnings.append(f"LLM returned invalid JSON: {exc}")
            return result

        except Exception as exc:  # noqa: BLE001
            logger.warning("LLMParser: API error — %s. Using regex fallback.", exc)
            result = self._fallback.parse(text)
            result.parser_used = "regex-fallback"
            result.warnings.append(f"LLM call failed: {exc}")
            return result

        return SchedulingInfo(
            date        = payload.get("date"),
            time        = payload.get("time"),
            duration    = int(payload.get("duration") or 30),
            summary     = payload.get("summary") or "Meeting",
            raw_text    = text,
            parser_used = f"llm:{self._model}",
            confidence  = payload.get("confidence", "high"),
            warnings    = payload.get("warnings") or [],
        )


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def extract_scheduling_info(
    text:   str,
    parser: Literal["regex", "llm"] = "regex",
    **parser_kwargs: Any,
) -> dict[str, Any]:
    """
    Extract structured scheduling information from a natural-language string.

    Args:
        text:           Free-text scheduling request, e.g.
                        ``"schedule a meeting tomorrow at 3pm for 1 hour"``.
        parser:         Which backend to use — ``"regex"`` (default, offline-safe)
                        or ``"llm"`` (Anthropic API, higher accuracy).
        **parser_kwargs: Forwarded to the parser constructor (e.g. ``api_key``,
                        ``model``, ``timeout`` for :class:`LLMParser`).

    Returns:
        A JSON-serialisable dict::

            {
                "date":        "YYYY-MM-DD or null",
                "time":        "HH:MM or null",
                "duration":    60,
                "summary":     "Meeting",
                "raw_text":    "...",
                "parser_used": "regex",
                "confidence":  "high",
                "warnings":    []
            }

    Examples::

        extract_scheduling_info("schedule meeting tomorrow at 3pm for 1 hour")
        # {'date': '2024-06-02', 'time': '15:00', 'duration': 60, ...}

        extract_scheduling_info("standup next Monday morning", parser="regex")
        # {'date': '2024-06-03', 'time': '09:00', 'duration': 30, ...}

        extract_scheduling_info("catch-up next Friday evening", parser="llm")
        # {'date': '2024-06-07', 'time': '18:00', 'duration': 30, ...}
    """
    if parser == "llm":
        impl: SchedulingParser = LLMParser(**parser_kwargs)
    else:
        impl = RegexParser()

    info = impl.parse(text)
    return info.to_dict()