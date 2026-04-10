from collections import Counter
import os
from uuid import UUID

from sqlalchemy.orm import Session

from backend.storage.models import Document
from backend.storage.models import Workspace
from backend.storage.repositories.document import DocumentRepository
from backend.rag.embedder import EmbeddingService
from backend.rag.pipeline import RAGService
from backend.rag.vector_store import VectorStore


class QueryService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = DocumentRepository(db)
        self._embedder = EmbeddingService()
        self._store = VectorStore()
        self._rag = RAGService()

    def _resolve_workspace_db_id(self, workspace_id: str | None) -> int | None:
        if workspace_id is None:
            return None

        value = workspace_id.strip()
        if not value:
            return None

        if value.isdigit():
            return int(value)

        try:
            parsed_uuid = UUID(value)
        except ValueError as exc:
            raise ValueError("Invalid workspace_id. Use workspace UUID or numeric id.") from exc

        workspace = self._db.query(Workspace).filter(Workspace.workspace_id == str(parsed_uuid)).first()
        if workspace is None:
            raise ValueError("Workspace not found")
        return int(workspace.id)

    def search_documents(self, query: str, workspace_id: str | None = None) -> dict:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        clean_query = query.strip()
        target_workspace_id = self._resolve_workspace_db_id(workspace_id)

        hits: list[dict] = []
        try:
            query_embedding = self._embedder.embed_text(clean_query)
            hits = self._store.query(
                query_embedding=query_embedding,
                workspace_id=target_workspace_id,
                n_results=8,
            )
        except Exception:
            hits = []

        inferred_workspace_id: int | None = target_workspace_id
        if inferred_workspace_id is None and hits:
            candidates = [hit.get("workspace_id") for hit in hits if isinstance(hit.get("workspace_id"), int)]
            if candidates:
                inferred_workspace_id = Counter(candidates).most_common(1)[0][0]

        if inferred_workspace_id is not None:
            workspace_hits = [
                hit for hit in hits if hit.get("workspace_id") == inferred_workspace_id
            ]
        else:
            workspace_hits = hits

        doc_ids_from_hits = [
            int(hit["document_id"])
            for hit in workspace_hits
            if isinstance(hit.get("document_id"), int)
        ]
        if doc_ids_from_hits:
            documents = self._repo.get_by_ids(doc_ids_from_hits, workspace_id=inferred_workspace_id)
        else:
            documents = self._repo.search(clean_query, workspace_id=inferred_workspace_id)

        prompt = self._rag.build_prompt(clean_query, workspace_hits)
        answer = self._rag.generate_answer(prompt)

        return {
            "query": clean_query,
            "workspace_id": inferred_workspace_id,
            "answer": answer,
            "documents": documents,
            "sources": workspace_hits,
            "used_llm": bool(os.getenv("OPENAI_API_KEY")),
        }
