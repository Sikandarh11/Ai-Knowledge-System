import json

from sqlalchemy.orm import Session

from backend.storage.models import ChatMessage


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _dump_json(value) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _load_json(value, default):
        if not value:
            return default
        try:
            return json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return default

    def create_message(
        self,
        *,
        user_id: str,
        workspace_id: int,
        role: str,
        content: str,
        sources: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
            content=content,
            sources_json=self._dump_json(sources or []),
            metadata_json=self._dump_json(metadata or {}),
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_messages(self, *, user_id: str, workspace_id: int, limit: int = 200) -> list[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id, ChatMessage.workspace_id == workspace_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .limit(limit)
            .all()
        )

    def clear_messages(self, *, user_id: str, workspace_id: int) -> int:
        deleted = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id, ChatMessage.workspace_id == workspace_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return int(deleted or 0)

    def serialize_message(self, message: ChatMessage) -> dict:
        sources = self._load_json(message.sources_json, [])
        normalized_sources = []
        for index, source in enumerate(sources if isinstance(sources, list) else []):
            if not isinstance(source, dict):
                continue

            distance = source.get("distance")
            relevance = source.get("relevance")
            if isinstance(relevance, (int, float)):
                normalized_relevance = float(relevance)
            elif isinstance(distance, (int, float)):
                normalized_relevance = 1 / (1 + max(0.0, float(distance)))
            else:
                normalized_relevance = 0.0

            normalized_sources.append(
                {
                    "filename": source.get("filename") or f"Source {index + 1}",
                    "chunk_index": source.get("chunk_index") if isinstance(source.get("chunk_index"), int) else index,
                    "relevance": normalized_relevance,
                }
            )

        return {
            "id": message.id,
            "user_id": message.user_id,
            "workspace_id": message.workspace_id,
            "role": message.role,
            "content": message.content,
            "sources": normalized_sources,
            "metadata": self._load_json(message.metadata_json, {}),
            "created_at": message.created_at,
        }
