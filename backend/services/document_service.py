import os
import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.ingestion.extractor import extract_text
from backend.ingestion.uploader import handle_upload
from backend.rag.chunker import chunk_text
from backend.rag.embedder import EmbeddingService
from backend.rag.vector_store import VectorStore
from backend.services.blob_storage_service import BlobStorageService
from backend.services.document_metadata_service import DocumentMetadataService
from backend.storage.models import Document
from backend.storage.repositories.document import DocumentRepository
from backend.storage.repositories.workspace import WorkspaceRepository


class DocumentService:
    def __init__(self, db: Session):
        self._repo = DocumentRepository(db)
        self._workspace_repo = WorkspaceRepository(db)
        self._embedder = EmbeddingService()
        self._store = VectorStore(collection_name=self._embedder.collection_name())

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _sha256_file(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _approximate_token_count(text: str) -> int:
        return len(text.split()) if text.strip() else 0

    @staticmethod
    def _safe_blob_name(*, workspace_id: int, content_hash: str, filename: str) -> str:
        safe_filename = Path(filename).name or "document"
        return f"workspaces/{workspace_id}/documents/{content_hash[:16]}_{safe_filename}"

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
        workspace = self._workspace_repo.get_by_id(workspace_id)
        if workspace is None:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=404, detail="Workspace not found")

        blob_storage: BlobStorageService | None = None
        metadata_store: DocumentMetadataService | None = None
        blob_info: dict | None = None
        document: Document | None = None
        metadata_doc_id: str | None = None
        job_id = str(uuid4())
        vector_stage_started = False
        stage = "initialize"

        try:
            stage = "file-stats"
            size_bytes = os.path.getsize(file_path)
            content_hash = self._sha256_file(file_path)
            mime_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

            stage = "extract-text"
            text = extract_text(file_path, file_type)
            if not text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="No extractable text found. If this is a scanned/image PDF, OCR is required.",
                )

            stage = "chunk-text"
            chunks = chunk_text(text)
            if not chunks:
                raise HTTPException(status_code=400, detail="Chunking failed")

            normalized_type = file_type.lstrip(".").lower() or "txt"
            stage = "init-storage-services"
            blob_storage = BlobStorageService()
            metadata_store = DocumentMetadataService()
            blob_name = self._safe_blob_name(
                workspace_id=workspace_id,
                content_hash=content_hash,
                filename=filename,
            )

            stage = "upload-blob"
            blob_info = blob_storage.upload_file(
                file_path=file_path,
                blob_name=blob_name,
                content_type=mime_type,
            )

            stage = "persist-sql-document"
            document = self._repo.create(
                workspace_id=workspace_id,
                content=text,
                filename=filename,
                file_type=normalized_type,
                chunk_count=len(chunks),
            )

            metadata_doc_id = str(uuid4())
            stage = "persist-mongo-document"
            metadata_store.create_document(
                doc_id=metadata_doc_id,
                workspace_id=workspace_id,
                owner_id=workspace.owner_id,
                filename=filename,
                mime_type=mime_type,
                size_bytes=size_bytes,
                blob_path=blob_info["blob_path"],
                content_hash=content_hash,
                status="processing",
                download_url=blob_info.get("download_url"),
            )

            stage = "persist-mongo-job"
            metadata_store.create_ingestion_job(
                job_id=job_id,
                doc_id=metadata_doc_id,
                status="running",
                chunk_count=len(chunks),
                embedding_model=self._embedder.model_name,
            )

            vector_stage_started = True
            stage = "embed-chunks"
            embeddings = self._embedder.embed_batch(chunks)
            if len(embeddings) != len(chunks):
                raise HTTPException(status_code=500, detail="Embedding mismatch")

            chunk_ids = [str(uuid4()) for _ in chunks]
            ids = chunk_ids
            metadatas = [
                {
                    "chunk_id": chunk_ids[i],
                    "document_id": document.id,
                    "doc_id": metadata_doc_id,
                    "workspace_id": workspace_id,
                    "chunk_index": i,
                }
                for i, _ in enumerate(chunks)
            ]

            stage = "persist-vectors"
            self._store.add_documents(
                ids=ids,
                texts=chunks,
                embeddings=embeddings,
                metadata=metadatas,
            )

            stage = "persist-mongo-chunks"
            metadata_store.create_document_chunks(
                [
                    {
                        "chunk_id": chunk_ids[i],
                        "doc_id": metadata_doc_id,
                        "chunk_index": i,
                        "text_preview": chunk[:240],
                        "token_count": self._approximate_token_count(chunk),
                        "vector_id": chunk_ids[i],
                    }
                    for i, chunk in enumerate(chunks)
                ]
            )

            stage = "mark-indexed"
            metadata_store.update_document(metadata_doc_id, {"status": "indexed"})
            metadata_store.update_ingestion_job(
                job_id,
                {
                    "status": "done",
                    "chunk_count": len(chunks),
                    "finished_at": self._utcnow(),
                    "error": None,
                },
            )

            return {
                "message": "Document uploaded and processed",
                "document_id": document.id,
                "filename": document.filename,
                "file_type": document.file_type,
                "chunks": len(chunks),
                "storage": blob_info,
                "ingestion_job_id": job_id,
            }
        except HTTPException:
            if metadata_store is not None and metadata_doc_id is not None:
                try:
                    metadata_store.update_document(metadata_doc_id, {"status": "failed"})
                    metadata_store.update_ingestion_job(
                        job_id,
                        {
                            "status": "failed",
                            "error": "Validation failed",
                            "finished_at": self._utcnow(),
                        },
                    )
                except Exception:
                    pass
            raise
        except Exception as exc:
            if metadata_store is not None and metadata_doc_id is not None:
                try:
                    metadata_store.update_document(metadata_doc_id, {"status": "failed"})
                    metadata_store.update_ingestion_job(
                        job_id,
                        {
                            "status": "failed",
                            "error": str(exc),
                            "finished_at": self._utcnow(),
                        },
                    )
                except Exception:
                    pass

            if not vector_stage_started:
                if document is not None:
                    try:
                        self._repo.delete(document.id)
                    except Exception:
                        pass
                if blob_info is not None and blob_storage is not None:
                    try:
                        blob_storage.delete_blob(blob_info["blob_name"])
                    except Exception:
                        pass

            raise HTTPException(status_code=500, detail=f"{stage}: {exc}") from exc
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
