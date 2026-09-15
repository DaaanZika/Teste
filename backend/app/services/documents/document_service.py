"""Document upload/processing orchestration.

Implements the pipeline from PROMPT 1 section 6:

    UPLOAD -> VALIDACAO -> HASH -> VERIFICA DUPLICIDADE -> SALVA ORIGINAL
    -> PROCESSAMENTO -> OCR -> EXTRACAO -> VALIDACAO -> BANCO

`upload_document` covers everything through "salva original" plus the
hash-based duplicate check (fast, no OCR needed yet). `process_document`
runs OCR/extraction and the logical duplicate check, which needs extracted
fields to exist. They're split into two steps (and two API calls) instead
of one long synchronous request so a slow OCR pass never blocks the
upload response — see PROMPT 1 section 28 on keeping OCR decoupled from
the request/response cycle even while V1 runs it in-process.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    DocumentProcessingError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedFileTypeError,
)
from app.integrations.storage_adapter import get_storage_provider, get_storage_provider_for_document
from app.models.campaign import Campaign
from app.models.document import Document, DocumentItem
from app.models.enums import (
    AlertType,
    AuditAction,
    DocumentStatus,
    OCRConfidence,
    ProcessingJobStatus,
    ProcessingJobType,
)
from app.models.processing_job import ProcessingJob
from app.services.audit.audit_service import record as record_audit
from app.services.compliance.alerts import raise_alert
from app.services.documents import backup_service
from app.services.documents.duplicate_detector import DuplicateCheckResult, check_duplicates, find_hash_duplicate
from app.services.documents.hashing import sha256_hex
from app.services.ocr.confidence import requires_human_review, score_confidence
from app.services.ocr.engine import run_ocr
from app.services.ocr.extractor import extract_fields
from app.utils.files import sanitize_filename

logger = logging.getLogger("app.documents")


@dataclass
class UploadResult:
    document: Document
    possible_duplicate: bool
    duplicate_reasons: list[str]


def _validate_upload(filename: str, content: bytes, mime_type: str) -> str:
    settings = get_settings()
    safe_name = sanitize_filename(filename)
    extension = ("." + safe_name.rsplit(".", 1)[-1].lower()) if "." in safe_name else ""

    if extension not in settings.allowed_upload_extensions:
        raise UnsupportedFileTypeError(
            f"Extensão '{extension}' não suportada. Formatos aceitos: "
            f"{', '.join(settings.allowed_upload_extensions)}."
        )
    if mime_type not in settings.allowed_upload_mime_types:
        raise UnsupportedFileTypeError(f"Tipo de arquivo '{mime_type}' não suportado.")
    if len(content) == 0:
        raise UnsupportedFileTypeError("Arquivo vazio.")
    if len(content) > settings.max_upload_size_bytes:
        raise FileTooLargeError(
            f"Arquivo excede o limite de {settings.max_upload_size_bytes // (1024 * 1024)} MB."
        )
    return extension


def upload_document(
    db: Session,
    *,
    filename: str,
    content: bytes,
    mime_type: str,
    organization_id: str,
    campaign_id: str | None = None,
    user_id: str | None = None,
) -> UploadResult:
    """`organization_id` (PROMPT 4) scopes duplicate detection — a hash/
    field match in a different organization must never be surfaced to this
    caller. `campaign_id`, when given, is trusted to already belong to
    `organization_id` (the route resolves/validates it first — see
    app.core.tenancy.resolve_campaign_id)."""
    extension = _validate_upload(filename, content, mime_type)
    file_hash = sha256_hex(content)

    # Exact-file duplicate (section 7): do NOT create a new document record
    # automatically. Surface the existing one with `possible_duplicate=True`
    # instead — the human decides whether to keep it, not the pipeline.
    hash_match = find_hash_duplicate(db, file_hash, organization_id=organization_id)
    if hash_match is not None:
        raise_alert(
            db,
            type=AlertType.HUMAN_REVIEW,
            title="Documento duplicado",
            message=(
                f"O arquivo enviado ('{sanitize_filename(filename)}') é idêntico ao documento "
                f"já cadastrado {hash_match.id}. Nenhum novo documento foi criado."
            ),
            entity="document",
            entity_id=hash_match.id,
            campaign_id=campaign_id,
        )
        db.commit()
        db.refresh(hash_match)
        return UploadResult(document=hash_match, possible_duplicate=True, duplicate_reasons=["same_file_hash"])

    settings = get_settings()
    storage = get_storage_provider(db)
    original_path = storage.save_original(filename, content, campaign_id=campaign_id)

    document = Document(
        campaign_id=campaign_id,
        original_filename=sanitize_filename(filename),
        mime_type=mime_type,
        file_extension=extension,
        file_size_bytes=len(content),
        sha256_hash=file_hash,
        original_path=original_path,
        storage_provider=settings.storage_provider,
        external_storage_id=original_path if settings.storage_provider != "local" else None,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    db.flush()

    record_audit(
        db,
        entity="document",
        entity_id=document.id,
        action=AuditAction.CREATE,
        new_value={"filename": document.original_filename, "sha256_hash": file_hash},
        user_id=user_id,
    )

    db.commit()
    db.refresh(document)

    backup_service.backup_document(db, document, content=content, filename=filename)

    return UploadResult(document=document, possible_duplicate=False, duplicate_reasons=[])


def get_document(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError(f"Documento {document_id} não encontrado.")
    return document


def get_document_in_org(db: Session, document_id: str, *, organization_id: str) -> Document:
    """Like get_document, but 404s (never a bare 403 — no cross-org
    existence leak) for a document outside `organization_id`, even one
    that genuinely exists. Every route reachable by an organization-scoped
    caller uses this, not the plain get_document above."""
    document = db.get(Document, document_id)
    if document is None or document.campaign_id is None:
        raise NotFoundError(f"Documento {document_id} não encontrado.")
    campaign = db.get(Campaign, document.campaign_id)
    if campaign is None or campaign.organization_id != organization_id:
        raise NotFoundError(f"Documento {document_id} não encontrado.")
    return document


def list_documents(
    db: Session,
    *,
    organization_id: str,
    status: DocumentStatus | None = None,
    campaign_id: str | None = None,
) -> list[Document]:
    stmt = (
        select(Document)
        .join(Campaign, Document.campaign_id == Campaign.id)
        .where(Campaign.organization_id == organization_id)
        .order_by(Document.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(Document.status == status)
    if campaign_id is not None:
        stmt = stmt.where(Document.campaign_id == campaign_id)
    return list(db.execute(stmt).scalars())


def mark_queued_for_processing(db: Session, document_id: str) -> Document:
    """Used by the QUEUE_BACKEND=redis route path (app/api/routes/documents.py):
    marks the document PROCESSING and returns immediately — the actual OCR
    pipeline runs later, out of the request/response cycle, in
    app.queue.worker via the exact same `process_document` below that the
    default synchronous ("inline") path calls directly."""
    document = get_document(db, document_id)
    document.status = DocumentStatus.PROCESSING
    db.commit()
    db.refresh(document)
    return document


def process_document(db: Session, document_id: str, *, user_id: str | None = None) -> Document:
    """Runs OCR + extraction for a document and persists the results.

    Never raises for an OCR failure: the document is marked FAILED /
    HUMAN_REVIEW with `processing_error` set instead, so a bad scan never
    takes down the API (PROMPT 1 section 25).
    """
    document = get_document(db, document_id)
    settings = get_settings()

    job = ProcessingJob(
        document_id=document.id, type=ProcessingJobType.DOCUMENT_PROCESSING, status=ProcessingJobStatus.RUNNING
    )
    db.add(job)
    document.status = DocumentStatus.PROCESSING
    db.commit()
    db.refresh(job)

    try:
        storage = get_storage_provider_for_document(db, document.storage_provider)
        original_bytes = storage.read(document.original_path)

        ocr_result = run_ocr(original_bytes, document.mime_type, language=settings.ocr_language)

        if not ocr_result.engine_available:
            document.status = DocumentStatus.HUMAN_REVIEW
            document.ocr_confidence = OCRConfidence.NONE
            document.processing_error = (
                "Mecanismo de OCR indisponível (Tesseract não encontrado). "
                "Revisão humana necessária."
            )
            job.status = ProcessingJobStatus.FAILED
            job.error_message = ocr_result.error
            raise_alert(
                db,
                type=AlertType.HUMAN_REVIEW,
                title="OCR indisponível",
                message=f"Não foi possível executar OCR no documento {document.id}: {ocr_result.error}",
                entity="document",
                entity_id=document.id,
                campaign_id=document.campaign_id,
            )
            db.commit()
            db.refresh(document)
            return document

        extracted = extract_fields(ocr_result.text)
        confidence = score_confidence(
            engine_available=ocr_result.engine_available,
            mean_ocr_confidence=ocr_result.mean_confidence,
            extracted=extracted,
        )

        document.ocr_text = ocr_result.text or None
        document.ocr_confidence = confidence
        document.extracted_date = extracted.data
        document.extracted_amount = extracted.valor
        document.extracted_supplier_name = extracted.fornecedor
        document.extracted_razao_social = extracted.razao_social
        document.extracted_cnpj = extracted.cnpj
        document.extracted_cpf = extracted.cpf
        document.extracted_description = extracted.descricao
        document.extracted_document_number = extracted.numero_documento
        document.extracted_payment_method = extracted.forma_pagamento
        document.processing_error = None

        for item in extracted.itens:
            db.add(
                DocumentItem(
                    document_id=document.id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_value=item.unit_value,
                    total_value=item.total_value,
                )
            )

        # Derived from the document's own (already org-resolved-at-upload)
        # campaign — process_document runs from the async worker with no
        # request/session context, so organization_id can't come from a
        # dependency here the way it does in the upload/list/get routes.
        campaign = db.get(Campaign, document.campaign_id) if document.campaign_id else None
        logical_duplicate = (
            check_duplicates(
                db,
                organization_id=campaign.organization_id,
                sha256_hash=document.sha256_hash,
                extracted_date=extracted.data,
                extracted_amount=extracted.valor,
                supplier_name=extracted.fornecedor,
                cnpj=extracted.cnpj,
                cpf=extracted.cpf,
                document_number=extracted.numero_documento,
            )
            if campaign is not None
            else DuplicateCheckResult()
        )
        if logical_duplicate.is_possible_duplicate and logical_duplicate.duplicate_document_id != document.id:
            document.status = DocumentStatus.POSSIBLE_DUPLICATE
            document.possible_duplicate_of_id = logical_duplicate.duplicate_document_id
            raise_alert(
                db,
                type=AlertType.HUMAN_REVIEW,
                title="Possível duplicidade lógica",
                message=(
                    f"O documento {document.id} coincide em data, valor e identificador com o "
                    f"documento {logical_duplicate.duplicate_document_id}."
                ),
                entity="document",
                entity_id=document.id,
                campaign_id=document.campaign_id,
            )
        elif requires_human_review(confidence):
            document.status = DocumentStatus.HUMAN_REVIEW
            raise_alert(
                db,
                type=AlertType.HUMAN_REVIEW,
                title="Documento ilegível ou com baixa confiança",
                message=f"O documento {document.id} foi processado com confiança {confidence.value}.",
                entity="document",
                entity_id=document.id,
                campaign_id=document.campaign_id,
            )
        else:
            document.status = DocumentStatus.PROCESSED

        job.status = ProcessingJobStatus.COMPLETED

        record_audit(
            db,
            entity="document",
            entity_id=document.id,
            action=AuditAction.UPDATE,
            new_value={"status": document.status.value, "ocr_confidence": confidence.value},
            user_id=user_id,
        )

        db.commit()
        db.refresh(document)
        return document

    except Exception as exc:  # noqa: BLE001 - convert any unexpected failure into a safe state
        db.rollback()
        document = get_document(db, document_id)
        document.status = DocumentStatus.FAILED
        document.processing_error = "Falha inesperada ao processar o documento."
        logger.exception("Document processing failed for %s", document_id)
        job = db.get(ProcessingJob, job.id)
        if job is not None:
            job.status = ProcessingJobStatus.FAILED
            job.error_message = str(exc)
        raise_alert(
            db,
            type=AlertType.ERROR,
            title="Falha no processamento do documento",
            message=f"Não foi possível processar o documento {document_id}.",
            entity="document",
            entity_id=document_id,
            campaign_id=document.campaign_id,
        )
        db.commit()
        raise DocumentProcessingError("Não foi possível processar o documento.") from exc


def apply_manual_correction(
    db: Session, document_id: str, corrections: dict, *, user_id: str | None = None
) -> Document:
    """Applies a human correction to extracted fields. Always audited (section 9).

    `corrections` keys are the `Document` attribute names directly (e.g.
    `extracted_amount`), matching `schemas.document.DocumentCorrection`.
    """
    document = get_document(db, document_id)
    old_values = {}
    new_values = {}
    for field_name, value in corrections.items():
        if value is None or not hasattr(document, field_name):
            continue
        old_values[field_name] = getattr(document, field_name, None)
        setattr(document, field_name, value)
        new_values[field_name] = value

    if new_values:
        if document.status in (DocumentStatus.HUMAN_REVIEW, DocumentStatus.POSSIBLE_DUPLICATE):
            document.status = DocumentStatus.PROCESSED
        record_audit(
            db,
            entity="document",
            entity_id=document.id,
            action=AuditAction.MANUAL_CORRECTION,
            old_value=old_values,
            new_value=new_values,
            user_id=user_id,
        )
        db.commit()
        db.refresh(document)

    return document
