"""Google Calendar service wrapper using centralized auth manager."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.services.google_auth_manager import get_credentials

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Calendar API adapter exposing list/create/delete APIs used by CalendarTool."""

    def __init__(self) -> None:
        creds = get_credentials()
        self.service = build("calendar", "v3", credentials=creds)

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

        try:
            events_result = self.service.events().list(**params).execute()
            return events_result.get("items", [])
        except HttpError as exc:
            logger.exception("Google Calendar list_events failed: %s", exc)
            raise RuntimeError(f"Google Calendar API error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Calendar list_events unexpected error: %s", exc)
            raise RuntimeError(f"Calendar service error: {exc}") from exc

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

        try:
            return self.service.events().insert(calendarId=calendar_id, body=body).execute()
        except HttpError as exc:
            logger.exception("Google Calendar create_event failed: %s", exc)
            raise RuntimeError(f"Google Calendar API error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Calendar create_event unexpected error: %s", exc)
            raise RuntimeError(f"Calendar service error: {exc}") from exc

    def delete_event(
        self,
        calendar_id: str = "primary",
        event_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        event_id = event_id or kwargs.get("eventId")
        if not event_id:
            raise ValueError("'event_id' is required")

        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return {"status": "deleted", "event_id": event_id}
        except HttpError as exc:
            logger.exception("Google Calendar delete_event failed: %s", exc)
            raise RuntimeError(f"Google Calendar API error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("Calendar delete_event unexpected error: %s", exc)
            raise RuntimeError(f"Calendar service error: {exc}") from exc
