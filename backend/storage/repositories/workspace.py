from uuid import UUID

from sqlalchemy.orm import Session

from backend.storage.models import Workspace


class WorkspaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        name: str,
        workspace_type: str = "Work",
        description: str | None = None,
        owner_id: str | None = None,
    ) -> Workspace:
        workspace = Workspace(
            name=name,
            type=workspace_type,
            description=description,
            owner_id=owner_id,
        )
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def list_all(self, owner_id: str | None = None) -> list[Workspace]:
        query = self.db.query(Workspace)
        if owner_id is not None:
            query = query.filter(Workspace.owner_id == owner_id)
        return query.all()

    def get_by_id(self, workspace_id: int) -> Workspace | None:
        return self.db.query(Workspace).filter(Workspace.id == workspace_id).first()

    def get_by_uuid(self, workspace_id: UUID) -> Workspace | None:
        return self.db.query(Workspace).filter(Workspace.workspace_id == str(workspace_id)).first()

    def delete_for_owner(self, workspace_id: int, owner_id: str) -> tuple[bool, str | None]:
        workspace = (
            self.db.query(Workspace)
            .filter(Workspace.id == workspace_id, Workspace.owner_id == owner_id)
            .first()
        )
        if workspace is None:
            exists = self.get_by_id(workspace_id)
            if exists is None:
                return False, "not_found"
            return False, "forbidden"

        self.db.delete(workspace)
        self.db.commit()
        return True, None

    def update_by_uuid(
        self,
        *,
        workspace_id: UUID,
        owner_id: str,
        updates: dict,
    ) -> tuple[Workspace | None, str | None]:
        workspace = (
            self.db.query(Workspace)
            .filter(
                Workspace.workspace_id == str(workspace_id),
                Workspace.owner_id == owner_id,
            )
            .first()
        )
        if workspace is None:
            exists = self.get_by_uuid(workspace_id)
            if exists is None:
                return None, "not_found"
            return None, "forbidden"

        for field, value in updates.items():
            if value is not None:
                setattr(workspace, field, value)

        self.db.commit()
        self.db.refresh(workspace)
        return workspace, None
