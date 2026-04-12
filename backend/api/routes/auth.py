from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.services.auth_service import AuthService
from backend.services.gmail_sync_service import sync_contacts_for_user
from backend.storage.database import get_db
from backend.storage.models import User
from backend.storage.repositories.contact import ContactRepository
from backend.storage.repositories.user import UserRepository
from backend.storage.schemas import TokenResponse, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(UserRepository(db))
    try:
        access_token, token_type = service.register(
            email=payload.email,
            username=payload.username,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return TokenResponse(access_token=access_token, token_type=token_type)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return UserRead(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
    )


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username
    password = form_data.password

    service = AuthService(UserRepository(db))
    try:
        access_token, token_type = service.login(email=email, password=password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return TokenResponse(access_token=access_token, token_type=token_type)


@router.post("/sync-contacts")
def sync_contacts(current_user: User = Depends(get_current_user)):
    """
    Manually trigger contact sync for the authenticated user.
    """
    result = sync_contacts_for_user(user_id=str(current_user.id))
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result)
    return result


@router.get("/contacts")
def list_contacts(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ContactRepository(db)
    safe_limit = max(1, min(limit, 1000))
    safe_offset = max(0, offset)

    rows = repo.list_by_user(
        user_id=str(current_user.id),
        limit=safe_limit,
        offset=safe_offset,
    )
    total = repo.count_by_user(user_id=str(current_user.id))

    return {
        "total": total,
        "limit": safe_limit,
        "offset": safe_offset,
        "contacts": [
            {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "source": row.source,
                "frequency": row.frequency,
                "last_used": row.last_used.isoformat() if row.last_used else None,
            }
            for row in rows
        ],
    }
