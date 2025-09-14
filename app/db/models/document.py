import uuid
from sqlalchemy import TIMESTAMP, Column, Integer, String, Text, ForeignKey, text
from sqlalchemy.orm import relationship
from app.db.models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True, default="Untitled Document")
    content = Column(Text)
    version = Column(Integer, default=0)
    owner_id = Column(String, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'), onupdate=text('now()'), nullable=False)

    owner = relationship("User")
