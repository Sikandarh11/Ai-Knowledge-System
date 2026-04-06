from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.rag import RAGService
from backend.services.email import send_email_service

router = APIRouter(prefix="/chat", tags=["chat"])

# Module-level singleton — constructed once, reused across requests
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The question to answer.")
    history: list[dict] = []


class SourceDocument(BaseModel):
    id:           str
    text:         str
    distance:     float
    document_id:  int | None
    workspace_id: int | None


class ChatResponse(BaseModel):
    query:    str
    answer:   str
    sources:  list[SourceDocument]
    used_llm: bool


# ── Route ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """
    Run the full RAG pipeline for the given query.

    - Embeds the query
    - Retrieves the most relevant document chunks
    - Generates a grounded answer via gpt-4o-mini (or returns context fallback)
    """
    rag = get_rag_service()

    history = (payload.history or [])[-6:]
    conversation_lines: list[str] = []
    total_chars = 0

    for msg in history:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = msg.get("content")

        if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
            continue

        line = f"User: {content.strip()}" if role == "user" else f"Assistant: {content.strip()}"

        if total_chars + len(line) > 4000:
            break

        conversation_lines.append(line)
        total_chars += len(line)

    conversation_text = "\n".join(conversation_lines)

    if conversation_text:
        query_text = (
            "You are a helpful assistant.\n\n"
            "Conversation so far:\n"
            f"{conversation_text}\n\n"
            "Question:\n"
            f"{payload.query}"
        )
    else:
        query_text = payload.query

    try:
        result = rag.run(query=query_text)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"RAG pipeline failed: {str(exc)}",
        )

    sources = [SourceDocument(**hit) for hit in result["sources"]]

    return ChatResponse(
        query=result["query"],
        answer=result["answer"],
        sources=sources,
        used_llm=result["used_llm"],
    )

@router.post("/send-email")
def send_email_endpoint(payload: SendEmailRequest):
    return send_email_service(
        to=payload.to,
        subject=payload.subject,
        body=payload.body,
    )