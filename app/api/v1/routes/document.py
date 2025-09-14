from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.db.models.user import User

from app.db.schemas.document import DocCreate
from app.db.schemas.operation import OperationOut
from app.db.crud.document import create_document, get_document, get_documents_operations


router = APIRouter(prefix="/docs", tags=["documents"])


@router.post("/")
def create_doc(
    doc_in: DocCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_doc = create_document(db, doc_in, current_user)
    return new_doc

@router.get("/{doc_id}")
def get_doc(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/{doc_id}/ops", response_model=List[OperationOut])
def get_doc_ops(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ops = get_documents_operations(db, doc_id)
    if not ops:
        raise HTTPException(status_code=404, detail="No operations found for this document")
    return ops