"""
Compatibility wrapper for Google Calendar service.

This module provides the interface expected by `backend.tools.calendar_tool`
while reusing the existing authentication/bootstrap logic in
`backend.services.google_calendar`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.services.google_calendar import GoogleCalendarService as _LegacyGoogleCalendarService


class GoogleCalendarService(_LegacyGoogleCalendarService):
    """Adapter exposing list/create/delete APIs used by CalendarTool."""

    def list_events(
        self,
        calendar_id: str = "primary",
        max_results: int = 10,
        time_min: str | None = None,
        time_max: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        if time_min is None:
            time_min = datetime.now(timezone.utc).isoformat()

        params: dict[str, Any] = {
            "calendarId": calendar_id,
            "timeMin": time_min,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query

        events_result = self.service.events().list(**params).execute()
        return events_result.get("items", [])

    def create_event(
        self,
        calendar_id: str = "primary",
        body: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if body is None:
            summary = kwargs.get("summary", "Meeting")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            description = kwargs.get("description", "")
            if not start_time or not end_time:
                raise ValueError("'start_time' and 'end_time' are required when body is not provided")

            body = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_time, "timeZone": "UTC"},
                "end": {"dateTime": end_time, "timeZone": "UTC"},
            }

        return self.service.events().insert(calendarId=calendar_id, body=body).execute()

    def delete_event(
        self,
        calendar_id: str = "primary",
        event_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        event_id = event_id or kwargs.get("eventId")
        if not event_id:
            raise ValueError("'event_id' is required")

        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return {"status": "deleted", "event_id": event_id}
