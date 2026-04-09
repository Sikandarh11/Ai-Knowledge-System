from sqlalchemy.orm import Session

from backend.storage.models import Document
from backend.storage.repositories.document import DocumentRepository


class QueryService:
    def __init__(self, db: Session):
        self._repo = DocumentRepository(db)

    def search_documents(self, query: str) -> list[Document]:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        return self._repo.search(query.strip())
