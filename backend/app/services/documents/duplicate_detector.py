"""Duplicate detection.

Two independent checks, per the product requirement:

1. Exact file duplicate: same SHA-256 hash already stored.
2. Logical duplicate: a different file that nonetheless matches on
   date + amount + supplier (name or CNPJ/CPF) + document number —
   catches a re-scanned or re-photographed copy of the same receipt.

Neither check auto-merges or deletes anything; both only flag the new
document as `possible_duplicate` for a human to confirm.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


@dataclass
class DuplicateCheckResult:
    is_possible_duplicate: bool = False
    duplicate_document_id: str | None = None
    reasons: list[str] = field(default_factory=list)


def find_hash_duplicate(db: Session, sha256_hash: str) -> Document | None:
    stmt = select(Document).where(Document.sha256_hash == sha256_hash).limit(1)
    return db.execute(stmt).scalar_one_or_none()


def find_logical_duplicate(
    db: Session,
    *,
    extracted_date: date | None,
    extracted_amount: Decimal | None,
    supplier_name: str | None,
    cnpj: str | None,
    cpf: str | None,
    document_number: str | None,
) -> Document | None:
    """Best-effort match on business fields. Requires amount + date at minimum,
    plus at least one identifying field (supplier, CNPJ/CPF or document number),
    to avoid false positives on sparse OCR results."""
    if extracted_amount is None or extracted_date is None:
        return None
    identifying = [v for v in (cnpj, cpf, document_number, supplier_name) if v]
    if not identifying:
        return None

    stmt = select(Document).where(
        Document.extracted_date == extracted_date,
        Document.extracted_amount == extracted_amount,
    )
    for candidate in db.execute(stmt).scalars():
        if cnpj and candidate.extracted_cnpj == cnpj:
            return candidate
        if cpf and candidate.extracted_cpf == cpf:
            return candidate
        if document_number and candidate.extracted_document_number == document_number:
            return candidate
        if supplier_name and candidate.extracted_supplier_name and (
            supplier_name.strip().lower() == candidate.extracted_supplier_name.strip().lower()
        ):
            return candidate
    return None


def check_duplicates(
    db: Session,
    *,
    sha256_hash: str,
    extracted_date: date | None = None,
    extracted_amount: Decimal | None = None,
    supplier_name: str | None = None,
    cnpj: str | None = None,
    cpf: str | None = None,
    document_number: str | None = None,
) -> DuplicateCheckResult:
    result = DuplicateCheckResult()

    hash_match = find_hash_duplicate(db, sha256_hash)
    if hash_match is not None:
        result.is_possible_duplicate = True
        result.duplicate_document_id = hash_match.id
        result.reasons.append("same_file_hash")
        return result

    logical_match = find_logical_duplicate(
        db,
        extracted_date=extracted_date,
        extracted_amount=extracted_amount,
        supplier_name=supplier_name,
        cnpj=cnpj,
        cpf=cpf,
        document_number=document_number,
    )
    if logical_match is not None:
        result.is_possible_duplicate = True
        result.duplicate_document_id = logical_match.id
        result.reasons.append("matching_date_amount_and_identifier")

    return result
