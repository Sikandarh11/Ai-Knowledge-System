from __future__ import annotations

import difflib
from datetime import datetime, timezone
from typing import Any

from backend.storage.database import SessionLocal
from backend.storage.repositories.contact import ContactRepository


def _normalize_name(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _contact_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "name": row.name,
        "email": row.email,
        "source": row.source,
        "frequency": row.frequency,
        "last_used": row.last_used.isoformat() if row.last_used else None,
    }


def _rank_contacts(name: str, candidates: list[Any]) -> list[dict[str, Any]]:
    target = _normalize_name(name)
    ranked: list[dict[str, Any]] = []

    for row in candidates:
        name_ratio = difflib.SequenceMatcher(None, target, _normalize_name(row.name)).ratio()
        email_ratio = difflib.SequenceMatcher(None, target, (row.email or "").lower()).ratio()
        similarity = max(name_ratio, email_ratio)

        frequency_score = min(float(row.frequency or 0) / 50.0, 1.0)
        recency_score = 0.0
        if row.last_used:
            last_used = row.last_used
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (datetime.now(timezone.utc) - last_used).total_seconds() / 86400.0)
            recency_score = max(0.0, 1.0 - min(age_days / 30.0, 1.0))

        score = round((0.55 * similarity) + (0.30 * frequency_score) + (0.15 * recency_score), 4)

        item = _contact_to_dict(row)
        item["score"] = score
        ranked.append(item)

    ranked.sort(key=lambda item: (item["score"], item["frequency"], item["last_used"] or ""), reverse=True)
    return ranked


def resolve_contact(name: str, user_id: str) -> dict[str, Any]:
    """
    Resolve a recipient name from contacts table only (no runtime Gmail calls).

    Returns:
        {
            "status": "single" | "multiple" | "none",
            "contact": {...} | None,
            "options": [...]
        }
    """
    normalized = _normalize_name(name)
    if not normalized:
        return {"status": "none", "contact": None, "options": []}

    db = SessionLocal()
    try:
        repo = ContactRepository(db)

        exact = repo.get_exact_name(user_id=user_id, name=normalized)
        if len(exact) == 1:
            return {"status": "single", "contact": _contact_to_dict(exact[0]), "options": []}
        if len(exact) > 1:
            ranked_exact = _rank_contacts(normalized, exact)
            return {"status": "multiple", "contact": None, "options": ranked_exact}

        candidates = repo.search_candidates(user_id=user_id, name=normalized, limit=20)
        if not candidates:
            return {"status": "none", "contact": None, "options": []}

        ranked = _rank_contacts(normalized, candidates)
        if not ranked:
            return {"status": "none", "contact": None, "options": []}

        top = ranked[0]
        if len(ranked) == 1 or top["score"] >= 0.86:
            return {"status": "single", "contact": top, "options": []}

        if top["score"] >= 0.55:
            return {"status": "multiple", "contact": None, "options": ranked[:5]}

        return {"status": "none", "contact": None, "options": []}
    finally:
        db.close()


def upsert_contact(
    *,
    user_id: str,
    name: str,
    email: str,
    source: str = "manual",
    frequency_increment: int = 1,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        repo = ContactRepository(db)
        row = repo.upsert_contact(
            user_id=user_id,
            name=name,
            email=email,
            source=source,
            frequency_increment=frequency_increment,
            touch_last_used=True,
        )
        return _contact_to_dict(row)
    finally:
        db.close()


def bulk_upsert_contacts(user_id: str, contacts: list[dict[str, str]], source: str = "gmail") -> dict[str, Any]:
    db = SessionLocal()
    inserted_or_updated = 0
    try:
        repo = ContactRepository(db)
        for item in contacts:
            email = (item.get("email") or "").strip().lower()
            if not email:
                continue
            name = (item.get("name") or email.split("@", 1)[0]).strip()
            repo.upsert_contact(
                user_id=user_id,
                name=name,
                email=email,
                source=source,
                frequency_increment=1,
                touch_last_used=False,
            )
            inserted_or_updated += 1
        return {"success": True, "count": inserted_or_updated}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return {"success": False, "count": inserted_or_updated, "error": str(exc)}
    finally:
        db.close()
