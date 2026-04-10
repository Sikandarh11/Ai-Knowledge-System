from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.services.workspace_service import WorkspaceService
from backend.storage.database import get_db
from backend.storage.models import User
from backend.storage.schemas import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead)
def create_workspace(
    payload: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    return service.create_workspace(
        name=payload.name,
        workspace_type=payload.type.value,
        description=payload.description,
        owner_id=current_user.id,
    )


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    return service.list_workspaces(owner_id=current_user.id)


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    deleted, error = service.delete_workspace_for_owner(workspace_id, current_user.id)
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Workspace not found")
    if error == "forbidden":
        raise HTTPException(status_code=403, detail="You are not authorized to delete this workspace")
    return {"message": "Workspace deleted successfully"}


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def patch_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = WorkspaceService(db)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    workspace, error = service.update_workspace(
        workspace_id=workspace_id,
        owner_id=current_user.id,
        updates=updates,
    )

    if error == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    if error == "forbidden":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this workspace",
        )

    return workspace
