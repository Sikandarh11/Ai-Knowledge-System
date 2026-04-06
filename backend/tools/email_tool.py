"""
email_tool.py

Gmail tool layer for fetching and parsing emails.

Responsibilities:
    - Fetch latest emails via the Gmail API service object
    - Decode and extract subject, sender, and body from raw messages
    - Handle multipart MIME structures and base64url encoding
    - Strip HTML to return clean readable text

No authentication logic lives here — pass in the service object returned
by ``gmail_auth.authenticate_gmail()``.

Consistent with calendar_tool.py:
    - Every public function returns ``{"success": bool, "data": ..., "error": str | None}``
    - Exceptions are caught and surfaced in the envelope rather than raised
    - Internal helpers are prefixed with ``_``
"""

from __future__ import annotations

import base64
import logging
import re
from email import message_from_bytes
from email.message import Message
from typing import Any
import base64
from email.mime.text import MIMEText

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_response(
    success: bool,
    data: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """
    Construct the standard tool response envelope.

    Args:
        success: Whether the operation succeeded.
        data:    Result payload (JSON-serialisable).
        error:   Human-readable error message, or ``None`` on success.

    Returns:
        ``{"success": bool, "data": ..., "error": str | None}``
    """
    return {"success": success, "data": data, "error": error}


def _decode_base64url(encoded: str) -> str:
    """
    Decode a base64url-encoded string (as used by the Gmail API) to UTF-8 text.

    Gmail uses URL-safe base64 (``-`` and ``_`` instead of ``+`` and ``/``)
    without padding.  This helper restores padding before decoding.

    Args:
        encoded: A base64url string from a Gmail message part ``body.data`` field.

    Returns:
        Decoded UTF-8 string.  Returns an empty string on any decoding error
        rather than raising, so a single malformed part never drops the whole email.
    """
    if not encoded:
        return ""
    try:
        # Restore standard base64 alphabet and padding
        padded = encoded.replace("-", "+").replace("_", "/")
        padded += "=" * (-len(padded) % 4)
        return base64.b64decode(padded).decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        logger.warning("base64url decode failed: %s", exc)
        return ""


def _extract_body_from_mime(msg: Message) -> str:
    """
    Walk a parsed MIME message and extract the best available body text.

    Preference order:
        1. ``text/plain`` part — returned as-is.
        2. ``text/html`` part — returned raw (caller can clean with
           :func:`clean_email_body`).

    For non-multipart messages the payload is returned directly.

    Args:
        msg: A :class:`email.message.Message` object built from raw bytes.

    Returns:
        The best available body string (may contain HTML).
    """
    if not msg.is_multipart():
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace") if isinstance(payload, bytes) else ""

    plain_part: str | None = None
    html_part:  str | None = None

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition  = str(part.get("Content-Disposition", ""))

        # Skip attachments
        if "attachment" in disposition:
            continue

        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue

        charset = part.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")

        if content_type == "text/plain" and plain_part is None:
            plain_part = text
        elif content_type == "text/html" and html_part is None:
            html_part = text

    return plain_part or html_part or ""


def _parse_payload_parts(parts: list[dict[str, Any]]) -> str:
    """
    Recursively extract body text from Gmail API message ``parts`` structures.

    The Gmail API represents MIME parts as nested dicts rather than a parsed
    :class:`email.message.Message`.  This helper walks the tree, preferring
    ``text/plain`` over ``text/html`` at every level.

    Args:
        parts: The ``payload.parts`` list from a full Gmail API message object.

    Returns:
        Best available body string (may contain HTML if no plain part exists).
    """
    plain: str | None = None
    html:  str | None = None

    for part in parts:
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data", "")

        # Recurse into nested multipart containers
        if mime_type.startswith("multipart/") and part.get("parts"):
            nested = _parse_payload_parts(part["parts"])
            if nested:
                plain = plain or nested
            continue

        if mime_type == "text/plain" and body_data and plain is None:
            plain = _decode_base64url(body_data)
        elif mime_type == "text/html" and body_data and html is None:
            html = _decode_base64url(body_data)

    return plain or html or ""


def _extract_body(payload: dict[str, Any]) -> str:
    """
    Extract the email body from a Gmail API message payload dict.

    Handles three structures returned by the Gmail API:
        1. Simple (non-multipart): body data lives in ``payload.body.data``.
        2. Multipart (API parts): body data is split across ``payload.parts``.
        3. Raw ``data`` field with base64url encoding that wraps a full MIME
           message (less common but present on some forwarded messages).

    Args:
        payload: The ``payload`` field of a Gmail API message object.

    Returns:
        Decoded body string (may contain HTML; pass through
        :func:`clean_email_body` to strip tags).
    """
    mime_type = payload.get("mimeType", "")

    # --- Case 1: simple message with body data directly in payload ----------
    body_data = payload.get("body", {}).get("data", "")
    if body_data and not mime_type.startswith("multipart/"):
        return _decode_base64url(body_data)

    # --- Case 2: multipart — recurse through parts --------------------------
    parts = payload.get("parts", [])
    if parts:
        return _parse_payload_parts(parts)

    # --- Case 3: raw MIME bytes embedded in body.data -----------------------
    if body_data:
        raw_bytes = base64.urlsafe_b64decode(
            body_data + "=" * (-len(body_data) % 4)
        )
        try:
            msg = message_from_bytes(raw_bytes)
            return _extract_body_from_mime(msg)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse raw MIME body: %s", exc)

    return ""


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """
    Extract a single header value (case-insensitive) from the Gmail headers list.

    Args:
        headers: List of ``{"name": str, "value": str}`` dicts from the API.
        name:    Header name to look up (e.g. ``"Subject"``, ``"From"``).

    Returns:
        The header value, or an empty string if not found.
    """
    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value", "")
    return ""


def _parse_message(raw_message: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a full Gmail API message object into a clean, flat dictionary.

    Args:
        raw_message: A message resource returned by
                     ``service.users().messages().get(..., format="full")``.

    Returns:
        A dict with keys:
            ``id``, ``thread_id``, ``subject``, ``sender``,
            ``date``, ``snippet``, ``body``, ``body_clean``,
            ``label_ids``.
    """
    msg_id    = raw_message.get("id", "")
    thread_id = raw_message.get("threadId", "")
    snippet   = raw_message.get("snippet", "")
    label_ids = raw_message.get("labelIds", [])

    payload  = raw_message.get("payload", {})
    headers  = payload.get("headers", [])

    subject = _get_header(headers, "Subject") or "(No subject)"
    sender  = _get_header(headers, "From")    or "(Unknown sender)"
    date    = _get_header(headers, "Date")    or ""

    body       = _extract_body(payload)
    body_clean = clean_email_body(body)

    return {
        "id":         msg_id,
        "thread_id":  thread_id,
        "subject":    subject,
        "sender":     sender,
        "date":       date,
        "snippet":    snippet,
        "body":       body,
        "body_clean": body_clean,
        "label_ids":  label_ids,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_email_body(body: str) -> str:
    """
    Strip HTML tags and normalise whitespace in an email body string.

    Handles:
        - All HTML tags (``<p>``, ``<br>``, ``<div>``, ``<a>``, etc.)
        - Common HTML entities (``&nbsp;``, ``&amp;``, ``&lt;``, ``&gt;``,
          ``&quot;``, ``&#39;``)
        - Consecutive blank lines collapsed to a single blank line
        - Leading and trailing whitespace

    Args:
        body: Raw email body, which may or may not contain HTML markup.

    Returns:
        Clean, human-readable plain text.

    Example::

        clean_email_body("<p>Hello <b>world</b>!&nbsp;</p>")
        # "Hello world!"
    """
    if not body:
        return ""

    # Replace block-level tags with newlines before stripping
    body = re.sub(r"<br\s*/?>",           "\n",  body, flags=re.IGNORECASE)
    body = re.sub(r"</?(p|div|tr|li)\b[^>]*>", "\n",  body, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    body = re.sub(r"<[^>]+>", "", body)

    # Decode common HTML entities
    entities = {
        "&nbsp;":  " ",
        "&amp;":   "&",
        "&lt;":    "<",
        "&gt;":    ">",
        "&quot;":  '"',
        "&#39;":   "'",
        "&apos;":  "'",
        "&mdash;": "—",
        "&ndash;": "–",
        "&hellip;":"…",
    }
    for entity, char in entities.items():
        body = body.replace(entity, char)

    # Collapse runs of blank lines → single blank line
    body = re.sub(r"\n{3,}", "\n\n", body)

    return body.strip()


def fetch_emails(
    service: Any,
    max_results: int = 5,
    label_ids: list[str] | None = None,
    query: str = "",
) -> dict[str, Any]:
    """
    Fetch and parse the latest emails from the authenticated Gmail account.

    Retrieves message IDs from the list endpoint, then fetches each message
    in full to extract headers and body.  Multipart and HTML emails are both
    handled transparently.

    Args:
        service:     Gmail API service object returned by
                     ``gmail_auth.authenticate_gmail()``.
        max_results: Maximum number of emails to return (default 5, max 500).
        label_ids:   Optional list of Gmail label IDs to filter by
                     (e.g. ``["INBOX"]``, ``["UNREAD"]``).
                     Defaults to ``["INBOX"]`` when ``None``.
        query:       Optional Gmail search query string (same syntax as the
                     Gmail search box), e.g. ``"from:boss@example.com"``,
                     ``"is:unread"``, ``"subject:invoice"``.

    Returns:
        On success::

            {
                "success": True,
                "data": [
                    {
                        "id":         "18f3a...",
                        "thread_id":  "18f3a...",
                        "subject":    "Weekly report",
                        "sender":     "Alice <alice@example.com>",
                        "date":       "Mon, 01 Jan 2024 09:00:00 +0000",
                        "snippet":    "Hi team, please find...",
                        "body":       "<html>...</html>",
                        "body_clean": "Hi team, please find...",
                        "label_ids":  ["INBOX", "UNREAD"]
                    },
                    ...
                ],
                "error": None
            }

        On failure::

            {"success": False, "data": None, "error": "<message>"}

    Example::

        from gmail_auth import authenticate_gmail
        from backend.tools.email_tool import fetch_emails

        service = authenticate_gmail()

        # Latest 5 inbox emails
        result = fetch_emails(service)

        # Unread emails from a specific sender
        result = fetch_emails(service, max_results=10, query="from:boss@example.com is:unread")

        if result["success"]:
            for email in result["data"]:
                print(email["subject"], "—", email["sender"])
                print(email["body_clean"][:200])
    """
    if label_ids is None:
        label_ids = ["INBOX"]

    try:
        # Step 1: retrieve message IDs
        list_kwargs: dict[str, Any] = {
            "userId":     "me",
            "maxResults": max(1, min(max_results, 500)),
            "labelIds":   label_ids,
        }
        if query:
            list_kwargs["q"] = query

        list_response = service.users().messages().list(**list_kwargs).execute()
        message_refs: list[dict] = list_response.get("messages", [])

        if not message_refs:
            logger.info("fetch_emails: no messages matched the query.")
            return _build_response(success=True, data=[])

        # Step 2: fetch each message in full and parse
        emails: list[dict[str, Any]] = []
        for ref in message_refs:
            try:
                raw = service.users().messages().get(
                    userId="me",
                    id=ref["id"],
                    format="full",
                ).execute()
                emails.append(_parse_message(raw))
            except HttpError as exc:
                logger.warning("Could not fetch message %s: %s", ref["id"], exc)
                continue  # skip this message, collect the rest

        logger.info("fetch_emails: returned %d email(s).", len(emails))
        return _build_response(success=True, data=emails)

    except HttpError as exc:
        logger.exception("fetch_emails HttpError: %s", exc)
        return _build_response(success=False, error=f"Gmail API error: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("fetch_emails unexpected error: %s", exc)
        return _build_response(success=False, error=str(exc))



import base64
from email.mime.text import MIMEText


def send_email(
    service: Any,
    to: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    try:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )

        return _build_response(success=True, data=sent)

    except Exception as exc:
        logger.exception("send_email failed: %s", exc)
        return _build_response(success=False, error=str(exc))