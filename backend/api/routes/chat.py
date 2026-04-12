from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

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


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    service = ChatService(db)
    try:
        result = service.run(
            query=payload.query,
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
