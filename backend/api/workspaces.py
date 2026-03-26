from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..db import get_db

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=schemas.WorkspaceRead)
def create_workspace(payload: schemas.WorkspaceCreate, db: Session = Depends(get_db)):
    return crud.create_workspace(db, name=payload.name)


@router.get("", response_model=list[schemas.WorkspaceRead])
def list_workspaces(db: Session = Depends(get_db)):
    return crud.get_workspaces(db)


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: int, db: Session = Depends(get_db)):
    result = crud.delete_workspace(db, workspace_id=workspace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"message": "Workspace deleted successfully"}