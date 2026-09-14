from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus, OCRConfidence


class DocumentItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str | None
    quantity: Decimal | None
    unit_value: Decimal | None
    total_value: Decimal | None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str | None
    original_filename: str
    mime_type: str
    file_extension: str
    file_size_bytes: int
    sha256_hash: str
    status: DocumentStatus
    ocr_confidence: OCRConfidence
    ocr_text: str | None
    extracted_date: date | None
    extracted_amount: Decimal | None
    extracted_supplier_name: str | None
    extracted_razao_social: str | None
    extracted_cnpj: str | None
    extracted_cpf: str | None
    extracted_description: str | None
    extracted_document_number: str | None
    extracted_payment_method: str | None
    possible_duplicate_of_id: str | None
    processing_error: str | None
    items: list[DocumentItemRead] = []
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    possible_duplicate: bool = False
    duplicate_reasons: list[str] = []


class DocumentCorrection(BaseModel):
    """Manual correction of extracted fields. Every change is written to the audit log."""

    extracted_date: date | None = None
    extracted_amount: Decimal | None = None
    extracted_supplier_name: str | None = None
    extracted_razao_social: str | None = None
    extracted_cnpj: str | None = None
    extracted_cpf: str | None = None
    extracted_description: str | None = None
    extracted_document_number: str | None = None
    extracted_payment_method: str | None = None
