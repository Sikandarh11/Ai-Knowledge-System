import os

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.ingestion.extractor import extract_text
from backend.ingestion.uploader import handle_upload
from backend.rag.chunker import chunk_text
from backend.rag.embedder import EmbeddingService
from backend.rag.vector_store import VectorStore
from backend.storage.models import Document
from backend.storage.repositories.document import DocumentRepository


class DocumentService:
    def __init__(self, db: Session):
        self._repo = DocumentRepository(db)
        self._embedder = EmbeddingService()
        self._store = VectorStore(collection_name=self._embedder.collection_name())

    def create_document(self, *, workspace_id: int, content: str) -> Document:
        document = self._repo.create(
            workspace_id=workspace_id,
            content=content,
            filename="text_input.txt",
            file_type="txt",
            chunk_count=1 if content.strip() else 0,
        )

        try:
            embedding = self._embedder.embed_text(document.content)
            self._store.add_documents(
                ids=[f"doc_{document.id}_chunk_0"],
                texts=[document.content],
                embeddings=[embedding],
                metadata=[
                    {
                        "document_id": document.id,
                        "workspace_id": document.workspace_id,
                        "chunk_index": 0,
                        "filename": "text_input",
                    }
                ],
            )
        except Exception:
            # Vector indexing must not block relational persistence.
            pass

        return document

    def delete_document(self, document_id: int) -> bool:
        document = self._repo.get(document_id)
        if document is None:
            return False

        try:
            self._store.delete_document(document_id)
        except Exception:
            pass

        return self._repo.delete(document_id)

    def list_documents(self, workspace_id: int) -> list[Document]:
        return self._repo.list_by_workspace(workspace_id)

    async def upload_document_file(self, *, workspace_id: int, file: UploadFile) -> dict:
        upload_info = await handle_upload(file)

        file_path = upload_info["file_path"]
        file_type = upload_info["file_type"]
        filename = upload_info.get("filename") or file.filename or "unknown"

        try:
            text = extract_text(file_path, file_type)
            if not text.strip():
                raise HTTPException(status_code=400, detail="Empty document")

            chunks = chunk_text(text)
            if not chunks:
                raise HTTPException(status_code=400, detail="Chunking failed")

            normalized_type = file_type.lstrip(".").lower() or "txt"
            document = self._repo.create(
                workspace_id=workspace_id,
                content=text,
                filename=filename,
                file_type=normalized_type,
                chunk_count=len(chunks),
            )

            embeddings = self._embedder.embed_batch(chunks)
            if len(embeddings) != len(chunks):
                raise HTTPException(status_code=500, detail="Embedding mismatch")

            ids = [f"doc_{document.id}_chunk_{i}" for i, _ in enumerate(chunks)]
            metadatas = [
                {
                    "document_id": document.id,
                    "workspace_id": workspace_id,
                    "chunk_index": i,
                    "filename": filename,
                }
                for i, _ in enumerate(chunks)
            ]

            self._store.add_documents(
                ids=ids,
                texts=chunks,
                embeddings=embeddings,
                metadata=metadatas,
            )

            return {
                "message": "Document uploaded and processed",
                "document_id": document.id,
                "filename": document.filename,
                "file_type": document.file_type,
                "chunks": len(chunks),
            }
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
