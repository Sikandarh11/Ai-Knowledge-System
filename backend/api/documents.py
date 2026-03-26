from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend import crud, schemas
from backend.db import get_db
from backend.embeddings import EmbeddingService
from backend.vector_store import VectorStore

from fastapi import UploadFile, File, Form

from backend.ingestion.uploader import handle_upload
from backend.ingestion.extractor import extract_text
from backend.ingestion.chunker import chunk_text

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

@router.post("/upload")
def upload_document_file(
    workspace_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        embedder = get_embedding_service()
        store = get_vector_store()

        # -------------------------
        # 1. Upload file
        # -------------------------
        upload_info = handle_upload(file)

        file_path = upload_info["file_path"]
        file_type = upload_info["file_type"]
        filename = upload_info["filename"]

        # -------------------------
        # 2. Extract text
        # -------------------------
        text = extract_text(file_path, file_type)

        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty document")

        # -------------------------
        # 3. Store full document in DB
        # -------------------------
        document = crud.create_document(
            db,
            workspace_id=workspace_id,
            content=text,
        )

        # -------------------------
        # 4. Chunk text
        # -------------------------
        chunks = chunk_text(text)

        if not chunks:
            raise HTTPException(status_code=400, detail="Chunking failed")

        # -------------------------
        # 5. Generate embeddings
        # -------------------------
        embeddings = embedder.embed_batch(chunks)

        # -------------------------
        # 6. Store in vector DB
        # -------------------------
        ids = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            ids.append(f"doc_{document.id}_chunk_{i}")

            metadatas.append({
                "document_id": document.id,
                "workspace_id": workspace_id,
                "chunk_index": i,
                "filename": filename,
            })

        store.add_documents(
            ids=ids,
            texts=chunks,
            embeddings=embeddings,
            metadata=metadatas,
        )

        # -------------------------
        # 7. Cleanup temp file
        # -------------------------
        import os
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "message": "Document uploaded and processed",
            "document_id": document.id,
            "chunks": len(chunks),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))