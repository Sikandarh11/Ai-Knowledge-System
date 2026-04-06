import os
import datetime
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from backend.core.config import settings

SCOPES = settings.GOOGLE_CALENDAR_SCOPES
TOKEN_PATH = settings.GOOGLE_CALENDAR_TOKEN_PATH
CREDENTIALS_PATH = settings.GOOGLE_CALENDAR_CREDENTIALS_PATH


class GoogleCalendarService:
    def __init__(self):
        self.creds = None
        self.service = self._authenticate()

    

    def _authenticate(self):
        if TOKEN_PATH.exists():
            try:
                # Load granted scopes from token file as-is; do not override here.
                self.creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
            except Exception:
                with open(TOKEN_PATH, 'rb') as token:
                    self.creds = pickle.load(token)

        # Force re-consent when an existing token was issued with insufficient scopes.
        if self.creds and hasattr(self.creds, "has_scopes") and not self.creds.has_scopes(SCOPES):
            self.creds = None
            if TOKEN_PATH.exists():
                TOKEN_PATH.unlink()

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_PATH), SCOPES
                )
                self.creds = flow.run_local_server(port=0, prompt="consent")

            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_PATH.write_text(self.creds.to_json(), encoding='utf-8')

        return build('calendar', 'v3', credentials=self.creds)
    # -----------------------------
    # 📅 GET EVENTS
    # -----------------------------
    def get_events(self, max_results=10):
        now = datetime.datetime.utcnow().isoformat() + 'Z'

        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    # -----------------------------
    # ➕ CREATE EVENT
    # -----------------------------
    def create_event(self, summary, start_time, end_time, description=""):
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        created_event = self.service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        return created_event

    # -----------------------------
    # 🔄 UPDATE EVENT
    # -----------------------------
    def update_event(self, event_id, summary=None, description=None):
        event = self.service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()

        if summary:
            event['summary'] = summary
        if description:
            event['description'] = description

        updated_event = self.service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event
        ).execute()

        return updated_event

    # -----------------------------
    # ❌ DELETE EVENT
    # -----------------------------
    def delete_event(self, event_id):
        self.service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()

        return {"status": "deleted"}