from uuid import uuid4

from sqlalchemy import inspect, text
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.db import engine
from backend.models import Base
from backend.api import workspaces, documents, query, chat, upload
from backend.routes import ws


def _ensure_workspace_schema() -> None:
    inspector = inspect(engine)
    if "workspaces" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("workspaces")}

    with engine.begin() as connection:
        if "workspace_id" not in columns:
            connection.execute(text("ALTER TABLE workspaces ADD COLUMN workspace_id VARCHAR(36)"))
            existing_rows = connection.execute(text("SELECT id FROM workspaces WHERE workspace_id IS NULL")).fetchall()
            for row in existing_rows:
                connection.execute(
                    text("UPDATE workspaces SET workspace_id = :workspace_id WHERE id = :id"),
                    {"workspace_id": str(uuid4()), "id": row.id},
                )

        if "type" not in columns:
            connection.execute(text("ALTER TABLE workspaces ADD COLUMN type VARCHAR DEFAULT 'Work'"))
            connection.execute(text("UPDATE workspaces SET type = 'Work' WHERE type IS NULL"))

        if "description" not in columns:
            connection.execute(text("ALTER TABLE workspaces ADD COLUMN description TEXT"))

        if "owner_id" not in columns:
            connection.execute(text("ALTER TABLE workspaces ADD COLUMN owner_id VARCHAR(255)"))

        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_workspaces_workspace_id ON workspaces(workspace_id)")
        )
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_workspaces_owner_id ON workspaces(owner_id)"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_workspace_schema()
    yield


app = FastAPI(
    title="Workspace API",
    description="Backend API for managing workspaces, documents, and RAG-powered chat.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(workspaces.router)
app.include_router(ws.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(upload.router)

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "version": "2.0.0"}