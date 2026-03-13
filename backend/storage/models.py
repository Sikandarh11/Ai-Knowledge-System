"""
backend/storage/models.py

SQLAlchemy ORM models for the Agentic AI Personal Knowledge System.

Entity hierarchy:
    User
    └── Workspace (many per user)
        └── Document (many per workspace)
            └── Chunk (many per document)

Design decisions:
    - UUID primary keys prevent enumeration attacks and work across distributed systems.
    - created_at timestamps use server_default so the DB sets them — no application clock drift.
    - Cascading deletes flow top-down: deleting a User removes all their data.
    - Indexes are added on every foreign key and on fields used in frequent WHERE clauses.
    - All models inherit from Base defined in backend/storage/database.py.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.storage.database import Base


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    """
    Represents an authenticated user of the system.

    A user owns one or more Workspaces. Authentication credentials
    (hashed password, OAuth tokens) belong in a separate auth table
    to keep this model clean.
    """

    __tablename__ = "users"

    # Primary key — UUID avoids sequential ID guessing.
    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique user identifier (UUID v4).",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,          # Indexed: used in every login and JWT validation query.
        doc="User's email address. Must be unique across all accounts.",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="bcrypt-hashed password. Never store plain text.",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Soft-disable accounts without deleting data.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Account creation timestamp (UTC, set by the database).",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace",
        back_populates="user",
        cascade="all, delete-orphan",   # Deleting a user removes all their workspaces.
        lazy="select",
        doc="All workspaces owned by this user.",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

class Workspace(Base):
    """
    A named knowledge space owned by a User.

    Each workspace maps to its own ChromaDB collection (chroma_collection).
    This enforces retrieval isolation — a query against the 'Work' workspace
    can never surface documents from 'Personal' or 'Research'.

    Examples of workspace types: Work, Personal, Research, Projects.
    """

    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique workspace identifier (UUID v4).",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="FK → users.id. The user who owns this workspace.",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Human-readable workspace name, e.g. 'Research 2024'.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional description of the workspace's purpose.",
    )

    chroma_collection: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        doc=(
            "ChromaDB collection name for this workspace. "
            "Typically set to the workspace UUID string. "
            "Bridge between PostgreSQL metadata and the vector store."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Workspace creation timestamp (UTC, set by the database).",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workspaces",
        doc="The user who owns this workspace.",
    )

    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="select",
        doc="All documents uploaded to this workspace.",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_workspaces_user_id", "user_id"),  # list_by_user queries
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id!r} name={self.name!r} user_id={self.user_id!r}>"


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class Document(Base):
    """
    A single uploaded file within a Workspace.

    Tracks the file on disk (file_path), ingestion status, and how many
    chunks were produced. The status field drives the UI progress indicator.

    Status lifecycle:
        'processing'  →  ingestion background task is running
        'ready'       →  chunks are in ChromaDB, document is queryable
        'failed'      →  ingestion failed; error_message contains the reason
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique document identifier (UUID v4).",
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        doc="FK → workspaces.id. The workspace this document belongs to.",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Display title. Defaults to the original filename.",
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Absolute path to the uploaded file on disk.",
    )

    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="File extension without the dot: 'pdf', 'docx', 'txt', 'md'.",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="processing",
        index=True,         # Indexed: polled frequently via GET /documents/{id}/status
        doc="Ingestion status: 'processing' | 'ready' | 'failed'.",
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of chunks produced during ingestion. 0 until ingestion completes.",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Populated when status='failed'. Contains the exception message.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Upload timestamp (UTC, set by the database).",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="documents",
        doc="The workspace this document belongs to.",
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
        doc="All text chunks produced from this document.",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_documents_workspace_id", "workspace_id"),  # list_by_workspace queries
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id!r} title={self.title!r} "
            f"status={self.status!r} workspace_id={self.workspace_id!r}>"
        )


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------

class Chunk(Base):
    """
    A text segment extracted from a Document during ingestion.

    Each chunk has a corresponding vector in ChromaDB (identified by
    chroma_id). The chunk content is stored here for citation rendering —
    so the UI can display the exact passage that was retrieved without
    re-querying ChromaDB.

    chunk_index preserves the original order of chunks within a document,
    which matters for context assembly in the reasoning agent.
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique chunk identifier (UUID v4).",
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        doc="FK → documents.id. The document this chunk was extracted from.",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Raw text content of this chunk (512 tokens by default).",
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Zero-based position of this chunk within its document.",
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Source page number for PDF documents. None for plain text files.",
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Approximate token count of this chunk's content.",
    )

    chroma_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        doc=(
            "The ID of this chunk's vector in ChromaDB. "
            "Set after the embedding is stored. Null while ingestion is in progress."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Chunk creation timestamp (UTC, set by the database).",
    )

    # ── Relationships ────────────────────────────────────────────────────────
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
        doc="The document this chunk was extracted from.",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_chunks_document_id", "document_id"),            # bulk fetch by document
        Index("ix_chunks_document_chunk_index", "document_id", "chunk_index"),  # ordered retrieval
    )

    def __repr__(self) -> str:
        return (
            f"<Chunk id={self.id!r} document_id={self.document_id!r} "
            f"index={self.chunk_index} tokens={self.token_count}>"
        )


# ---------------------------------------------------------------------------
# Manual self-test
# ---------------------------------------------------------------------------
# Uncomment the block below and run this file directly to verify the module:
#
#   python -m backend.storage.models
#   — or —
#   python backend/storage/models.py
#
# What this test covers:
#   1. All four models can be imported and instantiated
#   2. Relationships are wired correctly (User → Workspace → Document → Chunk)
#   3. create_all_tables() creates the correct schema in SQLite
#   4. A full insert + query round-trip through all four tables
#   5. Cascade delete: removing a User deletes all their downstream records
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import uuid
    from sqlalchemy import text
    from backend.storage.database import (
        SessionLocal,
        create_all_tables,
        drop_all_tables,
        DATABASE_URL,
    )

    print("=" * 60)
    print("models.py — manual self-test")
    print("=" * 60)

    # Build schema in the default SQLite dev DB
    create_all_tables()
    print("\n[1] Schema       : create_all_tables() OK")

    db = SessionLocal()

    try:
        # ── Test 2: Create a User ────────────────────────────────────────────
        user = User(
            id=uuid.uuid4(),
            email="testuser@example.com",
            hashed_password="$2b$12$fakehash",
            is_active=True,
        )
        db.add(user)
        db.flush()
        print(f"\n[2] User created : {user}")

        # ── Test 3: Create a Workspace ───────────────────────────────────────
        ws_id = uuid.uuid4()
        workspace = Workspace(
            id=ws_id,
            user_id=user.id,
            name="Research",
            description="My research workspace",
            chroma_collection=f"workspace_{ws_id}",
        )
        db.add(workspace)
        db.flush()
        print(f"\n[3] Workspace    : {workspace}")

        # ── Test 4: Create a Document ────────────────────────────────────────
        doc_id = uuid.uuid4()
        document = Document(
            id=doc_id,
            workspace_id=workspace.id,
            title="AI Research Paper.pdf",
            file_path="/uploads/ai_research.pdf",
            file_type="pdf",
            status="processing",
            chunk_count=0,
        )
        db.add(document)
        db.flush()
        print(f"\n[4] Document     : {document}")

        # ── Test 5: Create Chunks ────────────────────────────────────────────
        chunks = [
            Chunk(
                id=uuid.uuid4(),
                document_id=document.id,
                content=f"This is chunk number {i} with some meaningful text.",
                chunk_index=i,
                page_number=i + 1,
                token_count=12,
                chroma_id=f"chroma_chunk_{i}",
            )
            for i in range(3)
        ]
        db.add_all(chunks)
        db.commit()
        print(f"\n[5] Chunks       : inserted {len(chunks)} chunks")
        for c in chunks:
            print(f"    {c}")

        # ── Test 6: Verify relationships ─────────────────────────────────────
        from sqlalchemy import select
        fetched_user = db.execute(
            select(User).where(User.email == "testuser@example.com")
        ).scalars().first()
        assert fetched_user is not None, "User not found after commit"
        assert len(fetched_user.workspaces) == 1, "Expected 1 workspace"
        assert len(fetched_user.workspaces[0].documents) == 1, "Expected 1 document"
        assert len(fetched_user.workspaces[0].documents[0].chunks) == 3, "Expected 3 chunks"
        print(f"\n[6] Relationships: OK — User → {len(fetched_user.workspaces)} workspace(s) "
              f"→ {len(fetched_user.workspaces[0].documents)} document(s) "
              f"→ {len(fetched_user.workspaces[0].documents[0].chunks)} chunk(s)")

        # ── Test 7: Cascade delete ───────────────────────────────────────────
        db.delete(fetched_user)
        db.commit()
        remaining = db.execute(select(Workspace)).scalars().all()
        assert len(remaining) == 0, f"Expected 0 workspaces after user delete, got {len(remaining)}"
        remaining_chunks = db.execute(select(Chunk)).scalars().all()
        assert len(remaining_chunks) == 0, f"Expected 0 chunks after cascade, got {len(remaining_chunks)}"
        print("\n[7] Cascade del  : OK — deleting User removed all workspaces, documents, and chunks")

    finally:
        db.close()
        drop_all_tables()
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("./", "")
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"\n    Cleaned up test DB: {db_path}")

    print("\n" + "=" * 60)
    print("All models.py tests passed.")
    print("=" * 60)
