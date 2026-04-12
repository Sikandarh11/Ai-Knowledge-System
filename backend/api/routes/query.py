from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.services.chat_service import ChatService
from backend.storage.database import get_db
from backend.storage.schemas import DocumentRead

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str
    workspace_id: str | None = None
    history: list[dict] = Field(default_factory=list)
    mode: str | None = None
    include_documents: bool = True


class QuerySource(BaseModel):
    id: str
    text: str
    distance: float
    document_id: int | None
    workspace_id: int | None


class QueryResponse(BaseModel):
    query: str
    workspace_id: int | None
    answer: str
    documents: list[DocumentRead]
    sources: list[QuerySource]
    used_llm: bool
    metadata: dict


@router.post("", response_model=QueryResponse, deprecated=True)
def search_documents(payload: QueryRequest, db: Session = Depends(get_db)):
    service = ChatService(db)
    try:
        result = service.run(
            query=payload.query,
            workspace_id=payload.workspace_id,
            history=payload.history,
            mode=payload.mode or "query",
            include_documents=payload.include_documents,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return QueryResponse(
        query=result["query"],
        workspace_id=result["workspace_id"],
        answer=result["answer"],
        documents=result["documents"] or [],
        sources=result["sources"],
        used_llm=result["used_llm"],
        metadata=result["metadata"],
    )
