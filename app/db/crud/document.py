from sqlalchemy.orm import Session
from app.db.models import Document, User, Operation
from app.db.schemas.document import DocCreate


def create_document(db: Session, doc: DocCreate, owner: User) -> Document:
    """Create a new document in the database."""
    db_doc = Document(
        title=doc.title, content=doc.content, version=0, owner_id=owner.id
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


def get_document(db: Session, doc_id: str) -> Document | None:
    """Retrieve a document by its ID."""
    return db.query(Document).filter(Document.id == doc_id).first()


def get_documents_operations(db: Session, doc_id: str):
    """Retrieve operations associated with a document."""
    ops = (
        db.query(Operation)
        .filter(Operation.document_id == doc_id)
        .order_by(Operation.id.asc())
        .all()
    )
    return ops
