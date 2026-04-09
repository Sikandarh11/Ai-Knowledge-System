from sqlalchemy.orm import Session

from backend.storage.models import Document


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, workspace_id: int, content: str) -> Document:
        document = Document(workspace_id=workspace_id, content=content)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get(self, document_id: int) -> Document | None:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def list_by_workspace(self, workspace_id: int) -> list[Document]:
        return self.db.query(Document).filter(Document.workspace_id == workspace_id).all()

    def delete(self, document_id: int) -> bool:
        document = self.get(document_id)
        if document is None:
            return False
        self.db.delete(document)
        self.db.commit()
        return True

    def search(self, query: str) -> list[Document]:
        return self.db.query(Document).filter(Document.content.like(f"%{query}%")).all()
