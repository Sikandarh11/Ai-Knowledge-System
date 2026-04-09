from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkspaceType(str, Enum):
    WORK = "Work"
    PERSONAL = "Personal"
    RESEARCH = "Research"
    PROJECTS = "Projects"


class WorkspaceCreate(BaseModel):
    name: str
    type: WorkspaceType = WorkspaceType.WORK
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    type: WorkspaceType | None = None
    description: str | None = None


class WorkspaceRead(BaseModel):
    id: int
    workspace_id: UUID
    name: str
    type: WorkspaceType
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    workspace_id: int
    content: str


class DocumentRead(BaseModel):
    id: int
    workspace_id: int
    content: str
    model_config = ConfigDict(from_attributes=True)