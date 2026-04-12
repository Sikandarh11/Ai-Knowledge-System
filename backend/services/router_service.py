from __future__ import annotations

from functools import partial
import re
from typing import Any

from anyio import to_thread
from sqlalchemy.orm import Session

from backend.agents.scheduling_agent import SchedulingAgent
from backend.agents.email_agent import EmailCommandAgent
from backend.services import chat_service, email_service, query_service, workspace_service
from backend.storage.database import SessionLocal


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
        if intent in {"send_email", "email"}:
            recipient_name = params.get("recipient_name") or params.get("to_name") or params.get("to")
            subject_value = params.get("subject") or "No Subject"
            body_value = params.get("body")
            user_id = params.get("user_id") or "default-user"

            missing_fields: list[str] = []
            if not recipient_name:
                missing_fields.append("recipient_name")
            if not body_value:
                missing_fields.append("body")
            if missing_fields:
                return _build_error_response(
                    "email",
                    "Email intent is missing required params from LLM output: "
                    + ", ".join(missing_fields),
                )

            explicit_email = _extract_first_email(str(recipient_name))
            if explicit_email:
                send_result = await _run_sync_callable(
                    email_service.send_email_service,
                    to=explicit_email,
                    subject=str(subject_value),
                    body=str(body_value),
                )
                return {
                    "type": "send_email",
                    "status": "success" if send_result.get("success") else "error",
                    "message": (
                        f"Email sent to {explicit_email}"
                        if send_result.get("success")
                        else (send_result.get("error") or "Email send failed.")
                    ),
                    "data": send_result,
                }

            agent = EmailCommandAgent()
            result = await _run_sync_callable(
                agent.handle_send_email_request,
                recipient_name=str(recipient_name),
                subject=str(subject_value),
                body=str(body_value),
                user_id=str(user_id),
            )
            return {
                "type": "send_email",
                "status": "success" if result.get("type") != "error" else "error",
                "message": result.get("message") or "Email intent processed.",
                "data": result,
            }
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
