"""
scheduler_service.py

Backend scheduling service responsible for:
    - Conflict detection against existing calendar events
    - Free slot generation within working hours
    - Alternative meeting time suggestions

Conventions:
    - All datetimes are UTC-aware ISO-8601 strings on input/output
    - Work hours: 09:00 – 18:00 UTC
    - Minimum slot duration: 30 minutes
    - Every public function returns a structured, JSON-serialisable dict
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORK_START_HOUR: int = settings.SCHEDULER_WORK_START_HOUR
WORK_END_HOUR: int = settings.SCHEDULER_WORK_END_HOUR
MIN_SLOT_MINUTES: int = settings.SCHEDULER_MIN_SLOT_MINUTES
_SLOT_DELTA = timedelta(minutes=MIN_SLOT_MINUTES)
_DAY_DELTA = timedelta(days=1)
MAX_ALTERNATIVE_DAYS: int = settings.SCHEDULER_MAX_ALTERNATIVE_DAYS
MAX_ALTERNATIVES: int = settings.SCHEDULER_MAX_ALTERNATIVES


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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_utc(iso_string: str) -> datetime:
    """
    Parse an ISO-8601 string and return a UTC-aware ``datetime``.

    Naive strings (no timezone suffix) are assumed to already be UTC.

    Args:
        iso_string: An ISO-8601 datetime string, e.g.
                    ``"2024-06-01T09:00:00+00:00"`` or
                    ``"2024-06-01T09:00:00"``.

    Returns:
        A ``datetime`` object in UTC.

    Raises:
        ValueError: If ``iso_string`` cannot be parsed.
    """
    # Python 3.10 doesn't support the Z suffix — replace it with +00:00
    iso_string = iso_string.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _to_iso(dt: datetime) -> str:
    """Return a UTC ISO-8601 string for *dt*, converting if necessary."""
    return dt.astimezone(timezone.utc).isoformat()


def _working_window(date: datetime) -> tuple[datetime, datetime]:
    """
    Return the UTC work-hour boundaries for the calendar date of *date*.

    Args:
        date: Any UTC ``datetime``; only its date portion is used.

    Returns:
        ``(work_start, work_end)`` as UTC-aware ``datetime`` objects.
    """
    local_date = date.astimezone(_SCHEDULER_TZ).date()
    work_start_local = datetime(
        local_date.year,
        local_date.month,
        local_date.day,
        WORK_START_HOUR,
        0,
        0,
        tzinfo=_SCHEDULER_TZ,
    )
    work_end_local = datetime(
        local_date.year,
        local_date.month,
        local_date.day,
        WORK_END_HOUR,
        0,
        0,
        tzinfo=_SCHEDULER_TZ,
    )
    return work_start_local.astimezone(timezone.utc), work_end_local.astimezone(timezone.utc)


def _parse_events(
    events: list[dict[str, Any]],
) -> list[tuple[datetime, datetime]]:
    """
    Convert a list of raw event dicts to sorted ``(start, end)`` UTC tuples.

    Malformed events (missing/unparseable fields) are skipped with a warning.

    Args:
        events: List of dicts, each with ``"start"`` and ``"end"`` ISO strings.

    Returns:
        Sorted list of ``(start_dt, end_dt)`` tuples.
    """
    parsed: list[tuple[datetime, datetime]] = []
    for idx, ev in enumerate(events):
        try:
            start = _parse_utc(ev["start"])
            end = _parse_utc(ev["end"])
            if end <= start:
                logger.warning("Event %d skipped: end <= start.", idx)
                continue
            parsed.append((start, end))
        except (KeyError, ValueError) as exc:
            logger.warning("Event %d skipped due to parse error: %s", idx, exc)
    return sorted(parsed, key=lambda t: t[0])


def _overlaps(
    ev_start: datetime,
    ev_end: datetime,
    slot_start: datetime,
    slot_end: datetime,
) -> bool:
    """
    Return ``True`` when ``[ev_start, ev_end)`` overlaps ``[slot_start, slot_end)``.

    Two intervals overlap when one starts before the other ends and vice-versa.
    """
    return ev_start < slot_end and ev_end > slot_start


def _build_response(
    success: bool,
    data: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """
    Construct a standardised service response envelope.

    Args:
        success: Whether the operation succeeded.
        data:    Result payload (JSON-serialisable).
        error:   Human-readable error message, or ``None`` on success.

    Returns:
        ``{"success": bool, "data": ..., "error": str | None}``
    """
    return {"success": success, "data": data, "error": error}


def _free_slots_for_day(
    sorted_events: list[tuple[datetime, datetime]],
    work_start: datetime,
    work_end: datetime,
    slot_duration: timedelta = _SLOT_DELTA,
) -> list[dict[str, str]]:
    """
    Compute free slots for a single working day given pre-sorted events.

    Args:
        sorted_events:  Pre-sorted ``(start, end)`` tuples (may span multiple days;
                        only those overlapping today's window are considered).
        work_start:     Start of the working window for the target day.
        work_end:       End of the working window for the target day.
        slot_duration:  Minimum duration each free slot must have.

    Returns:
        List of ``{"start": iso, "end": iso, "duration_minutes": int}`` dicts.
    """
    slots: list[dict[str, str]] = []
    cursor = work_start

    # Collect busy intervals that overlap this day's work window
    busy: list[tuple[datetime, datetime]] = [
        (max(s, work_start), min(e, work_end))
        for s, e in sorted_events
        if _overlaps(s, e, work_start, work_end)
    ]
    busy.sort(key=lambda t: t[0])

    busy_idx = 0
    while cursor + slot_duration <= work_end:
        slot_end = cursor + slot_duration

        # Advance past any busy blocks that start before slot_end
        blocked = False
        while busy_idx < len(busy) and busy[busy_idx][0] < slot_end:
            b_start, b_end = busy[busy_idx]
            if b_start < slot_end and b_end > cursor:
                # Overlap — jump cursor to end of this busy block
                cursor = b_end
                blocked = True
                busy_idx += 1
                break
            busy_idx += 1

        if blocked:
            continue  # re-evaluate from new cursor position

        if cursor + slot_duration <= work_end:
            slots.append({
                "start": _to_iso(cursor),
                "end": _to_iso(cursor + slot_duration),
                "duration_minutes": int(slot_duration.total_seconds() // 60),
            })
        cursor += slot_duration

    return slots


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def has_conflict(
    events: list[dict[str, Any]],
    start_time: str,
    end_time: str,
) -> dict[str, Any]:
    """
    Check whether a proposed time window conflicts with existing events.

    An overlap exists when a proposed interval shares any time with an
    existing event (boundaries touching are *not* considered a conflict).

    Args:
        events:     Existing calendar events, each with ``"start"`` and
                    ``"end"`` ISO-8601 strings.
        start_time: Proposed start as a UTC ISO-8601 string.
        end_time:   Proposed end as a UTC ISO-8601 string.

    Returns:
        On success::

            {
                "success": True,
                "data": {
                    "has_conflict": bool,
                    "conflicting_events": [
                        {"start": "...", "end": "..."},
                        ...
                    ]
                },
                "error": None
            }

        On failure::

            {"success": False, "data": None, "error": "<message>"}

    Example::

        result = has_conflict(
            events=[{"start": "2024-06-01T09:00:00Z", "end": "2024-06-01T10:00:00Z"}],
            start_time="2024-06-01T09:30:00Z",
            end_time="2024-06-01T10:30:00Z",
        )
        # result["data"]["has_conflict"] → True
    """
    try:
        proposed_start = _parse_utc(start_time)
        proposed_end = _parse_utc(end_time)

        if proposed_end <= proposed_start:
            return _build_response(
                success=False,
                error="'end_time' must be strictly after 'start_time'.",
            )

        sorted_events = _parse_events(events)

        conflicts = [
            {"start": _to_iso(s), "end": _to_iso(e)}
            for s, e in sorted_events
            if _overlaps(s, e, proposed_start, proposed_end)
        ]

        logger.info(
            "has_conflict [%s → %s]: %d conflict(s) found.",
            start_time, end_time, len(conflicts),
        )
        return _build_response(
            success=True,
            data={
                "has_conflict": bool(conflicts),
                "conflicting_events": conflicts,
            },
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("has_conflict raised: %s", exc)
        return _build_response(success=False, error=str(exc))


# ---------------------------------------------------------------------------

def find_free_slots(
    events: list[dict[str, Any]],
    date: str,
    slot_minutes: int = MIN_SLOT_MINUTES,
) -> dict[str, Any]:
    """
    Return all free slots of at least *slot_minutes* on the given date.

    Free slots are computed within working hours (09:00–18:00 UTC) by
    subtracting busy event intervals from the working window and enumerating
    non-overlapping slots of *slot_minutes* duration.

    Args:
        events:       Existing calendar events with ``"start"`` / ``"end"`` keys.
        date:         Target date as an ISO-8601 string (time portion ignored).
        slot_minutes: Minimum free-slot duration in minutes (default 30).

    Returns:
        On success::

            {
                "success": True,
                "data": {
                    "date": "2024-06-01",
                    "work_start": "2024-06-01T09:00:00+00:00",
                    "work_end":   "2024-06-01T18:00:00+00:00",
                    "slot_duration_minutes": 30,
                    "free_slots": [
                        {
                            "start": "2024-06-01T09:00:00+00:00",
                            "end":   "2024-06-01T09:30:00+00:00",
                            "duration_minutes": 30
                        },
                        ...
                    ],
                    "total_free_slots": 5
                },
                "error": None
            }

        On failure::

            {"success": False, "data": None, "error": "<message>"}
    """
    try:
        if slot_minutes < 1:
            return _build_response(
                success=False, error="'slot_minutes' must be a positive integer."
            )

        target_dt = _parse_utc(date)
        work_start, work_end = _working_window(target_dt)
        slot_duration = timedelta(minutes=slot_minutes)

        if slot_duration > (work_end - work_start):
            return _build_response(
                success=False,
                error=(
                    f"slot_minutes ({slot_minutes}) exceeds the working window "
                    f"({WORK_START_HOUR}:00-{WORK_END_HOUR}:00 {settings.SCHEDULER_TIMEZONE})."
                ),
            )

        sorted_events = _parse_events(events)
        free_slots = _free_slots_for_day(
            sorted_events, work_start, work_end, slot_duration
        )

        logger.info(
            "find_free_slots [%s]: %d free slot(s) found.",
            target_dt.date().isoformat(), len(free_slots),
        )
        return _build_response(
            success=True,
            data={
                "date": target_dt.date().isoformat(),
                "work_start": _to_iso(work_start),
                "work_end": _to_iso(work_end),
                "slot_duration_minutes": slot_minutes,
                "free_slots": free_slots,
                "total_free_slots": len(free_slots),
            },
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("find_free_slots raised: %s", exc)
        return _build_response(success=False, error=str(exc))


# ---------------------------------------------------------------------------

def suggest_alternative(
    events: list[dict[str, Any]],
    requested_time: str,
    duration_minutes: int = MIN_SLOT_MINUTES,
    max_suggestions: int = MAX_ALTERNATIVES,
    max_days_ahead: int = MAX_ALTERNATIVE_DAYS,
) -> dict[str, Any]:
    """
    Suggest alternative meeting times when the requested time has a conflict.

    The function first checks whether *requested_time* is conflict-free; if so,
    it is returned as-is.  Otherwise it searches forward (same day first, then
    subsequent working days) for free slots of the required duration.

    Args:
        events:           Existing calendar events with ``"start"``/``"end"`` keys.
        requested_time:   Desired meeting start as a UTC ISO-8601 string.
        duration_minutes: Required meeting length in minutes (default 30).
        max_suggestions:  Maximum number of alternatives to return (default 3).
        max_days_ahead:   How many calendar days ahead to search (default 7).

    Returns:
        On success::

            {
                "success": True,
                "data": {
                    "requested_time": "2024-06-01T09:00:00+00:00",
                    "requested_end":  "2024-06-01T09:30:00+00:00",
                    "conflict_free":  False,
                    "alternatives": [
                        {
                            "start": "2024-06-01T10:00:00+00:00",
                            "end":   "2024-06-01T10:30:00+00:00",
                            "duration_minutes": 30,
                            "same_day": True
                        },
                        ...
                    ]
                },
                "error": None
            }

        On failure::

            {"success": False, "data": None, "error": "<message>"}
    """
    try:
        if duration_minutes < 1:
            return _build_response(
                success=False, error="'duration_minutes' must be a positive integer."
            )

        requested_start = _parse_utc(requested_time)
        slot_duration = timedelta(minutes=duration_minutes)
        requested_end = requested_start + slot_duration

        sorted_events = _parse_events(events)

        # --- Check if requested time is already conflict-free ---------------
        conflict = any(
            _overlaps(s, e, requested_start, requested_end)
            for s, e in sorted_events
        )

        if not conflict:
            logger.info("suggest_alternative: requested time is conflict-free.")
            return _build_response(
                success=True,
                data={
                    "requested_time": _to_iso(requested_start),
                    "requested_end": _to_iso(requested_end),
                    "conflict_free": True,
                    "alternatives": [],
                },
            )

        # --- Search for alternatives ----------------------------------------
        alternatives: list[dict[str, Any]] = []
        search_date = requested_start  # start search from the same day

        for day_offset in range(max_days_ahead):
            if len(alternatives) >= max_suggestions:
                break

            work_start, work_end = _working_window(search_date)
            is_same_day = (day_offset == 0)

            # On the first day, begin search from the requested time (not 09:00)
            effective_start = max(work_start, requested_start) if is_same_day else work_start

            # Snap effective_start to the next slot boundary
            if is_same_day and effective_start > work_start:
                elapsed = int(
                    (effective_start - work_start).total_seconds() // 60
                )
                remainder = elapsed % duration_minutes
                if remainder:
                    effective_start += timedelta(minutes=duration_minutes - remainder)

            cursor = effective_start

            while cursor + slot_duration <= work_end:
                slot_end = cursor + slot_duration
                busy = any(
                    _overlaps(s, e, cursor, slot_end)
                    for s, e in sorted_events
                )
                if not busy:
                    alternatives.append({
                        "start": _to_iso(cursor),
                        "end": _to_iso(slot_end),
                        "duration_minutes": duration_minutes,
                        "same_day": is_same_day,
                    })
                    if len(alternatives) >= max_suggestions:
                        break
                    cursor = slot_end          # non-overlapping next candidate
                else:
                    cursor += _SLOT_DELTA      # step forward by minimum unit

            search_date = work_start + _DAY_DELTA   # advance to next calendar day

        logger.info(
            "suggest_alternative: %d alternative(s) found for %s.",
            len(alternatives), requested_time,
        )
        return _build_response(
            success=True,
            data={
                "requested_time": _to_iso(requested_start),
                "requested_end": _to_iso(requested_end),
                "conflict_free": False,
                "alternatives": alternatives[:max_suggestions],
            },
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("suggest_alternative raised: %s", exc)
        return _build_response(success=False, error=str(exc))