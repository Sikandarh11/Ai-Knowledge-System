from uuid import UUID

from sqlalchemy.orm import Session

from backend.storage.repositories.workspace import WorkspaceRepository


def update_workspace(db: Session, workspace_id: UUID, owner_id: str, updates: dict):
    repository = WorkspaceRepository(db)
    return repository.update_by_uuid(
        workspace_id=workspace_id,
        owner_id=owner_id,
        updates=updates,
    )
