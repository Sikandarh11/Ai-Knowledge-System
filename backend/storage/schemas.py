from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    doc_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    workspace_id: int
    content: str


class DocumentRead(BaseModel):
    id: int
    workspace_id: int
    filename: str | None = None
    file_type: str | None = None
    chunk_count: int | None = None
    created_at: datetime | None = None
    content: str
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserRead(BaseModel):
    id: str
    email: str
    username: str | None = None
    model_config = ConfigDict(from_attributes=True)
