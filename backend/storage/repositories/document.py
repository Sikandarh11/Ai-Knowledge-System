from sqlalchemy.orm import Session

from backend.storage.models import Document


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        workspace_id: int,
        content: str,
        filename: str | None = None,
        file_type: str | None = None,
        chunk_count: int | None = None,
    ) -> Document:
        document = Document(
            workspace_id=workspace_id,
            content=content,
            filename=filename or "document.txt",
            file_type=file_type or "txt",
            chunk_count=chunk_count if chunk_count is not None else 0,
        )
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

    def search(self, query: str, workspace_id: int | None = None) -> list[Document]:
        query_builder = self.db.query(Document).filter(Document.content.like(f"%{query}%"))
        if workspace_id is not None:
            query_builder = query_builder.filter(Document.workspace_id == workspace_id)
        return query_builder.all()

    def get_by_ids(self, document_ids: list[int], workspace_id: int | None = None) -> list[Document]:
        if not document_ids:
            return []

        query_builder = self.db.query(Document).filter(Document.id.in_(document_ids))
        if workspace_id is not None:
            query_builder = query_builder.filter(Document.workspace_id == workspace_id)
        return query_builder.all()
