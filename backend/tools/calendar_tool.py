"""
calendar_tool.py

A clean tool layer wrapping GoogleCalendarService for use in AI agent systems.
Exposes structured, JSON-friendly outputs for all calendar operations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Replace this import with the real path to your GoogleCalendarService
# ---------------------------------------------------------------------------
from backend.services.google_calendar_service import GoogleCalendarService  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_utc_iso(dt: datetime | str) -> str:
    """
    Normalise a datetime value to a UTC ISO-8601 string.

    Accepts:
    - A timezone-aware ``datetime`` object (converted to UTC).
    - A naive ``datetime`` object (assumed to already be UTC).
    - An ISO-8601 string (returned unchanged).

    Returns:
        A UTC ISO-8601 string such as ``"2024-06-01T09:00:00+00:00"``.
    """
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _parse_event(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a raw Google Calendar API event object into a clean dictionary.

    Args:
        raw: The raw event dict returned by the Google Calendar API.

    Returns:
        A simplified, JSON-serialisable event dictionary with the keys:
        ``id``, ``summary``, ``description``, ``location``,
        ``start``, ``end``, ``status``, ``html_link``, ``attendees``.
    """
    start_raw = raw.get("start", {})
    end_raw = raw.get("end", {})

    attendees = [
        {
            "email": a.get("email", ""),
            "display_name": a.get("displayName", ""),
            "response_status": a.get("responseStatus", "needsAction"),
        }
        for a in raw.get("attendees", [])
    ]

    return {
        "id": raw.get("id", ""),
        "summary": raw.get("summary", "(No title)"),
        "description": raw.get("description", ""),
        "location": raw.get("location", ""),
        "start": start_raw.get("dateTime") or start_raw.get("date", ""),
        "end": end_raw.get("dateTime") or end_raw.get("date", ""),
        "status": raw.get("status", "confirmed"),
        "html_link": raw.get("htmlLink", ""),
        "attendees": attendees,
    }


def _build_response(
    success: bool,
    data: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """
    Build a standardised tool response envelope.

    Args:
        success: Whether the operation succeeded.
        data:    The payload to return on success.
        error:   A human-readable error message on failure.

    Returns:
        ``{"success": bool, "data": ..., "error": str | None}``
    """
    return {"success": success, "data": data, "error": error}


# ---------------------------------------------------------------------------
# CalendarTool
# ---------------------------------------------------------------------------

class CalendarTool:
    """
    Production-ready tool layer over ``GoogleCalendarService``.

    Designed for use inside AI agent pipelines.  Every method returns a
    consistent ``{"success": bool, "data": ..., "error": str | None}``
    envelope so callers never have to deal with raw API exceptions.

    Args:
        service: An initialised ``GoogleCalendarService`` instance.
            If *None* a new instance is created with default credentials.
        calendar_id: The Google Calendar ID to operate on.
            Defaults to ``"primary"``.

    Example::

        tool = CalendarTool()
        result = tool.get_events(max_results=5)
        if result["success"]:
            for event in result["data"]:
                print(event["summary"])
    """

    def __init__(
        self,
        service: GoogleCalendarService | None = None,
        calendar_id: str = "primary",
    ) -> None:
        self._service = service or GoogleCalendarService()
        self._calendar_id = calendar_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_events(
        self,
        max_results: int = 10,
        time_min: datetime | str | None = None,
        time_max: datetime | str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve upcoming calendar events.

        Args:
            max_results: Maximum number of events to return (default 10).
            time_min:    Only return events *starting* at or after this time.
                         Defaults to *now* when omitted.
            time_max:    Only return events *starting* before this time.
            query:       Free-text search term applied to event fields.

        Returns:
            On success::

                {
                    "success": True,
                    "data": [
                        {
                            "id": "...",
                            "summary": "Team standup",
                            "start": "2024-06-01T09:00:00+00:00",
                            "end":   "2024-06-01T09:30:00+00:00",
                            ...
                        },
                        ...
                    ],
                    "error": None
                }

            On failure::

                {"success": False, "data": None, "error": "<message>"}
        """
        try:
            if time_min is None:
                time_min = datetime.now(tz=timezone.utc)

            kwargs: dict[str, Any] = {
                "calendar_id": self._calendar_id,
                "max_results": max_results,
                "time_min": _ensure_utc_iso(time_min),
            }
            if time_max is not None:
                kwargs["time_max"] = _ensure_utc_iso(time_max)
            if query is not None:
                kwargs["query"] = query

            raw_events: list[dict] = self._service.list_events(**kwargs)
            events = [_parse_event(e) for e in raw_events]

            logger.info("get_events returned %d event(s).", len(events))
            return _build_response(success=True, data=events)

        except Exception as exc:  # noqa: BLE001
            logger.exception("get_events failed: %s", exc)
            return _build_response(success=False, error=str(exc))

    # ------------------------------------------------------------------

    def create_event(
        self,
        summary: str,
        start_time: datetime | str,
        end_time: datetime | str,
        description: str = "",
        location: str = "",
        attendee_emails: list[str] | None = None,
        timezone_str: str = "UTC",
    ) -> dict[str, Any]:
        """
        Create a new calendar event.

        Args:
            summary:         Title / name of the event (required).
            start_time:      Event start as a ``datetime`` or ISO-8601 string.
            end_time:        Event end as a ``datetime`` or ISO-8601 string.
            description:     Optional long-form description.
            location:        Optional location string.
            attendee_emails: Optional list of guest e-mail addresses.
            timezone_str:    IANA timezone for the event (default ``"UTC"``).

        Returns:
            On success::

                {
                    "success": True,
                    "data": {
                        "id": "abc123",
                        "summary": "Team standup",
                        "start": "2024-06-01T09:00:00+00:00",
                        "end":   "2024-06-01T09:30:00+00:00",
                        "html_link": "https://calendar.google.com/..."
                        ...
                    },
                    "error": None
                }

            On failure::

                {"success": False, "data": None, "error": "<message>"}
        """
        if not summary or not summary.strip():
            return _build_response(success=False, error="'summary' must not be empty.")

        try:
            start_iso = _ensure_utc_iso(start_time)
            end_iso = _ensure_utc_iso(end_time)

            if start_iso >= end_iso:
                return _build_response(
                    success=False,
                    error="'end_time' must be strictly after 'start_time'.",
                )

            body: dict[str, Any] = {
                "summary": summary.strip(),
                "description": description,
                "location": location,
                "start": {"dateTime": start_iso, "timeZone": timezone_str},
                "end": {"dateTime": end_iso, "timeZone": timezone_str},
            }

            if attendee_emails:
                body["attendees"] = [{"email": e} for e in attendee_emails]

            raw_event: dict = self._service.create_event(
                calendar_id=self._calendar_id,
                body=body,
            )

            event = _parse_event(raw_event)
            logger.info("create_event succeeded: id=%s", event.get("id"))
            return _build_response(success=True, data=event)

        except Exception as exc:  # noqa: BLE001
            logger.exception("create_event failed: %s", exc)
            return _build_response(success=False, error=str(exc))

    # ------------------------------------------------------------------

    def delete_event(self, event_id: str) -> dict[str, Any]:
        """
        Permanently delete a calendar event by its ID.

        Args:
            event_id: The Google Calendar event ID to delete.

        Returns:
            On success::

                {
                    "success": True,
                    "data": {"deleted_event_id": "abc123"},
                    "error": None
                }

            On failure::

                {"success": False, "data": None, "error": "<message>"}
        """
        if not event_id or not event_id.strip():
            return _build_response(success=False, error="'event_id' must not be empty.")

        try:
            self._service.delete_event(
                calendar_id=self._calendar_id,
                event_id=event_id.strip(),
            )
            logger.info("delete_event succeeded: id=%s", event_id)
            return _build_response(
                success=True,
                data={"deleted_event_id": event_id},
            )

        except Exception as exc:  # noqa: BLE001
            logger.exception("delete_event failed: %s", exc)
            return _build_response(success=False, error=str(exc))

    # ------------------------------------------------------------------

    def get_availability(
        self,
        date: datetime | str,
        start_hour: int = 8,
        end_hour: int = 18,
        slot_minutes: int = 30,
    ) -> dict[str, Any]:
        """
        Return free / busy time slots for a given date.

        The method divides the working window (``start_hour`` → ``end_hour``)
        into equal ``slot_minutes`` slots and marks each one as free or busy
        based on existing events.

        Args:
            date:          The target date.  Only the date portion is used;
                           the time component is ignored.
            start_hour:    Start of the working day in 24-hour format (default 8).
            end_hour:      End of the working day in 24-hour format (default 18).
            slot_minutes:  Duration of each availability slot in minutes (default 30).

        Returns:
            On success::

                {
                    "success": True,
                    "data": {
                        "date": "2024-06-01",
                        "free_slots": [
                            {"start": "2024-06-01T08:00:00+00:00",
                             "end":   "2024-06-01T08:30:00+00:00"},
                            ...
                        ],
                        "busy_slots": [
                            {"start": "2024-06-01T09:00:00+00:00",
                             "end":   "2024-06-01T09:30:00+00:00",
                             "event_summary": "Team standup"},
                            ...
                        ]
                    },
                    "error": None
                }

            On failure::

                {"success": False, "data": None, "error": "<message>"}
        """
        try:
            # Normalise *date* to a UTC midnight datetime
            if isinstance(date, str):
                date_obj = datetime.fromisoformat(date).date()
            else:
                date_obj = date.date()

            day_start = datetime(
                date_obj.year, date_obj.month, date_obj.day,
                start_hour, 0, 0, tzinfo=timezone.utc,
            )
            day_end = datetime(
                date_obj.year, date_obj.month, date_obj.day,
                end_hour, 0, 0, tzinfo=timezone.utc,
            )

            # Fetch all events that overlap the working window
            raw_events: list[dict] = self._service.list_events(
                calendar_id=self._calendar_id,
                time_min=day_start.isoformat(),
                time_max=day_end.isoformat(),
                max_results=250,
            )
            events = [_parse_event(e) for e in raw_events]

            # Build (start, end) busy intervals
            busy_intervals: list[tuple[datetime, datetime, str]] = []
            for ev in events:
                try:
                    ev_start = datetime.fromisoformat(ev["start"]).astimezone(timezone.utc)
                    ev_end = datetime.fromisoformat(ev["end"]).astimezone(timezone.utc)
                    busy_intervals.append((ev_start, ev_end, ev["summary"]))
                except (ValueError, KeyError):
                    continue  # skip malformed events

            # Walk the working day in slots
            free_slots: list[dict[str, str]] = []
            busy_slots: list[dict[str, str]] = []
            slot_delta = timedelta(minutes=slot_minutes)
            cursor = day_start

            while cursor + slot_delta <= day_end:
                slot_end = cursor + slot_delta
                overlapping = [
                    b for b in busy_intervals
                    if b[0] < slot_end and b[1] > cursor
                ]
                if overlapping:
                    busy_slots.append({
                        "start": cursor.isoformat(),
                        "end": slot_end.isoformat(),
                        "event_summary": overlapping[0][2],
                    })
                else:
                    free_slots.append({
                        "start": cursor.isoformat(),
                        "end": slot_end.isoformat(),
                    })
                cursor = slot_end

            payload = {
                "date": date_obj.isoformat(),
                "free_slots": free_slots,
                "busy_slots": busy_slots,
            }
            logger.info(
                "get_availability for %s: %d free, %d busy slot(s).",
                date_obj.isoformat(), len(free_slots), len(busy_slots),
            )
            return _build_response(success=True, data=payload)

        except Exception as exc:  # noqa: BLE001
            logger.exception("get_availability failed: %s", exc)
            return _build_response(success=False, error=str(exc))