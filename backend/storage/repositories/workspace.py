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

    def list_all(self) -> list[Workspace]:
        return self.db.query(Workspace).all()

    def get_by_id(self, workspace_id: int) -> Workspace | None:
        return self.db.query(Workspace).filter(Workspace.id == workspace_id).first()

    def get_by_uuid(self, workspace_id: UUID) -> Workspace | None:
        return self.db.query(Workspace).filter(Workspace.workspace_id == str(workspace_id)).first()

    def delete(self, workspace_id: int) -> bool:
        workspace = self.get_by_id(workspace_id)
        if workspace is None:
            return False
        self.db.delete(workspace)
        self.db.commit()
        return True

    def update_by_uuid(
        self,
        *,
        workspace_id: UUID,
        owner_id: str,
        updates: dict,
    ) -> tuple[Workspace | None, str | None]:
        workspace = self.get_by_uuid(workspace_id)
        if workspace is None:
            return None, "not_found"

        if workspace.owner_id != owner_id:
            return None, "forbidden"

        for field, value in updates.items():
            if value is not None:
                setattr(workspace, field, value)

        self.db.commit()
        self.db.refresh(workspace)
        return workspace, None
