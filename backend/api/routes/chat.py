import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.agents.email_agent import EmailCommandAgent
from backend.services.router_service import route_intent
from backend.services.chat_service import ChatService
from backend.services.email_service import send_email_service
from backend.storage.database import get_db
from backend.storage.schemas import DocumentRead

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
    return lowered.startswith("send email") or lowered.startswith("email ")


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


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    query_text = payload.query.strip()

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

        return _build_chat_response_from_router(
            query=query_text,
            route_result=route_result,
            workspace_id=workspace_int,
        )

    service = ChatService(db)
    try:
        result = service.run(
            query=query_text,
            workspace_id=payload.workspace_id,
            history=payload.history,
            mode=payload.mode,
            include_documents=payload.include_documents,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {str(exc)}") from exc

    sources = [SourceDocument(**hit) for hit in result["sources"]]
    return ChatResponse(
        query=result["query"],
        answer=result["answer"],
        workspace_id=result["workspace_id"],
        sources=sources,
        documents=result["documents"] if payload.include_documents else None,
        used_llm=result["used_llm"],
        metadata=result["metadata"],
    )


@router.post("/send-email")
def send_email_endpoint(payload: SendEmailRequest):
    return send_email_service(to=payload.to, subject=payload.subject, body=payload.body)
