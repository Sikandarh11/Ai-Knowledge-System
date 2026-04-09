from uuid import UUID

from sqlalchemy.orm import Session

from backend.storage.models import Workspace
from backend.storage.repositories.workspace import WorkspaceRepository


class WorkspaceService:
    def __init__(self, db: Session):
        self._repo = WorkspaceRepository(db)

    def create_workspace(
        self,
        *,
        name: str,
        workspace_type: str,
        description: str | None = None,
        owner_id: str | None = None,
    ) -> Workspace:
        return self._repo.create(
            name=name,
            workspace_type=workspace_type,
            description=description,
            owner_id=owner_id,
        )

    def list_workspaces(self, owner_id: str | None = None) -> list[Workspace]:
        return self._repo.list_all(owner_id=owner_id)

    def delete_workspace_for_owner(self, workspace_id: int, owner_id: str) -> tuple[bool, str | None]:
        return self._repo.delete_for_owner(workspace_id, owner_id)

    def update_workspace(
        self,
        *,
        workspace_id: UUID,
        owner_id: str,
        updates: dict,
    ) -> tuple[Workspace | None, str | None]:
        return self._repo.update_by_uuid(
            workspace_id=workspace_id,
            owner_id=owner_id,
            updates=updates,
        )
