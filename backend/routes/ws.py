from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.auth import CurrentUser, get_current_user
from backend.db import get_db
from backend.repositories.workspace import update_workspace
from backend.schemas import WorkspaceRead, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def patch_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    workspace, error = update_workspace(
        db=db,
        workspace_id=workspace_id,
        owner_id=current_user.user_id,
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
