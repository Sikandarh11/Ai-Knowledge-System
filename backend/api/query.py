from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .. import crud, schemas
from ..db import get_db

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str


@router.post("", response_model=list[schemas.DocumentRead])
def search_documents(payload: QueryRequest, db: Session = Depends(get_db)):
    return crud.search_documents(db, query=payload.query)