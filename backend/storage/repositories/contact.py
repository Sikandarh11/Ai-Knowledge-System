from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.storage.models import Contact


class ContactRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_by_user_and_email(self, user_id: str, email: str) -> Contact | None:
        return (
            self._db.query(Contact)
            .filter(Contact.user_id == user_id, Contact.email == email.lower().strip())
            .first()
        )

    def get_exact_name(self, user_id: str, name: str) -> list[Contact]:
        normalized = name.strip().lower()
        if not normalized:
            return []
        return (
            self._db.query(Contact)
            .filter(Contact.user_id == user_id)
            .filter(func.lower(Contact.name) == normalized)
            .all()
        )

    def search_candidates(self, user_id: str, name: str, limit: int = 15) -> list[Contact]:
        normalized = name.strip().lower()
        if not normalized:
            return []
        pattern = f"%{normalized}%"
        return (
            self._db.query(Contact)
            .filter(Contact.user_id == user_id)
            .filter(
                func.lower(Contact.name).like(pattern)
                | func.lower(Contact.email).like(pattern)
            )
            .order_by(Contact.frequency.desc(), Contact.last_used.desc())
            .limit(max(1, limit))
            .all()
        )

    def upsert_contact(
        self,
        *,
        user_id: str,
        name: str,
        email: str,
        source: str,
        frequency_increment: int = 1,
        touch_last_used: bool = True,
    ) -> Contact:
        normalized_email = email.strip().lower()
        row = self.get_by_user_and_email(user_id, normalized_email)

        if row is None:
            row = Contact(
                user_id=user_id,
                name=name.strip() or normalized_email,
                email=normalized_email,
                source=source,
                frequency=max(1, int(frequency_increment)),
                last_used=datetime.now(timezone.utc),
            )
            self._db.add(row)
        else:
            row.name = name.strip() or row.name
            row.source = source or row.source
            row.frequency = int(row.frequency or 0) + max(1, int(frequency_increment))
            if touch_last_used:
                row.last_used = datetime.now(timezone.utc)

        self._db.commit()
        self._db.refresh(row)
        return row

    def list_by_user(
        self,
        *,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Contact]:
        return (
            self._db.query(Contact)
            .filter(Contact.user_id == user_id)
            .order_by(Contact.frequency.desc(), Contact.last_used.desc(), Contact.name.asc())
            .limit(max(1, limit))
            .offset(max(0, offset))
            .all()
        )

    def count_by_user(self, *, user_id: str) -> int:
        return int(
            self._db.query(func.count(Contact.id))
            .filter(Contact.user_id == user_id)
            .scalar()
            or 0
        )
