from sqlalchemy.orm import Session

from backend.storage.models import User


class UserRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_by_email(self, email: str) -> User | None:
        return self._db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> User | None:
        return self._db.query(User).filter(User.username == username).first()

    def create(self, *, email: str, username: str, hashed_password: str) -> User:
        user = User(email=email, username=username, hashed_password=hashed_password)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user
