from __future__ import annotations

from functools import partial
import re
from typing import Any

from anyio import to_thread
from sqlalchemy.orm import Session

from backend.agents.scheduling_agent import SchedulingAgent
from backend.services import chat_service, email_service, query_service, workspace_service
from backend.storage.database import SessionLocal
from backend.storage.models import Document, User


def _build_response(intent: str, result: Any) -> dict[str, Any]:
    return {
        "type": intent,
        "status": "success",
        "message": "Action completed successfully",
        "data": result,
    }


def _build_error_response(intent: str, message: str) -> dict[str, Any]:
    return {
        "type": intent or "unknown",
        "status": "error",
        "message": message,
        "data": {},
    }


def _create_workspace_sync(params: dict[str, Any]) -> Any:
    db: Session = SessionLocal()
    try:
        service = workspace_service.WorkspaceService(db)
        workspace_name = params.get("name")
        workspace_type = params.get("workspace_type") or params.get("type") or "Work"
        description = params.get("description")
        owner_id = params.get("owner_id")
        workspace = service.create_workspace(
            name=workspace_name,
            workspace_type=workspace_type,
            description=description,
            owner_id=owner_id,
        )
        return {
            "workspace_id": getattr(workspace, "workspace_id", None),
            "name": getattr(workspace, "name", workspace_name),
            "type": getattr(workspace, "type", workspace_type),
            "description": getattr(workspace, "description", description),
        }
    finally:
        db.close()


def _search_query_sync(raw_text: str) -> Any:
    db: Session = SessionLocal()
    try:
        service = query_service.QueryService(db)
        return service.search_documents(raw_text)
    finally:
        db.close()


def _chat_sync(raw_text: str) -> Any:
    db: Session = SessionLocal()
    try:
        service = chat_service.ChatService(db)
        return service.chat(raw_text)
    finally:
        db.close()


def _schedule_sync(raw_text: str) -> Any:
    agent = SchedulingAgent()
    return agent.run(raw_text)


def _extract_first_email(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0).strip() if match else None


def _resolve_recipient_email_sync(recipient: str, params: dict[str, Any]) -> str | None:
    db: Session = SessionLocal()
    try:
        candidate = recipient.strip()
        if "@" in candidate:
            return candidate

        lowered = candidate.lower()

        # 1) Try user table: exact local-part or fuzzy email match
        users = db.query(User).all()
        for user in users:
            email = (user.email or "").strip()
            if not email:
                continue
            local_part = email.split("@", 1)[0].lower()
            if lowered == local_part or lowered in local_part or lowered in email.lower():
                return email

        # 2) Try workspace documents for named contact entries
        workspace_id = params.get("workspace_id")
        documents_query = db.query(Document)
        if isinstance(workspace_id, int):
            documents_query = documents_query.filter(Document.workspace_id == workspace_id)

        for document in documents_query.all():
            content = document.content or ""
            if lowered in content.lower():
                extracted = _extract_first_email(content)
                if extracted:
                    return extracted

        return None
    finally:
        db.close()


async def _run_sync_callable(callable_obj: Any, *args: Any, **kwargs: Any) -> Any:
    return await to_thread.run_sync(partial(callable_obj, *args, **kwargs))


async def route_intent(intent_json: dict, raw_text: str) -> dict:
    intent = (intent_json.get("intent") or "").lower()
    params = intent_json.get("params", {})

    try:
        if intent == "schedule":
            result = await _run_sync_callable(_schedule_sync, raw_text)
            status = "success" if result.get("success", False) else "error"
            return {
                "type": "schedule",
                "status": status,
                "message": result.get("message") or "Scheduling request processed.",
                "data": result,
            }
        if intent == "email":
            to_value = params.get("to")
            subject_value = params.get("subject")
            body_value = params.get("body")

            missing_fields: list[str] = []
            if not to_value:
                missing_fields.append("to")
            if not subject_value:
                missing_fields.append("subject")
            if not body_value:
                missing_fields.append("body")

            if missing_fields:
                return _build_error_response(
                    "email",
                    "Email intent is missing required params from LLM output: "
                    + ", ".join(missing_fields),
                )

            resolved_email = await _run_sync_callable(_resolve_recipient_email_sync, str(to_value), params)
            if not resolved_email:
                return _build_error_response(
                    "email",
                    f"Could not find an email for recipient '{to_value}' in users/documents.",
                )

            if hasattr(email_service, "send_email_service"):
                result = await _run_sync_callable(
                    email_service.send_email_service,
                    to=resolved_email,
                    subject=str(subject_value),
                    body=str(body_value),
                )
                message = f"Email sent to {resolved_email}"
                return {
                    "type": "email",
                    "status": "success" if result.get("success") else "error",
                    "message": message if result.get("success") else (result.get("error") or "Email send failed."),
                    "data": result,
                }
            return _build_error_response("email", "No email sender function is available.")
        elif intent == "workspace":
            result = await _run_sync_callable(_create_workspace_sync, params)
        elif intent == "query":
            if hasattr(query_service, "search"):
                result = await _run_sync_callable(query_service.search, raw_text)
            else:
                result = await _run_sync_callable(_search_query_sync, raw_text)
        else:
            if hasattr(chat_service, "chat"):
                result = await _run_sync_callable(chat_service.chat, raw_text)
            else:
                result = await _run_sync_callable(_chat_sync, raw_text)
            intent = "chat"
    except Exception as exc:  # noqa: BLE001
        return _build_error_response(intent, f"Routing failed: {exc}")

    return _build_response(intent, result)


__all__ = ["route_intent"]
