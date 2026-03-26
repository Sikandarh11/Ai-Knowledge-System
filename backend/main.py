from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.db import engine
from backend.models import Base
from backend.api import workspaces, documents, query, chat, upload


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Workspace API",
    description="Backend API for managing workspaces, documents, and RAG-powered chat.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(upload.router)

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "version": "2.0.0"}