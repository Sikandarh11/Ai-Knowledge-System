from uuid import uuid4

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base

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
    content = Column(Text, nullable=False)

    workspace = relationship("Workspace", back_populates="documents")