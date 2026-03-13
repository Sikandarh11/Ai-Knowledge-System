"""
backend/storage/repositories/workspace.py

Repository for Workspace database operations.

Responsibilities:
    - Provide all database access methods for the Workspace model.
    - Accept a SQLAlchemy Session as a dependency (injected by the caller).
    - Contain zero business logic — only SQL operations.

The repository layer sits between the service/agent layer and the database.
Services call repository methods; repositories call SQLAlchemy. Nothing else
should query the database directly.

Usage example:
    from backend.storage.repositories.workspace import WorkspaceRepository
    from backend.storage.database import get_db

    repo = WorkspaceRepository()

    # Inside a FastAPI route:
    @router.post("/workspaces")
    def create(payload: WorkspaceCreate, db: Session = Depends(get_db)):
        return repo.create_workspace(db, user_id=current_user.id, name=payload.name)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.storage.models import Workspace


class WorkspaceRepository:
    """
    Data-access class for the Workspace entity.

    All methods accept a Session as their first argument so the caller
    controls transaction boundaries. The repository never commits or
    rolls back — that is the service layer's responsibility.
    """

    # -----------------------------------------------------------------------
    # Create
    # -----------------------------------------------------------------------

    def create_workspace(
        self,
        db: Session,
        *,
        user_id: uuid.UUID,
        name: str,
        description: str | None = None,
    ) -> Workspace:
        """
        Insert a new Workspace row and return the persisted object.

        The chroma_collection name is derived from the workspace UUID so
        it is guaranteed to be unique without a separate lookup. The
        ChromaDB collection itself is created by the service layer, not here.

        Args:
            db:          Active SQLAlchemy session.
            user_id:     UUID of the user who owns this workspace.
            name:        Human-readable workspace name (e.g. "Research 2024").
            description: Optional text describing the workspace's purpose.

        Returns:
            Workspace: The newly created and flushed ORM instance.
                       Call db.commit() in the service layer to persist it.
        """
        workspace_id = uuid.uuid4()

        workspace = Workspace(
            id=workspace_id,
            user_id=user_id,
            name=name,
            description=description,
            # Derive the ChromaDB collection name from the workspace UUID.
            # Using a predictable format makes debugging and inspection easy.
            chroma_collection=f"workspace_{workspace_id}",
        )

        db.add(workspace)
        db.flush()  # Assigns DB-generated values; caller must commit.
        return workspace

    # -----------------------------------------------------------------------
    # Read — single record
    # -----------------------------------------------------------------------

    def get_workspace_by_id(
        self,
        db: Session,
        workspace_id: uuid.UUID,
    ) -> Workspace | None:
        """
        Fetch a single Workspace by its primary key.

        Args:
            db:           Active SQLAlchemy session.
            workspace_id: UUID of the workspace to retrieve.

        Returns:
            Workspace if found, None otherwise.
        """
        statement = select(Workspace).where(Workspace.id == str(workspace_id))
        return db.execute(statement).scalars().first()

    def get_workspace_by_id_and_user(
        self,
        db: Session,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Workspace | None:
        """
        Fetch a Workspace only if it belongs to the given user.

        Use this variant in route handlers to prevent users from accessing
        other users' workspaces without raising an explicit permission error
        in the repository layer.

        Args:
            db:           Active SQLAlchemy session.
            workspace_id: UUID of the workspace to retrieve.
            user_id:      UUID of the requesting user.

        Returns:
            Workspace if found and owned by user_id, None otherwise.
        """
        statement = (
            select(Workspace)
            .where(Workspace.id == str(workspace_id))
            .where(Workspace.user_id == str(user_id))
        )
        return db.execute(statement).scalars().first()

    def get_workspace_by_chroma_collection(
        self,
        db: Session,
        chroma_collection: str,
    ) -> Workspace | None:
        """
        Look up a Workspace by its ChromaDB collection name.

        Called by workspace_selector_tool in the agent layer to resolve
        a collection name back to workspace metadata.

        Args:
            db:               Active SQLAlchemy session.
            chroma_collection: The ChromaDB collection name string.

        Returns:
            Workspace if found, None otherwise.
        """
        statement = select(Workspace).where(
            Workspace.chroma_collection == chroma_collection
        )
        return db.execute(statement).scalars().first()

    # -----------------------------------------------------------------------
    # Read — collection
    # -----------------------------------------------------------------------

    def get_user_workspaces(
        self,
        db: Session,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Workspace]:
        """
        Return all Workspaces owned by a given user, ordered by creation date.

        Args:
            db:      Active SQLAlchemy session.
            user_id: UUID of the user whose workspaces to fetch.
            limit:   Maximum number of rows to return (default 50).
            offset:  Number of rows to skip for pagination (default 0).

        Returns:
            list[Workspace]: Ordered list of Workspace objects (newest first).
        """
        statement = (
            select(Workspace)
            .where(Workspace.user_id == str(user_id))
            .order_by(Workspace.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(db.execute(statement).scalars().all())

    def count_user_workspaces(
        self,
        db: Session,
        user_id: uuid.UUID,
    ) -> int:
        """
        Return the total number of workspaces owned by a user.

        Useful for pagination metadata in list API responses.

        Args:
            db:      Active SQLAlchemy session.
            user_id: UUID of the user.

        Returns:
            int: Total workspace count for the user.
        """
        from sqlalchemy import func as sql_func

        statement = (
            select(sql_func.count())
            .select_from(Workspace)
            .where(Workspace.user_id == str(user_id))
        )
        result = db.execute(statement).scalar()
        return result or 0

    # -----------------------------------------------------------------------
    # Update
    # -----------------------------------------------------------------------

    def update_workspace(
        self,
        db: Session,
        workspace: Workspace,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Workspace:
        """
        Update mutable fields on an existing Workspace.

        Only the fields explicitly passed as keyword arguments are changed.
        Fields left as None retain their current values.

        Args:
            db:          Active SQLAlchemy session.
            workspace:   The ORM instance to update (fetched by get_workspace_by_id).
            name:        New name, or None to leave unchanged.
            description: New description, or None to leave unchanged.

        Returns:
            Workspace: The updated ORM instance. Caller must commit.
        """
        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description

        db.flush()
        return workspace

    # -----------------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------------

    def delete_workspace(
        self,
        db: Session,
        workspace: Workspace,
    ) -> None:
        """
        Delete a Workspace and all its cascading children.

        Cascade behaviour (defined on the ORM model):
            Workspace → Documents → Chunks (all deleted automatically by the DB).

        The corresponding ChromaDB collection must be deleted separately
        by the service layer before or after calling this method — the
        repository only handles the relational database.

        Args:
            db:        Active SQLAlchemy session.
            workspace: The ORM instance to delete (fetched by get_workspace_by_id).

        Returns:
            None. Caller must commit to make the deletion permanent.
        """
        db.delete(workspace)
        db.flush()

    def delete_workspace_by_id(
        self,
        db: Session,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        Convenience method: fetch and delete a workspace in one call.

        Verifies ownership before deleting to prevent unauthorised deletion.

        Args:
            db:           Active SQLAlchemy session.
            workspace_id: UUID of the workspace to delete.
            user_id:      UUID of the requesting user (ownership check).

        Returns:
            True  if the workspace was found and deleted.
            False if no matching workspace was found (or wrong user).
        """
        workspace = self.get_workspace_by_id_and_user(db, workspace_id, user_id)
        if workspace is None:
            return False

        self.delete_workspace(db, workspace)
        return True


# ---------------------------------------------------------------------------
# Manual self-test
# ---------------------------------------------------------------------------
# Uncomment the block below and run this file directly to verify the module:
#
#   python -m backend.storage.repositories.workspace
#   — or —
#   python backend/storage/repositories/workspace.py
#
# What this test covers:
#   1. create_workspace() inserts a row and derives chroma_collection correctly
#   2. get_workspace_by_id() retrieves by PK
#   3. get_workspace_by_id_and_user() enforces ownership (returns None for wrong user)
#   4. get_user_workspaces() returns all workspaces for a user, sorted newest-first
#   5. count_user_workspaces() returns the correct count
#   6. update_workspace() mutates name/description in place
#   7. get_workspace_by_chroma_collection() resolves by collection name
#   8. delete_workspace_by_id() removes the row and returns True; wrong user returns False
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     import os
#     import uuid
#     from backend.storage.database import (
#         SessionLocal,
#         create_all_tables,
#         drop_all_tables,
#         DATABASE_URL,
#     )
#     from backend.storage.models import User
#
#     print("=" * 60)
#     print("workspace.py — manual self-test")
#     print("=" * 60)
#
#     # Bootstrap schema and a seed user that workspaces will belong to
#     create_all_tables()
#     db = SessionLocal()
#     repo = WorkspaceRepository()
#
#     try:
#         # Seed user (repository tests are not responsible for auth logic)
#         user_id = uuid.uuid4()
#         other_user_id = uuid.uuid4()
#         seed_user = User(
#             id=user_id,
#             email="repo_test@example.com",
#             hashed_password="$2b$12$fakehash",
#             is_active=True,
#         )
#         db.add(seed_user)
#         db.commit()
#
#         # ── Test 1: create_workspace() ───────────────────────────────────────
#         ws = repo.create_workspace(
#             db,
#             user_id=user_id,
#             name="Research",
#             description="AI papers workspace",
#         )
#         db.commit()
#         assert ws.id is not None, "Workspace must have an id after flush"
#         assert ws.chroma_collection == f"workspace_{ws.id}", "chroma_collection mismatch"
#         print(f"\n[1] create_workspace : OK — {ws}")
#         print(f"    chroma_collection  : {ws.chroma_collection}")
#
#         # ── Test 2: get_workspace_by_id() ────────────────────────────────────
#         fetched = repo.get_workspace_by_id(db, ws.id)
#         assert fetched is not None, "Should find workspace by id"
#         assert fetched.name == "Research"
#         print(f"\n[2] get_by_id        : OK — found {fetched.name!r}")
#
#         missing = repo.get_workspace_by_id(db, uuid.uuid4())
#         assert missing is None, "Should return None for unknown id"
#         print("    get_by_id (miss)   : OK — returned None for unknown UUID")
#
#         # ── Test 3: get_workspace_by_id_and_user() ───────────────────────────
#         owned = repo.get_workspace_by_id_and_user(db, ws.id, user_id)
#         assert owned is not None, "Should find workspace owned by user"
#         print(f"\n[3] get_by_id+user   : OK — found workspace for correct owner")
#
#         not_owned = repo.get_workspace_by_id_and_user(db, ws.id, other_user_id)
#         assert not_owned is None, "Should return None for wrong owner"
#         print("    wrong owner        : OK — returned None")
#
#         # ── Test 4: get_user_workspaces() ────────────────────────────────────
#         ws2 = repo.create_workspace(db, user_id=user_id, name="Personal")
#         ws3 = repo.create_workspace(db, user_id=user_id, name="Work")
#         db.commit()
#         all_ws = repo.get_user_workspaces(db, user_id)
#         assert len(all_ws) == 3, f"Expected 3 workspaces, got {len(all_ws)}"
#         print(f"\n[4] get_user_workspaces : OK — returned {len(all_ws)} workspaces")
#         for w in all_ws:
#             print(f"    {w.name}")
#
#         # ── Test 5: count_user_workspaces() ──────────────────────────────────
#         count = repo.count_user_workspaces(db, user_id)
#         assert count == 3, f"Expected count 3, got {count}"
#         print(f"\n[5] count_user_workspaces : OK — count = {count}")
#
#         # ── Test 6: update_workspace() ───────────────────────────────────────
#         updated = repo.update_workspace(
#             db, ws, name="AI Research", description="Updated description"
#         )
#         db.commit()
#         assert updated.name == "AI Research"
#         assert updated.description == "Updated description"
#         print(f"\n[6] update_workspace : OK — name={updated.name!r}, desc={updated.description!r}")
#
#         # ── Test 7: get_workspace_by_chroma_collection() ─────────────────────
#         resolved = repo.get_workspace_by_chroma_collection(db, ws.chroma_collection)
#         assert resolved is not None, "Should find workspace by chroma collection name"
#         assert resolved.id == ws.id
#         print(f"\n[7] get_by_chroma_collection : OK — resolved workspace id={resolved.id}")
#
#         # ── Test 8: delete_workspace_by_id() ─────────────────────────────────
#         # Wrong user should fail
#         result_wrong = repo.delete_workspace_by_id(db, ws.id, other_user_id)
#         assert result_wrong is False, "Should return False for wrong owner"
#         print(f"\n[8] delete (wrong user) : OK — returned {result_wrong}")
#
#         # Correct user should succeed
#         result_ok = repo.delete_workspace_by_id(db, ws.id, user_id)
#         db.commit()
#         assert result_ok is True, "Should return True after successful delete"
#         gone = repo.get_workspace_by_id(db, ws.id)
#         assert gone is None, "Workspace should not exist after deletion"
#         print(f"    delete (owner)      : OK — returned {result_ok}, workspace gone")
#
#         # Remaining count should be 2
#         remaining_count = repo.count_user_workspaces(db, user_id)
#         assert remaining_count == 2, f"Expected 2 remaining, got {remaining_count}"
#         print(f"    remaining count     : OK — {remaining_count} workspace(s) left")
#
#     finally:
#         db.close()
#         drop_all_tables()
#         db_path = DATABASE_URL.replace("sqlite:///", "").replace("./", "")
#         if os.path.exists(db_path):
#             os.remove(db_path)
#             print(f"\n    Cleaned up test DB: {db_path}")
#
#     print("\n" + "=" * 60)
#     print("All workspace.py repository tests passed.")
#     print("=" * 60)
