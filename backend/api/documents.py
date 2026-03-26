from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend import crud, schemas
from backend.db import get_db
from backend.embeddings import EmbeddingService
from backend.vector_store import VectorStore

router = APIRouter(prefix="/documents", tags=["documents"])

# Module-level singletons
_embedding_service: EmbeddingService | None = None
_vector_store: VectorStore | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=schemas.DocumentRead)
def create_document(payload: schemas.DocumentCreate, db: Session = Depends(get_db)):
    # 1. Persist to relational DB
    document = crud.create_document(
        db,
        workspace_id=payload.workspace_id,
        content=payload.content,
    )

    # 2. Embed and store in vector DB
    try:
        embedder = get_embedding_service()
        store    = get_vector_store()

        embedding = embedder.embed_text(document.content)

        store.add_documents(
            ids        = [f"doc_{document.id}_chunk_0"],
            texts      = [document.content],
            embeddings = [embedding],
            metadata   = [
                {
                    "document_id":  document.id,
                    "workspace_id": document.workspace_id,
                }
            ],
        )
    except Exception as exc:
        # Vector DB failure must not roll back the relational write
        print(f"[vector_store] Failed to index document {document.id}: {exc}")

    return document


@router.get("", response_model=list[schemas.DocumentRead])
def list_documents(workspace_id: int, db: Session = Depends(get_db)):
    return crud.get_documents_by_workspace(db, workspace_id=workspace_id)