"""
scheduling_agent.py

Agent-based AI scheduling assistant.

Flow:
    User query
        → parse_intent()          – extract date, time, duration, intent
        → calendar_tool.get_events()  – fetch existing events
        → scheduler_service.has_conflict()
        → branch:
              check   → report availability
              create  → conflict-free → create_event()
                      → conflict     → suggest_alternative() → report
              suggest → find_free_slots() / suggest_alternative()
        → build_response()        – natural-language reply

All times are UTC ISO-8601 throughout.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from zoneinfo import ZoneInfo
from backend.core.config import settings
from backend.tools.calendar_tool import CalendarTool
from backend.services.scheduler_service import (
    has_conflict,
    find_free_slots,
    suggest_alternative,
)
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

_PARSER_MODEL = settings.SCHEDULER_PARSER_MODEL


def _get_scheduler_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.SCHEDULER_TIMEZONE)
    except ZoneInfoNotFoundError:
        logger.warning(
            "Invalid SCHEDULER_TIMEZONE=%r. Falling back to UTC.",
            settings.SCHEDULER_TIMEZONE,
        )
        return ZoneInfo("UTC")


_SCHEDULER_TZ = _get_scheduler_timezone()

_PARSER_SYSTEM_PROMPT = """\
You extract structured scheduling data from a user query.

Today's date (UTC): {today}

Return ONLY a valid JSON object with exactly these keys:
{{
    "intent": "check|create|suggest|unknown",
    "date": "YYYY-MM-DD or null",
    "time": "HH:MM:SS or null",
    "duration_minutes": <integer, default 30>,
    "summary": "short meeting title"
}}

Rules:
- Resolve relative dates like today/tomorrow/next Monday using today's date.
- Convert 12-hour time to 24-hour time and include seconds.
- If no duration is given use 30.
- Keep summary short and useful, default to "Meeting".
- If user asks to check availability, intent=check.
- If user asks to book/create/schedule, intent=create.
- If user asks for options/recommendations/available slots, intent=suggest.
- If unclear, intent=unknown.
- Return raw JSON only (no markdown, no extra text).
"""


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

class Intent(str, Enum):
    CHECK   = "check"    # user wants to know if a time is free
    CREATE  = "create"   # user wants to book a meeting
    SUGGEST = "suggest"  # user wants open-slot recommendations
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    """Structured representation of what the user is asking for."""
    intent: Intent          = Intent.UNKNOWN
    date: str | None        = None   # ISO date, e.g. "2024-06-01"
    time: str | None        = None   # ISO time, e.g. "09:00:00"
    duration_minutes: int   = settings.SCHEDULER_DEFAULT_DURATION_MINUTES
    summary: str            = "Meeting"
    raw_query: str          = ""
    errors: list[str]       = field(default_factory=list)

    @property
    def start_iso(self) -> str | None:
        """Combine date + time in scheduler timezone and return UTC ISO string."""
        if self.date and self.time:
            local_dt = datetime.fromisoformat(f"{self.date}T{self.time}").replace(
                tzinfo=_SCHEDULER_TZ
            )
            return local_dt.astimezone(timezone.utc).isoformat()
        return None

    @property
    def end_iso(self) -> str | None:
        """Derive the end time from start + duration."""
        if self.start_iso:
            start = datetime.fromisoformat(self.start_iso)
            end = start + timedelta(minutes=self.duration_minutes)
            return end.isoformat()
        return None


@dataclass
class AgentResponse:
    """Final structured output of the agent."""
    success: bool
    message: str                           # natural-language reply
    intent: Intent             = Intent.UNKNOWN
    conflict_detected: bool    = False
    created_event: dict | None = None
    alternatives: list[dict]   = field(default_factory=list)
    free_slots: list[dict]     = field(default_factory=list)
    error: str | None          = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success":          self.success,
            "message":          self.message,
            "intent":           self.intent.value,
            "conflict_detected": self.conflict_detected,
            "created_event":    self.created_event,
            "alternatives":     self.alternatives,
            "free_slots":       self.free_slots,
            "error":            self.error,
        }


# ---------------------------------------------------------------------------
# Intent parser
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: dict[Intent, list[str]] = {
    Intent.CREATE:  [
        r"\b(book|schedule|create|add|set up|arrange|plan)\b",
    ],
    Intent.SUGGEST: [
        r"\b(suggest|recommend|find|show|list|available|free slots?|open slots?|any time)\b",
    ],
    Intent.CHECK:   [
        r"\b(check|am i free|is .* free|available|busy|conflict|do i have)\b",
    ],
}

_DATE_PATTERNS: list[str] = [
    r"\b(\d{4}-\d{2}-\d{2})\b",                               # 2024-06-01
    r"\b(today)\b",
    r"\b(tomorrow)\b",
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",                  # 6/1/2024  or  1-6-24
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
]

_TIME_PATTERNS: list[str] = [
    r"\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]m)?)\b",          # 9:00, 09:30 AM
    r"\b(\d{1,2}\s*[ap]m)\b",                                 # 9am, 10 PM
]

_DURATION_PATTERNS: list[str] = [
    r"\b(\d+)\s*hour(?:s)?\b",                                # 2 hours
    r"\b(\d+)\s*h\b",                                         # 2h
    r"\b(\d+)\s*min(?:ute)?s?\b",                             # 30 minutes / 30 min
]

_WEEKDAY_MAP: dict[str, int] = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _resolve_date(raw: str) -> str | None:
    """
    Convert a raw date token into a ``YYYY-MM-DD`` string (UTC date).

    Handles ISO dates, 'today', 'tomorrow', weekday names, and slash/dash
    formats (M/D/YYYY).  Returns ``None`` when parsing fails.
    """
    today = datetime.now(tz=timezone.utc).date()
    raw = raw.strip().lower()

    if raw == "today":
        return today.isoformat()
    if raw == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if raw in _WEEKDAY_MAP:
        target_wd = _WEEKDAY_MAP[raw]
        days_ahead = (target_wd - today.weekday()) % 7 or 7
        return (today + timedelta(days=days_ahead)).isoformat()

    # ISO format
    iso_match = re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw)
    if iso_match:
        return raw

    # M/D/YYYY or D-M-YY
    for sep in ("/", "-"):
        parts = raw.split(sep)
        if len(parts) == 3:
            try:
                m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
                if y < 100:
                    y += 2000
                return datetime(y, m, d).date().isoformat()
            except ValueError:
                pass

    return None


def _resolve_time(raw: str) -> str | None:
    """
    Normalise a raw time token to ``HH:MM:00`` (24-hour, UTC assumed).

    Handles ``HH:MM``, ``HH:MM:SS``, ``H am/pm``, ``HH:MM am/pm``.
    Returns ``None`` on failure.
    """
    raw = raw.strip().lower().replace(" ", "")
    meridiem = None
    if raw.endswith("am"):
        meridiem = "am"
        raw = raw[:-2]
    elif raw.endswith("pm"):
        meridiem = "pm"
        raw = raw[:-2]

    parts = raw.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
    except (ValueError, IndexError):
        return None

    if meridiem == "am" and hour == 12:
        hour = 0
    elif meridiem == "pm" and hour != 12:
        hour += 12

    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return None

    return f"{hour:02d}:{minute:02d}:{second:02d}"


def parse_intent(query: str) -> ParsedQuery:
    """
    Extract intent, date, time, duration, and summary from a free-text query.

    Uses regex heuristics.  Designed to be replaced by an LLM extraction
    layer without changing the ``ParsedQuery`` contract.

    Args:
        query: Raw natural-language user input.

    Returns:
        A :class:`ParsedQuery` instance (``errors`` list non-empty on issues).
    """
    result = ParsedQuery(raw_query=query)

    if _parse_intent_with_llm(query, result):
        _validate_parsed_query(result)
        return result

    # Fallback: regex extraction if LLM is unavailable/fails.
    _parse_intent_with_regex(query, result)
    _validate_parsed_query(result)
    return result


def _parse_intent_with_llm(query: str, result: ParsedQuery) -> bool:
    """Populate ``result`` via OpenAI extraction. Returns True on success."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("parse_intent: OPENAI_API_KEY not set; using regex fallback.")
        return False

    try:
        import openai  # type: ignore
    except ImportError:
        logger.warning("parse_intent: openai package not installed; using regex fallback.")
        return False

    today = datetime.now(tz=_SCHEDULER_TZ).date().isoformat()
    system_prompt = _PARSER_SYSTEM_PROMPT.format(today=today)

    try:
        client = openai.OpenAI(api_key=api_key, timeout=15)
        response = client.chat.completions.create(
            model=_PARSER_MODEL,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=400,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        )
        content = (response.choices[0].message.content or "").strip()
        payload: dict[str, Any] = json.loads(content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("parse_intent: OpenAI extraction failed (%s); using regex fallback.", exc)
        return False

    intent_raw = str(payload.get("intent", "unknown")).strip().lower()
    result.intent = {
        "check": Intent.CHECK,
        "create": Intent.CREATE,
        "suggest": Intent.SUGGEST,
    }.get(intent_raw, Intent.UNKNOWN)

    date_raw = payload.get("date")
    if isinstance(date_raw, str) and date_raw.strip():
        result.date = date_raw.strip()

    time_raw = payload.get("time")
    if isinstance(time_raw, str) and time_raw.strip():
        result.time = time_raw.strip()

    duration_raw = payload.get("duration_minutes")
    try:
        parsed_duration = int(duration_raw)
        if parsed_duration > 0:
            result.duration_minutes = parsed_duration
    except (TypeError, ValueError):
        pass

    summary_raw = payload.get("summary")
    if isinstance(summary_raw, str) and summary_raw.strip():
        result.summary = summary_raw.strip()

    return True


def _parse_intent_with_regex(query: str, result: ParsedQuery) -> None:
    """Legacy regex parser used only as fallback."""
    lowered = query.lower()

    # --- Intent -------------------------------------------------------------
    for intent, patterns in _INTENT_PATTERNS.items():
        if any(re.search(p, lowered) for p in patterns):
            result.intent = intent
            break

    # --- Date ---------------------------------------------------------------
    for pattern in _DATE_PATTERNS:
        m = re.search(pattern, lowered)
        if m:
            resolved = _resolve_date(m.group(1))
            if resolved:
                result.date = resolved
                break

    # --- Time ---------------------------------------------------------------
    for pattern in _TIME_PATTERNS:
        m = re.search(pattern, lowered, re.IGNORECASE)
        if m:
            resolved = _resolve_time(m.group(1))
            if resolved:
                result.time = resolved
                break

    # --- Duration -----------------------------------------------------------
    hours_m = re.search(_DURATION_PATTERNS[0], lowered) or \
              re.search(_DURATION_PATTERNS[1], lowered)
    mins_m  = re.search(_DURATION_PATTERNS[2], lowered)

    duration = 0
    if hours_m:
        duration += int(hours_m.group(1)) * 60
    if mins_m:
        duration += int(mins_m.group(1))
    if duration:
        result.duration_minutes = duration

    # --- Summary (title extraction) -----------------------------------------
    # Only extract an explicit title when the user names it with a keyword.
    # Avoid grabbing duration/time fragments like "30 minutes" or "1 hour".
    title_match = re.search(
        r'(?:called|titled|named|about|re:?)\s+"?([^"]+?)"?\s*(?:on|at|tomorrow|next|today|\d|$)',
        query, re.IGNORECASE,
    )
    if title_match:
        candidate = title_match.group(1).strip()
        # Reject if it looks like a duration or time token
        if not re.fullmatch(r'[\d\s]*(hour|hr|minute|min|am|pm|h|m)s?', candidate, re.I):
            result.summary = candidate.title()
    else:
        # Fall back to a known meeting-type word in the query
        meeting_m = re.search(
            r'\b(standup|stand-up|sync|call|interview|review|retrospective|retro'
            r'|one-on-one|1:1|kickoff|check-in|demo|workshop|training|webinar'
            r'|meeting|appointment|catch-up|catchup)\b',
            query, re.IGNORECASE,
        )
        if meeting_m:
            result.summary = meeting_m.group(1).title()


def _validate_parsed_query(result: ParsedQuery) -> None:
    """Apply common validation messages to parsed output."""
    # --- Validation ---------------------------------------------------------
    if result.intent == Intent.UNKNOWN:
        result.errors.append(
            "Could not determine intent. Try using words like 'book', 'check', or 'suggest'."
        )
    if not result.date:
        result.errors.append("No date found. Please include a date (e.g. 'tomorrow', '2024-06-01').")
    if result.intent in (Intent.CHECK, Intent.CREATE) and not result.time:
        result.errors.append("No time found. Please include a time (e.g. '10am', '14:30').")


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------

def _fmt_slot(slot: dict[str, Any]) -> str:
    """Format a slot dict into a human-readable string."""
    try:
        start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00")).astimezone(_SCHEDULER_TZ)
        end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00")).astimezone(_SCHEDULER_TZ)
        return (
            f"  • {start.strftime('%A %d %b %Y, %H:%M')} – "
            f"{end.strftime('%H:%M')} {settings.SCHEDULER_TIMEZONE}"
        )
    except (KeyError, ValueError):
        return f"  • {slot.get('start', '?')} – {slot.get('end', '?')}"


def _fmt_event(event: dict[str, Any]) -> str:
    """Format a created-event dict into a human-readable confirmation line."""
    try:
        start = datetime.fromisoformat(event["start"].replace("Z", "+00:00")).astimezone(_SCHEDULER_TZ)
        end = datetime.fromisoformat(event["end"].replace("Z", "+00:00")).astimezone(_SCHEDULER_TZ)
        return (
            f"\"{event.get('summary', 'Meeting')}\" on "
            f"{start.strftime('%A %d %b %Y')} from "
            f"{start.strftime('%H:%M')} to {end.strftime('%H:%M')} {settings.SCHEDULER_TIMEZONE}"
        )
    except (KeyError, ValueError):
        return str(event)


def build_response(
    parsed: ParsedQuery,
    conflict: bool,
    created_event: dict | None,
    alternatives: list[dict],
    free_slots: list[dict],
    error: str | None = None,
) -> AgentResponse:
    """
    Construct a natural-language :class:`AgentResponse` from agent outputs.

    Args:
        parsed:        The parsed user query.
        conflict:      Whether a scheduling conflict was detected.
        created_event: Event dict if creation succeeded, else ``None``.
        alternatives:  List of alternative slot dicts.
        free_slots:    List of free-slot dicts.
        error:         Error string if a step failed, else ``None``.

    Returns:
        A fully populated :class:`AgentResponse`.
    """
    if error:
        return AgentResponse(
            success=False,
            message=f"Sorry, I ran into a problem: {error}",
            intent=parsed.intent,
            error=error,
        )

    # --- CREATE path --------------------------------------------------------
    if parsed.intent == Intent.CREATE:
        if created_event:
            return AgentResponse(
                success=True,
                message=f"✅ Done! I've booked {_fmt_event(created_event)}.",
                intent=parsed.intent,
                conflict_detected=False,
                created_event=created_event,
            )
        if conflict:
            lines = ["⚠️ That time has a conflict. Here are some alternatives:\n"]
            lines += [_fmt_slot(s) for s in alternatives]
            if not alternatives:
                lines = ["⚠️ That time has a conflict and I couldn't find alternatives in the next 7 days."]
            return AgentResponse(
                success=True,
                message="\n".join(lines),
                intent=parsed.intent,
                conflict_detected=True,
                alternatives=alternatives,
            )

    # --- CHECK path ---------------------------------------------------------
    if parsed.intent == Intent.CHECK:
        if conflict:
            lines = ["🔴 You're busy at that time. Here are some alternatives:\n"]
            lines += [_fmt_slot(s) for s in alternatives]
        else:
            lines = [
                f"🟢 You're free on {parsed.date} at {parsed.time} {settings.SCHEDULER_TIMEZONE}. No conflicts found."
            ]
        return AgentResponse(
            success=True,
            message="\n".join(lines),
            intent=parsed.intent,
            conflict_detected=conflict,
            alternatives=alternatives,
        )

    # --- SUGGEST path -------------------------------------------------------
    if parsed.intent == Intent.SUGGEST:
        if free_slots:
            lines = [f"📅 Here are available slots on {parsed.date}:\n"]
            lines += [_fmt_slot(s) for s in free_slots[:5]]
        else:
            lines = [
                f"😔 No free slots found on {parsed.date} during working hours "
                f"({settings.SCHEDULER_WORK_START_HOUR:02d}:00-{settings.SCHEDULER_WORK_END_HOUR:02d}:00 {settings.SCHEDULER_TIMEZONE})."
            ]
        return AgentResponse(
            success=True,
            message="\n".join(lines),
            intent=parsed.intent,
            free_slots=free_slots,
        )

    # --- Fallback -----------------------------------------------------------
    return AgentResponse(
        success=False,
        message="I wasn't sure what you meant. Try asking to 'book', 'check', or 'suggest' a meeting.",
        intent=parsed.intent,
        error="unresolved intent",
    )


# ---------------------------------------------------------------------------
# Core agent
# ---------------------------------------------------------------------------

class SchedulingAgent:
    """
    Orchestrates intent parsing, calendar retrieval, conflict detection,
    event creation, and alternative suggestion into a single entry-point.

    Args:
        calendar_tool: An initialised :class:`CalendarTool` instance.
                       A default instance is created when ``None``.

    Example::

        agent = SchedulingAgent()
        result = agent.run("Book a meeting tomorrow at 10am for 1 hour")
        print(result["message"])
    """

    def __init__(self, calendar_tool: CalendarTool | None = None) -> None:
        self._calendar: CalendarTool | None = calendar_tool
        self._calendar_init_error: str | None = None

    def _get_calendar(self) -> CalendarTool | None:
        """Initialize CalendarTool on demand and capture startup failures."""
        if self._calendar is not None:
            return self._calendar
        if self._calendar_init_error is not None:
            return None

        try:
            self._calendar = CalendarTool()
            return self._calendar
        except Exception as exc:
            self._calendar_init_error = str(exc)
            logger.exception("SchedulingAgent calendar initialization failed")
            return None

    @staticmethod
    def _local_day_start_utc_iso(date_iso: str) -> str:
        local_start = datetime.fromisoformat(f"{date_iso}T00:00:00").replace(tzinfo=_SCHEDULER_TZ)
        return local_start.astimezone(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(self, query: str) -> dict[str, Any]:
        """
        Process a natural-language scheduling query end-to-end.

        Args:
            query: Free-text user input such as
                   ``"Am I free on Friday at 3pm?"`` or
                   ``"Book a standup tomorrow at 9am for 30 minutes"``.

        Returns:
            A JSON-serialisable dict (see :class:`AgentResponse`) with keys:
            ``success``, ``message``, ``intent``, ``conflict_detected``,
            ``created_event``, ``alternatives``, ``free_slots``, ``error``.
        """
        logger.info("SchedulingAgent.run | query=%r", query)

        # 1. Parse intent
        parsed = parse_intent(query)
        logger.debug("Parsed: %s", parsed)

        if parsed.errors and parsed.intent == Intent.UNKNOWN:
            return AgentResponse(
                success=False,
                message=(
                    "I had trouble understanding your request:\n"
                    + "\n".join(f"  • {e}" for e in parsed.errors)
                ),
                intent=parsed.intent,
                error="; ".join(parsed.errors),
            ).to_dict()

        calendar = self._get_calendar()
        if calendar is None:
            error_message = self._calendar_init_error or "Calendar service is unavailable."
            return AgentResponse(
                success=False,
                message=f"Sorry, I couldn't access your calendar: {error_message}",
                intent=parsed.intent,
                error=error_message,
            ).to_dict()

        # 2. Fetch current events
        events_result = calendar.get_events(
            max_results=settings.SCHEDULER_EVENT_FETCH_MAX_RESULTS,
            time_min=self._local_day_start_utc_iso(
                parsed.date or datetime.now(tz=_SCHEDULER_TZ).date().isoformat()
            ),
        )
        if not events_result["success"]:
            return build_response(
                parsed, False, None, [], [],
                error=f"Failed to retrieve calendar events: {events_result['error']}",
            ).to_dict()

        events: list[dict] = events_result["data"]

        # 3. Route by intent
        return self._route(parsed, events)

    # ------------------------------------------------------------------
    # Private routing
    # ------------------------------------------------------------------

    def _route(
        self,
        parsed: ParsedQuery,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Dispatch to the correct handler based on resolved intent."""
        if parsed.intent == Intent.CREATE:
            return self._handle_create(parsed, events)
        if parsed.intent == Intent.CHECK:
            return self._handle_check(parsed, events)
        if parsed.intent == Intent.SUGGEST:
            return self._handle_suggest(parsed, events)

        return AgentResponse(
            success=False,
            message=(
                "I wasn't sure what you wanted. Try:\n"
                "  • 'Book a meeting …'\n"
                "  • 'Am I free on …'\n"
                "  • 'Suggest a time on …'"
            ),
            intent=parsed.intent,
            error="unknown intent after routing",
        ).to_dict()

    # ------------------------------------------------------------------

    def _handle_create(
        self,
        parsed: ParsedQuery,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Attempt to create an event; if blocked, suggest alternatives.

        Steps:
            1. Validate start/end are available.
            2. Check conflict via scheduler_service.
            3a. No conflict → calendar_tool.create_event().
            3b. Conflict   → scheduler_service.suggest_alternative().
        """
        if not parsed.start_iso or not parsed.end_iso:
            return build_response(
                parsed, False, None, [], [],
                error="Date and time are required to create a meeting.",
            ).to_dict()

        # Conflict check
        conflict_result = has_conflict(events, parsed.start_iso, parsed.end_iso)
        if not conflict_result["success"]:
            return build_response(
                parsed, False, None, [], [],
                error=conflict_result["error"],
            ).to_dict()

        conflict = conflict_result["data"]["has_conflict"]

        if not conflict:
            # Create the event
            create_result = self._calendar.create_event(
                summary=parsed.summary,
                start_time=parsed.start_iso,
                end_time=parsed.end_iso,
                timezone_str=settings.SCHEDULER_TIMEZONE,
            )
            if not create_result["success"]:
                return build_response(
                    parsed, False, None, [], [],
                    error=f"Event creation failed: {create_result['error']}",
                ).to_dict()
            return build_response(
                parsed,
                conflict=False,
                created_event=create_result["data"],
                alternatives=[],
                free_slots=[],
            ).to_dict()

        # Conflict — suggest alternatives
        alt_result = suggest_alternative(
            events,
            requested_time=parsed.start_iso,
            duration_minutes=parsed.duration_minutes,
        )
        alternatives = alt_result["data"]["alternatives"] if alt_result["success"] else []
        return build_response(
            parsed,
            conflict=True,
            created_event=None,
            alternatives=alternatives,
            free_slots=[],
        ).to_dict()

    # ------------------------------------------------------------------

    def _handle_check(
        self,
        parsed: ParsedQuery,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Report whether the requested time is free; offer alternatives if busy.
        """
        if not parsed.start_iso or not parsed.end_iso:
            return build_response(
                parsed, False, None, [], [],
                error="Date and time are required to check availability.",
            ).to_dict()

        conflict_result = has_conflict(events, parsed.start_iso, parsed.end_iso)
        if not conflict_result["success"]:
            return build_response(
                parsed, False, None, [], [],
                error=conflict_result["error"],
            ).to_dict()

        conflict = conflict_result["data"]["has_conflict"]
        alternatives: list[dict] = []

        if conflict:
            alt_result = suggest_alternative(
                events,
                requested_time=parsed.start_iso,
                duration_minutes=parsed.duration_minutes,
            )
            if alt_result["success"]:
                alternatives = alt_result["data"]["alternatives"]

        return build_response(
            parsed,
            conflict=conflict,
            created_event=None,
            alternatives=alternatives,
            free_slots=[],
        ).to_dict()

    # ------------------------------------------------------------------

    def _handle_suggest(
        self,
        parsed: ParsedQuery,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Return free slots for the requested date.

        Falls back to ``suggest_alternative`` when a specific time was given.
        """
        if not parsed.date:
            return build_response(
                parsed, False, None, [], [],
                error="A date is required to suggest available times.",
            ).to_dict()

        slots_result = find_free_slots(
            events,
            date=self._local_day_start_utc_iso(parsed.date),
            slot_minutes=parsed.duration_minutes,
        )
        if not slots_result["success"]:
            return build_response(
                parsed, False, None, [], [],
                error=slots_result["error"],
            ).to_dict()

        free_slots: list[dict] = slots_result["data"]["free_slots"]

        # If a specific start time was also provided, filter/sort by proximity
        if parsed.start_iso and free_slots:
            requested_start = datetime.fromisoformat(parsed.start_iso)
            free_slots = sorted(
                free_slots,
                key=lambda s: abs(
                    (datetime.fromisoformat(s["start"]) - requested_start).total_seconds()
                ),
            )

        return build_response(
            parsed,
            conflict=False,
            created_event=None,
            alternatives=[],
            free_slots=free_slots,
        ).to_dict()


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def run_agent(query: str, calendar_tool: CalendarTool | None = None) -> dict[str, Any]:
    """
    Module-level convenience wrapper around :class:`SchedulingAgent`.

    Args:
        query:         Natural-language user request.
        calendar_tool: Optional pre-configured :class:`CalendarTool`.

    Returns:
        JSON-serialisable agent response dict.

    Example::

        from backend.agents.scheduling_agent import run_agent

        result = run_agent("Suggest available times on Friday")
        print(result["message"])
    """
    agent = SchedulingAgent(calendar_tool=calendar_tool)
    return agent.run(query)