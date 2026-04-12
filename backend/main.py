from uuid import uuid4

from sqlalchemy import inspect, text
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.storage.database import engine
from backend.storage.models import Base
from backend.api.routes import auth, workspaces, documents, query, chat, upload, voice


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


def _ensure_contacts_schema() -> None:
    inspector = inspect(engine)

    with engine.begin() as connection:
        if "contacts" not in inspector.get_table_names():
            connection.execute(
                text(
                    """
                    CREATE TABLE contacts (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        source VARCHAR(32) NOT NULL DEFAULT 'manual',
                        frequency INTEGER NOT NULL DEFAULT 1,
                        last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
        else:
            column_defs = inspector.get_columns("contacts")
            columns = {column["name"] for column in column_defs}

            id_column = next((column for column in column_defs if column.get("name") == "id"), None)
            id_type = str(id_column.get("type", "")).upper() if id_column else ""
            id_is_text = any(token in id_type for token in ("CHAR", "TEXT", "CLOB", "VARCHAR"))

            # Legacy schema may have INTEGER id; model now uses UUID strings.
            # Rebuild table once to avoid sqlite datatype mismatch on inserts.
            if not id_is_text:
                last_used_expr = "COALESCE(last_used, CURRENT_TIMESTAMP)"
                if "last_seen_at" in columns:
                    last_used_expr = "COALESCE(last_used, last_seen_at, CURRENT_TIMESTAMP)"

                connection.execute(text("DROP TABLE IF EXISTS contacts__new"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE contacts__new (
                            id VARCHAR(36) PRIMARY KEY,
                            user_id VARCHAR(36) NOT NULL,
                            name VARCHAR(255) NOT NULL,
                            email VARCHAR(255) NOT NULL,
                            source VARCHAR(32) NOT NULL DEFAULT 'manual',
                            frequency INTEGER NOT NULL DEFAULT 1,
                            last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )

                connection.execute(
                    text(
                        f"""
                        INSERT INTO contacts__new (id, user_id, name, email, source, frequency, last_used)
                        SELECT
                            COALESCE(NULLIF(CAST(id AS TEXT), ''), LOWER(HEX(RANDOMBLOB(16)))) AS id,
                            CAST(user_id AS TEXT) AS user_id,
                            COALESCE(NULLIF(TRIM(name), ''), LOWER(email)) AS name,
                            LOWER(email) AS email,
                            COALESCE(NULLIF(source, ''), 'manual') AS source,
                            CASE WHEN frequency IS NULL OR frequency < 1 THEN 1 ELSE frequency END AS frequency,
                            {last_used_expr} AS last_used
                        FROM contacts
                        WHERE email IS NOT NULL
                          AND TRIM(email) <> ''
                          AND user_id IS NOT NULL
                          AND TRIM(CAST(user_id AS TEXT)) <> ''
                        """
                    )
                )

                connection.execute(text("DROP TABLE contacts"))
                connection.execute(text("ALTER TABLE contacts__new RENAME TO contacts"))

                # Refresh contact column metadata after rebuild.
                inspector = inspect(engine)
                column_defs = inspector.get_columns("contacts")
                columns = {column["name"] for column in column_defs}

            if "source" not in columns:
                connection.execute(text("ALTER TABLE contacts ADD COLUMN source VARCHAR(32) DEFAULT 'manual'"))
            if "frequency" not in columns:
                connection.execute(text("ALTER TABLE contacts ADD COLUMN frequency INTEGER DEFAULT 1"))
            if "last_used" not in columns:
                connection.execute(text("ALTER TABLE contacts ADD COLUMN last_used DATETIME"))
                if "last_seen_at" in columns:
                    connection.execute(
                        text(
                            "UPDATE contacts "
                            "SET last_used = COALESCE(last_seen_at, CURRENT_TIMESTAMP) "
                            "WHERE last_used IS NULL"
                        )
                    )
                else:
                    connection.execute(
                        text("UPDATE contacts SET last_used = CURRENT_TIMESTAMP WHERE last_used IS NULL")
                    )

            # Backfill defaults for rows inserted before these columns existed.
            connection.execute(text("UPDATE contacts SET source = 'manual' WHERE source IS NULL OR source = ''"))
            connection.execute(text("UPDATE contacts SET frequency = 1 WHERE frequency IS NULL OR frequency < 1"))

        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_contacts_user_id ON contacts(user_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_contacts_name ON contacts(name)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_contacts_email ON contacts(email)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_user_email ON contacts(user_id, email)"))


def _ensure_users_schema() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}

    with engine.begin() as connection:
        if "username" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(64)"))

        # Backfill legacy rows so profile/avatar can render for existing users.
        # Use email to guarantee uniqueness before adding unique index.
        connection.execute(
            text(
                """
                UPDATE users
                SET username = email
                WHERE username IS NULL OR TRIM(username) = ''
                """
            )
        )

        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username)"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_workspace_schema()
    _ensure_contacts_schema()
    _ensure_users_schema()
    yield


app = FastAPI(
    title="Workspace API",
    description="Backend API for managing workspaces, documents, and RAG-powered chat.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(voice.router)

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "version": "2.0.0"}