from uuid import UUID

from sqlalchemy.orm import Session

from backend import models


def update_workspace(db: Session, workspace_id: UUID, owner_id: str, updates: dict):
    workspace = db.query(models.Workspace).filter(models.Workspace.workspace_id == str(workspace_id)).first()

    if workspace is None:
        return None, "not_found"

    if workspace.owner_id != owner_id:
        return None, "forbidden"

    for field, value in updates.items():
        if value is not None:
            setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)
    return workspace, None
