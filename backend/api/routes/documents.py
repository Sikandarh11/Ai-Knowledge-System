from fastapi import APIRouter, Depends, File, HTTPException, Form, UploadFile
from sqlalchemy.orm import Session

from backend.services.document_service import DocumentService
from backend.storage.database import get_db
from backend.storage.schemas import DocumentCreate, DocumentRead

router = APIRouter(prefix="/documents", tags=["documents"])


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    service = DocumentService(db)
    deleted = service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}


@router.post("", response_model=DocumentRead)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    service = DocumentService(db)
    return service.create_document(workspace_id=payload.workspace_id, content=payload.content)


@router.get("", response_model=list[DocumentRead])
def list_documents(workspace_id: int, db: Session = Depends(get_db)):
    service = DocumentService(db)
    return service.list_documents(workspace_id)


@router.post("/upload")
async def upload_document_file(
    workspace_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    service = DocumentService(db)
    return await service.upload_document_file(workspace_id=workspace_id, file=file)
