from pydantic import BaseModel, ConfigDict


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceRead(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    workspace_id: int
    content: str


class DocumentRead(BaseModel):
    id: int
    workspace_id: int
    content: str
    model_config = ConfigDict(from_attributes=True)