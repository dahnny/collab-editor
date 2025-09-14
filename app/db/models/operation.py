from sqlalchemy import String, Column, Integer, ForeignKey, Text, TIMESTAMP, text
from sqlalchemy.orm import relationship
from app.db.models.base import Base


class Operation(Base):
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    base_version = Column(Integer, nullable=False)  # Document version before this operation
    position = Column(Integer, nullable=False)
    insert_text = Column(Text, nullable=True)  # Text to insert
    delete_len = Column(Integer, nullable=True)  # Length of text to delete
    applied_version = Column(Integer, nullable=False)  # Document version after this operation
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    document = relationship("Document")
    user = relationship("User")
