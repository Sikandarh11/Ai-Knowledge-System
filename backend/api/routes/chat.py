from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.chat_service import ChatService
from backend.services.email_service import send_email_service

router = APIRouter(prefix="/chat", tags=["chat"])
_chat_service = ChatService()


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The question to answer.")
    history: list[dict] = []


class SourceDocument(BaseModel):
    id: str
    text: str
    distance: float
    document_id: int | None
    workspace_id: int | None


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceDocument]
    used_llm: bool


class SendEmailRequest(BaseModel):
    to: str = Field(..., description="Email recipient address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        result = _chat_service.chat(query=payload.query, history=payload.history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {str(exc)}") from exc

    sources = [SourceDocument(**hit) for hit in result["sources"]]
    return ChatResponse(
        query=result["query"],
        answer=result["answer"],
        sources=sources,
        used_llm=result["used_llm"],
    )


@router.post("/send-email")
def send_email_endpoint(payload: SendEmailRequest):
    return send_email_service(to=payload.to, subject=payload.subject, body=payload.body)
