from collections import Counter
import time
from uuid import UUID

from sqlalchemy.orm import Session

from backend.rag.pipeline import RAGService
from backend.storage.repositories.chat import ChatRepository
from backend.storage.models import Workspace
from backend.storage.repositories.document import DocumentRepository


class ChatService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = DocumentRepository(db)
        self._chat_repo = ChatRepository(db)
        self._rag = RAGService()

    def resolve_workspace_db_id(self, workspace_id: str | None) -> int | None:
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

    @staticmethod
    def _normalize_history(history: list[dict] | None) -> tuple[list[str], int]:
        history = (history or [])[-6:]
        conversation_lines: list[str] = []
        total_chars = 0

        for msg in history:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = msg.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
                continue

            line = f"User: {content.strip()}" if role == "user" else f"Assistant: {content.strip()}"
            if total_chars + len(line) > 4000:
                break
            conversation_lines.append(line)
            total_chars += len(line)

        return conversation_lines, total_chars

    @staticmethod
    def _infer_workspace_id(hits: list[dict], preferred_workspace_id: int | None) -> int | None:
        if preferred_workspace_id is not None:
            return preferred_workspace_id

        candidates = [hit.get("workspace_id") for hit in hits if isinstance(hit.get("workspace_id"), int)]
        if not candidates:
            return None
        return Counter(candidates).most_common(1)[0][0]

    def run(
        self,
        *,
        query: str,
        workspace_id: str | None = None,
        history: list[dict] | None = None,
        mode: str | None = None,
        include_documents: bool = False,
    ) -> dict:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        started_at = time.perf_counter()
        clean_query = query.strip()
        resolved_workspace_id = self.resolve_workspace_db_id(workspace_id)
        history_lines, _ = self._normalize_history(history)
        has_history = bool(history_lines)
        effective_mode = (mode or ("chat" if has_history else "query")).strip().lower()

        retrieval_query = clean_query
        conversation_text = "\n".join(history_lines)
        if conversation_text:
            retrieval_query = (
                "You are a helpful assistant.\n\n"
                "Conversation so far:\n"
                f"{conversation_text}\n\n"
                "Question:\n"
                f"{clean_query}"
            )

        retrieval_started = time.perf_counter()
        rag_result = self._rag.run(
            query=retrieval_query,
            workspace_id=resolved_workspace_id,
            conversation=conversation_text,
        )
        retrieval_duration_ms = (time.perf_counter() - retrieval_started) * 1000

        sources = rag_result.get("sources", [])
        inferred_workspace_id = self._infer_workspace_id(sources, resolved_workspace_id)

        documents = []
        if include_documents:
            doc_ids = [
                int(hit["document_id"])
                for hit in sources
                if isinstance(hit.get("document_id"), int)
            ]
            if doc_ids:
                documents = self._repo.get_by_ids(doc_ids, workspace_id=inferred_workspace_id)
            else:
                documents = self._repo.search(clean_query, workspace_id=inferred_workspace_id)

        total_duration_ms = (time.perf_counter() - started_at) * 1000

        return {
            "query": clean_query,
            "answer": rag_result["answer"],
            "workspace_id": inferred_workspace_id,
            "sources": sources,
            "documents": documents,
            "used_llm": rag_result["used_llm"],
            "metadata": {
                "mode": effective_mode,
                "retrieved_count": len(sources),
                "model_name": rag_result.get("model_name", self._rag.model_name),
                "timings_ms": {
                    "retrieval_and_generation": round(retrieval_duration_ms, 2),
                    "total": round(total_duration_ms, 2),
                },
            },
        }

    def chat(self, query: str, history: list[dict] | None = None, workspace_id: str | None = None) -> dict:
        return self.run(query=query, workspace_id=workspace_id, history=history, mode="chat", include_documents=False)

    def save_turn(
        self,
        *,
        user_id: str,
        workspace_id: int,
        query: str,
        answer: str,
        sources: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> None:
        self._chat_repo.create_message(
            user_id=user_id,
            workspace_id=workspace_id,
            role="user",
            content=query,
        )
        self._chat_repo.create_message(
            user_id=user_id,
            workspace_id=workspace_id,
            role="assistant",
            content=answer,
            sources=sources or [],
            metadata=metadata or {},
        )

    def get_history(self, *, user_id: str, workspace_id: int, limit: int = 200) -> list[dict]:
        messages = self._chat_repo.list_messages(user_id=user_id, workspace_id=workspace_id, limit=limit)
        return [self._chat_repo.serialize_message(message) for message in messages]

    def clear_history(self, *, user_id: str, workspace_id: int) -> int:
        return self._chat_repo.clear_messages(user_id=user_id, workspace_id=workspace_id)
