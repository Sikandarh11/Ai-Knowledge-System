from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.services.query_service import QueryService
from backend.storage.database import get_db
from backend.storage.schemas import DocumentRead

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str
    workspace_id: str | None = None


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


@router.post("", response_model=QueryResponse)
def search_documents(payload: QueryRequest, db: Session = Depends(get_db)):
    service = QueryService(db)
    try:
        result = service.search_documents(payload.query, workspace_id=payload.workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return QueryResponse(
        query=result["query"],
        workspace_id=result["workspace_id"],
        answer=result["answer"],
        documents=result["documents"],
        sources=result["sources"],
        used_llm=result["used_llm"],
    )
