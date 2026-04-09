from uuid import UUID

from sqlalchemy.orm import Session
from . import models


# ── Workspace ──────────────────────────────────────────────────────────────────

def create_workspace(
    db: Session,
    name: str,
    workspace_type: str = "Work",
    description: str | None = None,
    owner_id: str | None = None,
):
    workspace = models.Workspace(
        name=name,
        type=workspace_type,
        description=description,
        owner_id=owner_id,
    )
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


def get_workspace_by_uuid(db: Session, workspace_id: UUID):
    return db.query(models.Workspace).filter(models.Workspace.workspace_id == str(workspace_id)).first()


def update_workspace_by_uuid(db: Session, workspace_id: UUID, updates: dict):
    workspace = get_workspace_by_uuid(db, workspace_id)
    if not workspace:
        return None

    for field, value in updates.items():
        if value is not None:
            setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)
    return workspace


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