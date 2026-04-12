from sqlalchemy.orm import Session

from backend.services.chat_service import ChatService


class QueryService:
    def __init__(self, db: Session):
        self._chat_or_query = ChatService(db)

    def search_documents(self, query: str, workspace_id: str | None = None) -> dict:
        # Compatibility wrapper for legacy query flow.
        return self._chat_or_query.run(
            query=query,
            workspace_id=workspace_id,
            history=None,
            mode="query",
            include_documents=True,
        )
