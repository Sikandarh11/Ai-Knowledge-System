"""
email_service.py

Service layer for email processing.

Orchestrates the email tool and agent layers — no direct API calls.
Consistent with scheduler_service.py and google_calendar_service.py:
    - All public functions return {"success": bool, "data": ..., "error": str | None}
    - Exceptions are caught and surfaced in the envelope rather than raised
    - Internal helpers are prefixed with _
"""

from __future__ import annotations

import logging
from typing import Any

from backend.agents.email_agent import EmailAgent

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
    Construct the standard service response envelope.

    Args:
        success: Whether the operation succeeded.
        data:    Result payload (JSON-serialisable).
        error:   Human-readable error message, or ``None`` on success.

    Returns:
        ``{"success": bool, "data": ..., "error": str | None}``
    """
    return {"success": success, "data": data, "error": error}


def _validate_email(email: dict[str, Any]) -> str | None:
    """
    Validate that the email dict contains the minimum required fields.

    Args:
        email: Parsed email dict from ``email_tool.fetch_emails()``.

    Returns:
        An error string if validation fails, or ``None`` if the email is valid.
    """
    if not isinstance(email, dict):
        return "email must be a dict."
    if not email.get("body_clean") and not email.get("body"):
        return "email must contain a non-empty 'body_clean' or 'body' field."
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_email(
    email: dict[str, Any],
    reply_tone: str = "formal",
    agent: EmailAgent | None = None,
) -> dict[str, Any]:
    """
    Orchestrate summarisation, intent detection, and reply generation for
    a single parsed email.

    Calls the following agent methods in sequence:
        1. ``summarize_email``  — 2-3 line summary of the email content.
        2. ``detect_intent``    — classifies the email as URGENT or NORMAL.
        3. ``generate_reply``   — drafts a reply in the requested tone.

    No direct Gmail or OpenAI API calls are made here; all LLM interaction
    is delegated to :class:`backend.agents.email_agent.EmailAgent`.

    Args:
        email:      Parsed email dict as returned by
                    ``backend.tools.email_tool.fetch_emails()``.
                    Must contain at least one of ``body_clean`` or ``body``.
        reply_tone: Tone for the generated reply — ``"formal"`` (default),
                    ``"friendly"``, or ``"concise"``.
        agent:      Optional pre-configured :class:`EmailAgent` instance.
                    A default instance is created when ``None``, using the
                    ``OPENAI_API_KEY`` environment variable.

    Returns:
        On success::

            {
                "success": True,
                "data": {
                    "id":         "18f3a...",
                    "subject":    "Q2 Budget Proposal",
                    "sender":     "alice@example.com",
                    "summary":    "Alice is requesting sign-off on the Q2 budget...",
                    "intent":     "Classification: URGENT\\nReason: Deadline is today.",
                    "reply":      "Dear Alice,\\n\\nThank you for your message...",
                    "reply_tone": "formal"
                },
                "error": None
            }

        On validation failure::

            {"success": False, "data": None, "error": "email must contain a non-empty body."}

        On LLM failure::

            {"success": False, "data": None, "error": "LLM call failed: ..."}

    Example::

        from backend.tools.email_tool import fetch_emails
        from backend.services.email_service import process_email
        from gmail_auth import authenticate_gmail

        service = authenticate_gmail()
        emails  = fetch_emails(service, max_results=1)

        if emails["success"] and emails["data"]:
            result = process_email(emails["data"][0])
            if result["success"]:
                print(result["data"]["summary"])
                print(result["data"]["intent"])
                print(result["data"]["reply"])
    """
    # --- Validate -----------------------------------------------------------
    validation_error = _validate_email(email)
    if validation_error:
        logger.warning("process_email validation failed: %s", validation_error)
        return _build_response(success=False, error=validation_error)

    subject = email.get("subject", "(No subject)")
    sender  = email.get("sender",  "(Unknown)")
    logger.info("process_email | subject=%r sender=%r tone=%r", subject, sender, reply_tone)

    # --- Orchestrate --------------------------------------------------------
    _agent = agent or EmailAgent()

    summary: str | None = None
    intent:  str | None = None
    reply:   str | None = None

    try:
        summary = _agent.summarize_email(email)
        logger.debug("process_email: summary done")
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_email: summarize_email failed: %s", exc)
        return _build_response(success=False, error=f"summarize_email failed: {exc}")

    try:
        intent = _agent.detect_intent(email)
        logger.debug("process_email: intent detection done")
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_email: detect_intent failed: %s", exc)
        return _build_response(success=False, error=f"detect_intent failed: {exc}")

    try:
        reply = _agent.generate_reply(email, tone=reply_tone)  # type: ignore[arg-type]
        logger.debug("process_email: reply generation done")
    except ValueError as exc:
        logger.error("process_email: invalid tone %r — %s", reply_tone, exc)
        return _build_response(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_email: generate_reply failed: %s", exc)
        return _build_response(success=False, error=f"generate_reply failed: {exc}")

    # --- Return -------------------------------------------------------------
    return _build_response(
        success=True,
        data={
            "id":         email.get("id", ""),
            "subject":    subject,
            "sender":     sender,
            "summary":    summary,
            "intent":     intent,
            "reply":      reply,
            "reply_tone": reply_tone,
        },
    )


def process_emails_bulk(
    emails: list[dict[str, Any]],
    reply_tone: str = "formal",
    agent: EmailAgent | None = None,
    skip_on_error: bool = True,
) -> dict[str, Any]:
    """
    Process a list of emails, running the full pipeline on each one.

    Delegates to :func:`process_email` for each item.  When *skip_on_error*
    is ``True`` (default) a failed email is recorded in ``errors`` and
    processing continues; when ``False`` the first failure aborts the batch.

    Args:
        emails:        List of parsed email dicts.
        reply_tone:    Tone applied to all generated replies.
        agent:         Optional shared :class:`EmailAgent` instance (re-used
                       across all emails to avoid repeated client construction).
        skip_on_error: Continue processing remaining emails after a failure.

    Returns:
        On success::

            {
                "success": True,
                "data": {
                    "processed": [ { ...process_email data... }, ... ],
                    "errors":    [ { "index": 1, "subject": "...", "error": "..." } ],
                    "total":     5,
                    "succeeded": 4,
                    "failed":    1
                },
                "error": None
            }

        Hard abort (skip_on_error=False, first failure)::

            {"success": False, "data": None, "error": "..."}

    Example::

        from backend.services.email_service import process_emails_bulk

        result = process_emails_bulk(emails["data"], reply_tone="concise")
        if result["success"]:
            for item in result["data"]["processed"]:
                print(item["subject"], "->", item["intent"])
    """
    if not emails:
        return _build_response(
            success=True,
            data={"processed": [], "errors": [], "total": 0, "succeeded": 0, "failed": 0},
        )

    _agent = agent or EmailAgent()
    processed: list[dict[str, Any]] = []
    errors:    list[dict[str, Any]] = []

    for idx, email in enumerate(emails):
        result = process_email(email, reply_tone=reply_tone, agent=_agent)

        if result["success"]:
            processed.append(result["data"])
        else:
            error_entry = {
                "index":   idx,
                "subject": email.get("subject", "(No subject)"),
                "error":   result["error"],
            }
            errors.append(error_entry)
            logger.warning(
                "process_emails_bulk: email[%d] failed — %s", idx, result["error"]
            )
            if not skip_on_error:
                return _build_response(success=False, error=result["error"])

    logger.info(
        "process_emails_bulk: %d/%d succeeded.", len(processed), len(emails)
    )
    return _build_response(
        success=True,
        data={
            "processed": processed,
            "errors":    errors,
            "total":     len(emails),
            "succeeded": len(processed),
            "failed":    len(errors),
        },
    )