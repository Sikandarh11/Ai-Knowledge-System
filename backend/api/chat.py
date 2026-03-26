from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.rag import RAGService


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

    try:
        result = rag.run(query=payload.query)
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