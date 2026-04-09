from backend.core.auth import create_access_token, hash_password, verify_password
from backend.storage.repositories.user import UserRepository


class AuthService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def register(self, *, email: str, password: str) -> tuple[str, str]:
        normalized_email = email.strip().lower()
        existing = self._repo.get_by_email(normalized_email)
        if existing is not None:
            raise ValueError("Email already registered")

        hashed = hash_password(password)
        user = self._repo.create(email=normalized_email, hashed_password=hashed)

        token = create_access_token(subject=user.id)
        return token, "bearer"

    def login(self, *, email: str, password: str) -> tuple[str, str]:
        normalized_email = email.strip().lower()
        user = self._repo.get_by_email(normalized_email)
        if user is None:
            raise ValueError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        token = create_access_token(subject=user.id)
        return token, "bearer"
