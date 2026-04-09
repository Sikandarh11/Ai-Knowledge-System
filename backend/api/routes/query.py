from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.services.query_service import QueryService
from backend.storage.database import get_db
from backend.storage.schemas import DocumentRead

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str


@router.post("", response_model=list[DocumentRead])
def search_documents(payload: QueryRequest, db: Session = Depends(get_db)):
    service = QueryService(db)
    try:
        return service.search_documents(payload.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
