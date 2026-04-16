from backend.core.auth import create_access_token, hash_password, verify_password
from backend.storage.repositories.user import UserRepository


class AuthService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def register(self, *, email: str, username: str, password: str) -> tuple[str, str]:
        normalized_email = email.strip().lower()
        normalized_username = username.strip()

        if len(normalized_username) < 3:
            raise ValueError("Username must be at least 3 characters")

        existing = self._repo.get_by_email(normalized_email)
        if existing is not None:
            raise ValueError("Email already registered")

        existing_username = self._repo.get_by_username(normalized_username)
        if existing_username is not None:
            raise ValueError("Username already taken")

        hashed = hash_password(password)
        user = self._repo.create(email=normalized_email, username=normalized_username, hashed_password=hashed)

        token = create_access_token(subject=user.id)
        return token, "bearer"

    def login(self, *, email: str, password: str) -> tuple[str, str]:
        # OAuth2PasswordRequestForm uses the "username" field. Accept both
        # email and username here for compatibility with existing clients.
        identifier = email.strip()
        user = self._repo.get_by_email(identifier.lower())
        if user is None:
            user = self._repo.get_by_username(identifier)
        if user is None:
            raise ValueError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        token = create_access_token(subject=user.id)
        return token, "bearer"
