from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

from backend.core.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentMetadataService:
    def __init__(self) -> None:
        mongo_uri = settings.MONGODB_URI.strip()
        database_name = settings.MONGODB_DATABASE.strip()

        if not mongo_uri:
            raise RuntimeError("MONGODB_URI is not configured")
        if not database_name:
            raise RuntimeError("MONGODB_DATABASE is not configured")

        self._client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
        )
        self._db = self._client[database_name]
        self._documents = self._db[settings.MONGODB_DOCUMENTS_COLLECTION]
        self._jobs = self._db[settings.MONGODB_INGESTION_JOBS_COLLECTION]
        self._chunks = self._db[settings.MONGODB_DOCUMENT_CHUNKS_COLLECTION]

        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._documents.create_index([("doc_id", ASCENDING)], unique=True)
        self._documents.create_index([("workspace_id", ASCENDING), ("status", ASCENDING)])
        self._documents.create_index([("owner_id", ASCENDING)])

        self._jobs.create_index([("job_id", ASCENDING)], unique=True)
        self._jobs.create_index([("doc_id", ASCENDING), ("status", ASCENDING)])

        self._chunks.create_index([("chunk_id", ASCENDING)], unique=True)
        self._chunks.create_index([("doc_id", ASCENDING), ("chunk_index", ASCENDING)], unique=True)
        self._chunks.create_index([("vector_id", ASCENDING)])

    def create_document(
        self,
        *,
        doc_id: str,
        workspace_id: int,
        owner_id: str | None,
        filename: str,
        mime_type: str,
        size_bytes: int,
        blob_path: str,
        content_hash: str,
        status: str = "processing",
        download_url: str | None = None,
    ) -> dict:
        document = {
            "doc_id": doc_id,
            "workspace_id": workspace_id,
            "owner_id": owner_id,
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "blob_path": blob_path,
            "download_url": download_url,
            "content_hash": content_hash,
            "status": status,
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        }

        try:
            self._documents.insert_one(document)
        except PyMongoError as exc:
            raise RuntimeError(f"Failed to save document metadata: {exc}") from exc

        return document

    def update_document(self, doc_id: str, updates: dict[str, Any]) -> None:
        if not updates:
            return

        updates = {key: value for key, value in updates.items() if value is not None}
        if not updates:
            return

        updates["updated_at"] = _utcnow()

        try:
            self._documents.update_one({"doc_id": doc_id}, {"$set": updates})
        except PyMongoError as exc:
            raise RuntimeError(f"Failed to update document metadata: {exc}") from exc

    def delete_document(self, doc_id: str) -> None:
        try:
            self._documents.delete_one({"doc_id": doc_id})
            self._jobs.delete_many({"doc_id": doc_id})
            self._chunks.delete_many({"doc_id": doc_id})
        except PyMongoError as exc:
            raise RuntimeError(f"Failed to delete document metadata: {exc}") from exc

    def create_ingestion_job(
        self,
        *,
        job_id: str,
        doc_id: str,
        status: str,
        chunk_count: int = 0,
        embedding_model: str = "",
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> dict:
        job = {
            "job_id": job_id,
            "doc_id": doc_id,
            "status": status,
            "chunk_count": chunk_count,
            "embedding_model": embedding_model,
            "error": error,
            "started_at": started_at or _utcnow(),
            "finished_at": finished_at,
        }

        try:
            self._jobs.insert_one(job)
        except PyMongoError as exc:
            raise RuntimeError(f"Failed to save ingestion job: {exc}") from exc

        return job

    def update_ingestion_job(self, job_id: str, updates: dict[str, Any]) -> None:
        if not updates:
            return

        updates = {key: value for key, value in updates.items() if value is not None}
        if not updates:
            return

        try:
            self._jobs.update_one({"job_id": job_id}, {"$set": updates})
        except PyMongoError as exc:
            raise RuntimeError(f"Failed to update ingestion job: {exc}") from exc

    def create_document_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return

        try:
            self._chunks.insert_many(chunks, ordered=False)
        except PyMongoError as exc:
            raise RuntimeError(f"Failed to save chunk metadata: {exc}") from exc