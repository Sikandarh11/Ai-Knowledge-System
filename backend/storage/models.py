from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from backend.storage.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, default="Work")
    description = Column(Text, nullable=True)
    owner_id = Column(String(255), index=True, nullable=True)

    documents = relationship("Document", back_populates="workspace", cascade="all, delete")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    filename = Column(String(255), nullable=False, default="document.txt")
    file_type = Column(String(32), nullable=False, default="txt")
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    content = Column(Text, nullable=False)

    workspace = relationship("Workspace", back_populates="documents")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(64), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("user_id", "email", name="uq_contacts_user_email"),
    )

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    source = Column(String(32), nullable=False, default="manual")
    frequency = Column(Integer, nullable=False, default=1)
    last_used = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
