from __future__ import annotations

import logging
from email.utils import getaddresses
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.services.contact_service import bulk_upsert_contacts
from backend.services.google_auth_manager import get_credentials

logger = logging.getLogger(__name__)


def _normalize_contact(name: str, email: str) -> dict[str, str] | None:
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return None
    clean_name = (name or "").strip() or clean_email.split("@", 1)[0]
    return {"name": clean_name, "email": clean_email}


def _fetch_contacts_from_people_api() -> list[dict[str, str]]:
    contacts: list[dict[str, str]] = []
    service = build("people", "v1", credentials=get_credentials())

    page_token: str | None = None
    while True:
        response = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                personFields="names,emailAddresses",
                pageSize=500,
                pageToken=page_token,
            )
            .execute()
        )

        for person in response.get("connections", []):
            names = person.get("names", []) or [{}]
            emails = person.get("emailAddresses", [])
            name_value = names[0].get("displayName", "")
            for email_row in emails:
                normalized = _normalize_contact(name_value, email_row.get("value", ""))
                if normalized:
                    contacts.append(normalized)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return contacts


def _fetch_contacts_from_gmail_headers(max_results: int = 200) -> list[dict[str, str]]:
    contacts: list[dict[str, str]] = []
    gmail = build("gmail", "v1", credentials=get_credentials())

    for label in ("INBOX", "SENT"):
        refs = (
            gmail.users()
            .messages()
            .list(userId="me", labelIds=[label], maxResults=max_results)
            .execute()
            .get("messages", [])
        )

        for ref in refs:
            msg = (
                gmail.users()
                .messages()
                .get(
                    userId="me",
                    id=ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Cc", "Reply-To"],
                )
                .execute()
            )
            headers = msg.get("payload", {}).get("headers", [])
            values = [h.get("value", "") for h in headers if h.get("name") in {"From", "To", "Cc", "Reply-To"}]
            for display_name, email in getaddresses(values):
                normalized = _normalize_contact(display_name, email)
                if normalized:
                    contacts.append(normalized)

    return contacts


def sync_contacts_for_user(user_id: str) -> dict[str, Any]:
    """
    Background sync entry point.

    Strategy:
    1) Try Google Contacts API (People API)
    2) Fallback to Gmail header extraction
    3) Upsert normalized contacts into contacts table
    """
    try:
        source = "people"
        contacts: list[dict[str, str]] = []

        try:
            contacts = _fetch_contacts_from_people_api()
        except HttpError as exc:
            # Common first-run case: People API not enabled for the GCP project.
            # Fall back to Gmail headers instead of failing the sync endpoint.
            logger.warning("People API unavailable; falling back to Gmail headers: %s", exc)
            contacts = []
        except Exception as exc:  # noqa: BLE001
            logger.warning("People API fetch failed; falling back to Gmail headers: %s", exc)
            contacts = []

        if not contacts:
            contacts = _fetch_contacts_from_gmail_headers()
            source = "gmail"

        if not contacts:
            return {"success": True, "synced": 0, "source": source}

        upsert_result = bulk_upsert_contacts(user_id=user_id, contacts=contacts, source=source)
        if not upsert_result.get("success"):
            return {
                "success": False,
                "synced": upsert_result.get("count", 0),
                "source": source,
                "error": upsert_result.get("error", "upsert failed"),
            }

        return {
            "success": True,
            "synced": upsert_result.get("count", 0),
            "source": source,
        }
    except HttpError as exc:
        logger.exception("sync_contacts_for_user Gmail API failed: %s", exc)
        return {"success": False, "synced": 0, "error": f"Google API error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("sync_contacts_for_user failed: %s", exc)
        return {"success": False, "synced": 0, "error": str(exc)}


def run_daily_sync(user_ids: list[str]) -> dict[str, Any]:
    """
    Scheduler-friendly skeleton that can be called by APScheduler/Celery/cron.
    """
    report: list[dict[str, Any]] = []
    for user_id in user_ids:
        result = sync_contacts_for_user(user_id=user_id)
        report.append({"user_id": user_id, **result})

    successful = sum(1 for row in report if row.get("success"))
    return {
        "success": successful == len(report),
        "users_total": len(report),
        "users_successful": successful,
        "report": report,
    }
