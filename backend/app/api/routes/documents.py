from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.enums import DocumentStatus
from app.schemas.document import DocumentCorrection, DocumentRead, DocumentUploadResponse
from app.services.documents import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    campaign_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> DocumentUploadResponse:
    content = await file.read()
    result = document_service.upload_document(
        db,
        filename=file.filename or "documento",
        content=content,
        mime_type=file.content_type or "application/octet-stream",
        campaign_id=campaign_id,
        user_id=user_id,
    )
    return DocumentUploadResponse(
        document=DocumentRead.model_validate(result.document),
        possible_duplicate=result.possible_duplicate,
        duplicate_reasons=result.duplicate_reasons,
    )


@router.get("", response_model=list[DocumentRead])
def list_documents(
    status: DocumentStatus | None = None,
    campaign_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    documents = document_service.list_documents(db, status=status, campaign_id=campaign_id)
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentRead:
    document = document_service.get_document(db, document_id)
    return DocumentRead.model_validate(document)


@router.post("/{document_id}/process", response_model=DocumentRead)
def process_document(
    document_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> DocumentRead:
    document = document_service.process_document(db, document_id, user_id=user_id)
    return DocumentRead.model_validate(document)


@router.post("/{document_id}/ocr", response_model=DocumentRead)
def run_document_ocr(
    document_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> DocumentRead:
    """Alias of /process: OCR and field extraction run as one pipeline step in V1
    (see services.documents.document_service.process_document)."""
    document = document_service.process_document(db, document_id, user_id=user_id)
    return DocumentRead.model_validate(document)


@router.patch("/{document_id}/correct", response_model=DocumentRead)
def correct_document(
    document_id: str,
    correction: DocumentCorrection,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> DocumentRead:
    document = document_service.apply_manual_correction(
        db, document_id, correction.model_dump(exclude_unset=True), user_id=user_id
    )
    return DocumentRead.model_validate(document)
