from sqlalchemy.orm import Session
from . import models


# ── Workspace ──────────────────────────────────────────────────────────────────

def create_workspace(db: Session, name: str):
    workspace = models.Workspace(name=name)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_workspaces(db: Session):
    return db.query(models.Workspace).all()


def delete_workspace(db: Session, workspace_id: int):
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        return None
    db.delete(workspace)
    db.commit()
    return True


# ── Document ───────────────────────────────────────────────────────────────────

def create_document(db: Session, workspace_id: int, content: str):
    document = models.Document(workspace_id=workspace_id, content=content)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
def delete_document(db: Session, document_id: int):
    document = get_document(db, document_id)
    if document:
        db.delete(document)
        db.commit()

def get_documents_by_workspace(db: Session, workspace_id: int):
    return db.query(models.Document).filter(models.Document.workspace_id == workspace_id).all()

def get_document(db: Session, document_id: int):
    return db.query(models.Document).filter(models.Document.id == document_id).first()
# ── Search ─────────────────────────────────────────────────────────────────────

def search_documents(db: Session, query: str):
    return db.query(models.Document).filter(models.Document.content.like(f"%{query}%")).all()