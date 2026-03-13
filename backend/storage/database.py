"""
backend/storage/database.py

Database configuration module for the Agentic AI Personal Knowledge System.

Responsibilities:
- Create the SQLAlchemy engine from environment configuration
- Provide a reusable SessionLocal factory
- Declare the Base class shared by all ORM models
- Expose a FastAPI-compatible get_db() dependency

This module is intentionally free of business logic and AI dependencies.
It is imported by: ingestion, RAG pipeline, agent tools, and API routes.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_database_url() -> str:
    """
    Read the database connection URL from the environment.

    Defaults to a local SQLite file for zero-config development.
    Set DATABASE_URL to a PostgreSQL DSN for staging or production:

        DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname

    Returns:
        str: A SQLAlchemy-compatible connection string.
    """
    return os.getenv(
        "DATABASE_URL",
        "sqlite:///./ai_knowledge_system.db",
    )


DATABASE_URL: str = _get_database_url()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _build_engine(url: str) -> Engine:
    """
    Create a SQLAlchemy Engine configured for the given database URL.

    SQLite quirk:
        SQLite does not support multiple threads sharing a connection by
        default. The `check_same_thread=False` argument is required when
        running inside FastAPI (which uses a thread pool). This flag is
        only passed for SQLite connections.

    PostgreSQL:
        No extra connect_args are needed. Connection pooling (QueuePool)
        is used automatically by SQLAlchemy when the dialect is not SQLite.

    Args:
        url: SQLAlchemy database URL.

    Returns:
        Engine: A configured SQLAlchemy engine instance.
    """
    connect_args: dict = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        url,
        connect_args=connect_args,
        # Echo SQL statements to stdout in development.
        # Set to False or read from an env var in production.
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
    )


engine: Engine = _build_engine(DATABASE_URL)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,   # Explicit commits required — safer for transactional work.
    autoflush=False,    # Flush manually to control when SQL is emitted.
    expire_on_commit=False,  # Keep ORM objects usable after commit (important for async patterns).
)
"""
Session factory.

Usage (outside FastAPI):
    with SessionLocal() as session:
        result = session.execute(select(User)).scalars().all()

Usage inside FastAPI:
    Use the get_db() dependency instead (see below).
"""


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All models in backend/storage/models.py must inherit from this class
    so that Alembic's autogenerate can detect schema changes.

    Example:
        class User(Base):
            __tablename__ = "users"
            ...
    """
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request.

    Guarantees the session is closed after the request completes,
    whether the handler succeeded or raised an exception.

    Usage in a route:
        @router.get("/workspaces")
        def list_workspaces(db: Session = Depends(get_db)):
            return workspace_repo.get_user_workspaces(db, user_id=...)

    Yields:
        Session: An active SQLAlchemy session bound to the request lifecycle.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schema initialisation helper (development / testing only)
# ---------------------------------------------------------------------------

def create_all_tables() -> None:
    """
    Create all tables registered on Base.metadata.

    Call this during application startup in development, or inside test
    fixtures when using an in-memory SQLite database.

    In production, use Alembic migrations instead:
        alembic upgrade head

    Note:
        This function is a no-op if the tables already exist.
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables() -> None:
    """
    Drop all tables registered on Base.metadata.

    Intended for use in test teardown only. Never call this in production.
    """
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Manual self-test
# ---------------------------------------------------------------------------
# Uncomment the block below and run this file directly to verify the module:
#
#   python -m backend.storage.database
#   — or —
#   python backend/storage/database.py
#
# What this test covers:
#   1. Engine creation with the default SQLite URL
#   2. SessionLocal produces a usable session
#   3. Base.metadata is importable (models will register themselves on it)
#   4. get_db() generator yields and closes cleanly
#   5. create_all_tables() / drop_all_tables() round-trip on a fresh DB
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     import os
#     from sqlalchemy import text

#     print("=" * 60)
#     print("database.py — manual self-test")
#     print("=" * 60)

#     # ── Test 1: DATABASE_URL resolution ─────────────────────────────────────
#     print(f"\n[1] DATABASE_URL : {DATABASE_URL}")
#     assert DATABASE_URL.startswith("sqlite"), "Expected SQLite default URL"
#     print("    OK — defaults to SQLite as expected")

#     # ── Test 2: Engine creation ──────────────────────────────────────────────
#     print(f"\n[2] Engine       : {engine}")
#     assert engine is not None, "Engine must not be None"
#     print("    OK — engine created successfully")

#     # ── Test 3: Engine connectivity ──────────────────────────────────────────
#     print("\n[3] Connectivity : testing raw SQL ping...")
#     with engine.connect() as conn:
#         result = conn.execute(text("SELECT 1")).scalar()
#     assert result == 1, f"Expected 1, got {result}"
#     print(f"    OK — SELECT 1 returned {result}")

#     # ── Test 4: SessionLocal ─────────────────────────────────────────────────
#     print("\n[4] SessionLocal : opening and closing a session...")
#     session = SessionLocal()
#     assert session is not None, "Session must not be None"
#     ping = session.execute(text("SELECT 42")).scalar()
#     assert ping == 42, f"Expected 42, got {ping}"
#     session.close()
#     print(f"    OK — session executed SELECT 42, got {ping}, closed cleanly")

#     # ── Test 5: get_db() generator ───────────────────────────────────────────
#     print("\n[5] get_db()     : testing generator dependency...")
#     gen = get_db()
#     db_session = next(gen)
#     assert db_session is not None, "get_db() must yield a session"
#     pong = db_session.execute(text("SELECT 99")).scalar()
#     assert pong == 99, f"Expected 99, got {pong}"
#     try:
#         next(gen)  # triggers the finally block → closes the session
#     except StopIteration:
#         pass
#     print(f"    OK — get_db() yielded session, returned {pong}, session closed")

#     # ── Test 6: Base metadata ────────────────────────────────────────────────
#     print("\n[6] Base         : checking DeclarativeBase...")
#     assert hasattr(Base, "metadata"), "Base must expose .metadata"
#     print(f"    OK — Base.metadata found: {Base.metadata}")

#     # ── Test 7: create_all / drop_all ────────────────────────────────────────
#     print("\n[7] Schema ops   : create_all_tables() then drop_all_tables()...")
#     # At this point no models have been imported, so metadata is empty.
#     # Import models here to register them before calling create_all.
#     # (In normal use, models are imported at app startup.)
#     # from backend.storage.models import User, Workspace, Document, Chunk
#     create_all_tables()
#     print("    OK — create_all_tables() completed without error")
#     drop_all_tables()
#     print("    OK — drop_all_tables() completed without error")

#     # ── Cleanup ──────────────────────────────────────────────────────────────
#     db_path = DATABASE_URL.replace("sqlite:///", "")
#     engine.dispose()
#     if os.path.exists(db_path):
        
#         os.remove(db_path)
#         print(f"\n    Cleaned up test DB file: {db_path}")



#     print("\n" + "=" * 60)
#     print("All database.py tests passed.")
#     print("=" * 60)
