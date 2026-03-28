import os
import datetime
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, "token.pickle")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")


class GoogleCalendarService:
    def __init__(self):
        self.creds = None
        self.service = self._authenticate()

    

    def _authenticate(self):
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(self.creds, token)

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