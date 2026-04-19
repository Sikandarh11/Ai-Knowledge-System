import re
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.agents.email_agent import EmailCommandAgent
from backend.core.auth import get_current_user
from backend.services.intent_service import extract_intent, IntentExtractionError
from backend.services.router_service import route_intent
from backend.services.chat_service import ChatService, GLOBAL_CHAT_WORKSPACE_TOKEN
from backend.services.email_service import send_email_service
from backend.storage.database import get_db
from backend.storage.models import User
from backend.storage.schemas import DocumentRead
from backend.storage.schemas import ChatMessageRead

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The question to answer.")
    workspace_id: str | None = None
    history: list[dict] = Field(default_factory=list)
    mode: str | None = None
    include_documents: bool = False


class SourceDocument(BaseModel):
    id: str
    text: str
    distance: float
    document_id: int | None
    workspace_id: int | None


class ChatResponse(BaseModel):
    query: str
    answer: str
    workspace_id: int | None
    sources: list[SourceDocument]
    documents: list[DocumentRead] | None = None
    used_llm: bool
    metadata: dict


class SendEmailRequest(BaseModel):
    to: str = Field(..., description="Email recipient address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")


def _extract_email_address(text: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0).strip() if match else None


def _looks_like_send_email_command(text: str) -> bool:
    lowered = (text or "").strip().lower()
    return bool(
        re.match(r"^(please\s+)?send\s+(an?\s+)?email\b", lowered)
        or lowered.startswith("email ")
    )


def _build_chat_response_from_router(
    query: str,
    route_result: dict,
    workspace_id: int | None,
) -> ChatResponse:
    metadata = {
        "mode": "agent-router",
        "router": route_result,
    }
    return ChatResponse(
        query=query,
        answer=str(route_result.get("message") or "Action processed."),
        workspace_id=workspace_id,
        sources=[],
        documents=None,
        used_llm=False,
        metadata=metadata,
    )


def _should_route_via_agent(intent_json: dict | None) -> bool:
    if not isinstance(intent_json, dict):
        return False
    intent = str(intent_json.get("intent") or "").strip().lower()
    return intent in {"schedule", "send_email", "workspace", "query"}


async def _route_text_if_needed(query_text: str) -> dict | None:
    try:
        intent_json = await extract_intent(query_text)
    except IntentExtractionError:
        return None
    except Exception:
        return None

    if not _should_route_via_agent(intent_json):
        return None

    return await route_intent(intent_json, query_text)


def _to_sse(data: dict, event: str | None = None) -> str:
    payload = json.dumps(data, ensure_ascii=True)
    if event:
        return f"event: {event}\ndata: {payload}\n\n"
    return f"data: {payload}\n\n"


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    query_text = payload.query.strip()
    service = ChatService(db)
    user_id = str(current_user.id)
    is_global_chat = (payload.workspace_id or "").strip() == GLOBAL_CHAT_WORKSPACE_TOKEN

    if _looks_like_send_email_command(query_text):
        parser = EmailCommandAgent()
        parsed = parser.parse_send_email_command(query_text)
        explicit_email = _extract_email_address(query_text)
        recipient_name = str(parsed.get("recipient_name") or "").strip()
        body_text = str(parsed.get("body") or query_text).strip()
        subject_text = str(parsed.get("subject") or "No Subject").strip()

        if explicit_email:
            intent_json = {
                "intent": "send_email",
                "action": "send",
                "params": {
                    "recipient_name": explicit_email,
                    "subject": subject_text,
                    "body": body_text,
                    "user_id": "default-user",
                },
            }
        else:
            intent_json = {
                "intent": "send_email",
                "action": "send",
                "params": {
                    "recipient_name": recipient_name,
                    "subject": subject_text,
                    "body": body_text,
                    "user_id": "default-user",
                },
            }

        route_result = await route_intent(intent_json, query_text)

        workspace_int: int | None = None
        if payload.workspace_id and payload.workspace_id.strip().isdigit():
            workspace_int = int(payload.workspace_id.strip())

        chat_response = _build_chat_response_from_router(
            query=query_text,
            route_result=route_result,
            workspace_id=None if is_global_chat else workspace_int,
        )

        storage_workspace_id = service.resolve_workspace_db_id(
            payload.workspace_id,
            user_id=user_id,
            create_if_missing=is_global_chat,
        )
        if storage_workspace_id is None:
            storage_workspace_id = chat_response.workspace_id
        if storage_workspace_id is not None:
            service.save_turn(
                user_id=user_id,
                workspace_id=storage_workspace_id,
                query=query_text,
                answer=chat_response.answer,
                sources=[],
                metadata=chat_response.metadata,
            )
        return chat_response

    route_result = await _route_text_if_needed(query_text)
    if route_result is not None:
        workspace_int: int | None = None
        if payload.workspace_id and payload.workspace_id.strip().isdigit():
            workspace_int = int(payload.workspace_id.strip())

        chat_response = _build_chat_response_from_router(
            query=query_text,
            route_result=route_result,
            workspace_id=None if is_global_chat else workspace_int,
        )

        storage_workspace_id = service.resolve_workspace_db_id(
            payload.workspace_id,
            user_id=user_id,
            create_if_missing=is_global_chat,
        )
        if storage_workspace_id is None:
            storage_workspace_id = chat_response.workspace_id
        if storage_workspace_id is not None:
            service.save_turn(
                user_id=user_id,
                workspace_id=storage_workspace_id,
                query=query_text,
                answer=chat_response.answer,
                sources=[],
                metadata=chat_response.metadata,
            )
        return chat_response

    try:
        result = service.run(
            query=query_text,
            workspace_id=None if is_global_chat else payload.workspace_id,
            history=payload.history,
            mode=payload.mode,
            include_documents=payload.include_documents,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {str(exc)}") from exc

    sources = [SourceDocument(**hit) for hit in result["sources"]]
    chat_response = ChatResponse(
        query=result["query"],
        answer=result["answer"],
        workspace_id=result["workspace_id"],
        sources=sources,
        documents=result["documents"] if payload.include_documents else None,
        used_llm=result["used_llm"],
        metadata=result["metadata"],
    )

    storage_workspace_id = service.resolve_workspace_db_id(
        payload.workspace_id,
        user_id=user_id,
        create_if_missing=is_global_chat,
    )
    if storage_workspace_id is None:
        storage_workspace_id = chat_response.workspace_id
    if storage_workspace_id is not None:
        service.save_turn(
            user_id=user_id,
            workspace_id=storage_workspace_id,
            query=query_text,
            answer=chat_response.answer,
            sources=[source.model_dump() for source in sources],
            metadata=chat_response.metadata,
        )

    return chat_response


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query_text = payload.query.strip()
    service = ChatService(db)
    user_id = str(current_user.id)
    is_global_chat = (payload.workspace_id or "").strip() == GLOBAL_CHAT_WORKSPACE_TOKEN

    if _looks_like_send_email_command(query_text):
        parser = EmailCommandAgent()
        parsed = parser.parse_send_email_command(query_text)
        explicit_email = _extract_email_address(query_text)
        recipient_name = str(parsed.get("recipient_name") or "").strip()
        body_text = str(parsed.get("body") or query_text).strip()
        subject_text = str(parsed.get("subject") or "No Subject").strip()

        if explicit_email:
            intent_json = {
                "intent": "send_email",
                "action": "send",
                "params": {
                    "recipient_name": explicit_email,
                    "subject": subject_text,
                    "body": body_text,
                    "user_id": "default-user",
                },
            }
        else:
            intent_json = {
                "intent": "send_email",
                "action": "send",
                "params": {
                    "recipient_name": recipient_name,
                    "subject": subject_text,
                    "body": body_text,
                    "user_id": "default-user",
                },
            }

        route_result = await route_intent(intent_json, query_text)

        workspace_int: int | None = None
        if payload.workspace_id and payload.workspace_id.strip().isdigit():
            workspace_int = int(payload.workspace_id.strip())

        chat_response = _build_chat_response_from_router(
            query=query_text,
            route_result=route_result,
            workspace_id=None if is_global_chat else workspace_int,
        )

        storage_workspace_id = service.resolve_workspace_db_id(
            payload.workspace_id,
            user_id=user_id,
            create_if_missing=is_global_chat,
        )
        if storage_workspace_id is None:
            storage_workspace_id = chat_response.workspace_id
        if storage_workspace_id is not None:
            service.save_turn(
                user_id=user_id,
                workspace_id=storage_workspace_id,
                query=query_text,
                answer=chat_response.answer,
                sources=[],
                metadata=chat_response.metadata,
            )

        def _single_event_stream():
            yield _to_sse({"type": "chunk", "content": chat_response.answer})
            yield _to_sse(
                {
                    "type": "final",
                    "payload": {
                        "query": chat_response.query,
                        "answer": chat_response.answer,
                        "workspace_id": chat_response.workspace_id,
                        "sources": [],
                        "documents": None,
                        "used_llm": chat_response.used_llm,
                        "metadata": chat_response.metadata,
                    },
                }
            )

        return StreamingResponse(_single_event_stream(), media_type="text/event-stream")

    route_result = await _route_text_if_needed(query_text)
    if route_result is not None:
        workspace_int: int | None = None
        if payload.workspace_id and payload.workspace_id.strip().isdigit():
            workspace_int = int(payload.workspace_id.strip())

        chat_response = _build_chat_response_from_router(
            query=query_text,
            route_result=route_result,
            workspace_id=None if is_global_chat else workspace_int,
        )

        storage_workspace_id = service.resolve_workspace_db_id(
            payload.workspace_id,
            user_id=user_id,
            create_if_missing=is_global_chat,
        )
        if storage_workspace_id is None:
            storage_workspace_id = chat_response.workspace_id
        if storage_workspace_id is not None:
            service.save_turn(
                user_id=user_id,
                workspace_id=storage_workspace_id,
                query=query_text,
                answer=chat_response.answer,
                sources=[],
                metadata=chat_response.metadata,
            )

        def _single_event_stream():
            yield _to_sse({"type": "chunk", "content": chat_response.answer})
            yield _to_sse(
                {
                    "type": "final",
                    "payload": {
                        "query": chat_response.query,
                        "answer": chat_response.answer,
                        "workspace_id": chat_response.workspace_id,
                        "sources": [],
                        "documents": None,
                        "used_llm": chat_response.used_llm,
                        "metadata": chat_response.metadata,
                    },
                }
            )

        return StreamingResponse(_single_event_stream(), media_type="text/event-stream")

    try:
        stream = service.run_stream(
            query=query_text,
            workspace_id=None if is_global_chat else payload.workspace_id,
            history=payload.history,
            mode=payload.mode,
            include_documents=payload.include_documents,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _stream_events():
        final_payload: dict | None = None
        try:
            for event in stream:
                if event.get("type") == "final":
                    final_payload = event.get("payload") if isinstance(event.get("payload"), dict) else None
                yield _to_sse(event)
        except Exception as exc:
            yield _to_sse({"type": "error", "message": f"RAG pipeline failed: {str(exc)}"})
            return

        if final_payload is None:
            return

        sources = final_payload.get("sources") if isinstance(final_payload.get("sources"), list) else []
        storage_workspace_id = service.resolve_workspace_db_id(
            payload.workspace_id,
            user_id=user_id,
            create_if_missing=is_global_chat,
        )
        if storage_workspace_id is None and isinstance(final_payload.get("workspace_id"), int):
            storage_workspace_id = int(final_payload["workspace_id"])

        if storage_workspace_id is not None:
            service.save_turn(
                user_id=user_id,
                workspace_id=storage_workspace_id,
                query=query_text,
                answer=str(final_payload.get("answer") or ""),
                sources=sources,
                metadata=final_payload.get("metadata") if isinstance(final_payload.get("metadata"), dict) else {},
            )

    return StreamingResponse(_stream_events(), media_type="text/event-stream")


@router.post("/send-email")
def send_email_endpoint(payload: SendEmailRequest):
    return send_email_service(to=payload.to, subject=payload.subject, body=payload.body)


@router.get("/history", response_model=list[ChatMessageRead])
def get_chat_history(
    workspace_id: str | None = Query(
        default=GLOBAL_CHAT_WORKSPACE_TOKEN,
        description="Workspace id/uuid. Leave empty to use global chat history.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ChatService(db)
    requested_workspace = workspace_id or GLOBAL_CHAT_WORKSPACE_TOKEN
    resolved_workspace_id = service.resolve_workspace_db_id(
        requested_workspace,
        user_id=str(current_user.id),
        create_if_missing=requested_workspace.strip() == GLOBAL_CHAT_WORKSPACE_TOKEN,
    )
    if resolved_workspace_id is None:
        raise HTTPException(status_code=400, detail="workspace_id is required")

    return [
        ChatMessageRead(**message)
        for message in service.get_history(user_id=str(current_user.id), workspace_id=resolved_workspace_id)
    ]


@router.delete("/history")
def clear_chat_history(
    workspace_id: str | None = Query(
        default=GLOBAL_CHAT_WORKSPACE_TOKEN,
        description="Workspace id/uuid. Leave empty to clear global chat history.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ChatService(db)
    requested_workspace = workspace_id or GLOBAL_CHAT_WORKSPACE_TOKEN
    resolved_workspace_id = service.resolve_workspace_db_id(
        requested_workspace,
        user_id=str(current_user.id),
        create_if_missing=requested_workspace.strip() == GLOBAL_CHAT_WORKSPACE_TOKEN,
    )
    if resolved_workspace_id is None:
        raise HTTPException(status_code=400, detail="workspace_id is required")

    deleted = service.clear_history(user_id=str(current_user.id), workspace_id=resolved_workspace_id)
    return {"message": "Chat history cleared", "deleted": deleted}
