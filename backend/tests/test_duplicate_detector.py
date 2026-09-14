"""app/services/documents/duplicate_detector.py — the logical-duplicate
path (same date+amount+identifier across a DIFFERENT file hash, e.g. a
re-scanned receipt) had zero test coverage before this file; only the
fast exact-hash path was exercised elsewhere (tests/test_documents.py)."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.models.document import Document
from app.services.documents.duplicate_detector import (
    check_duplicates,
    find_hash_duplicate,
    find_logical_duplicate,
)


def _document(db_session, **overrides) -> Document:
    defaults = dict(
        original_filename="doc.pdf",
        mime_type="application/pdf",
        file_extension="pdf",
        file_size_bytes=10,
        sha256_hash=uuid.uuid4().hex,
        original_path="originals/doc.pdf",
    )
    defaults.update(overrides)
    doc = Document(**defaults)
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def test_find_hash_duplicate_matches_exact_hash(db_session):
    existing = _document(db_session, sha256_hash="abc123")
    match = find_hash_duplicate(db_session, "abc123")
    assert match is not None
    assert match.id == existing.id


def test_find_hash_duplicate_no_match_for_unknown_hash(db_session):
    assert find_hash_duplicate(db_session, "never-seen-hash") is None


def test_logical_duplicate_matches_by_cnpj(db_session):
    existing = _document(
        db_session,
        extracted_date=date(2024, 3, 1),
        extracted_amount=Decimal("150.00"),
        extracted_cnpj="12.345.678/0001-99",
    )
    match = find_logical_duplicate(
        db_session,
        extracted_date=date(2024, 3, 1),
        extracted_amount=Decimal("150.00"),
        supplier_name=None,
        cnpj="12.345.678/0001-99",
        cpf=None,
        document_number=None,
    )
    assert match is not None
    assert match.id == existing.id


def test_logical_duplicate_matches_by_cpf(db_session):
    existing = _document(
        db_session, extracted_date=date(2024, 4, 1), extracted_amount=Decimal("75.50"), extracted_cpf="123.456.789-00"
    )
    match = find_logical_duplicate(
        db_session,
        extracted_date=date(2024, 4, 1),
        extracted_amount=Decimal("75.50"),
        supplier_name=None,
        cnpj=None,
        cpf="123.456.789-00",
        document_number=None,
    )
    assert match is not None and match.id == existing.id


def test_logical_duplicate_matches_by_document_number(db_session):
    existing = _document(
        db_session,
        extracted_date=date(2024, 5, 1),
        extracted_amount=Decimal("300.00"),
        extracted_document_number="NF-12345",
    )
    match = find_logical_duplicate(
        db_session,
        extracted_date=date(2024, 5, 1),
        extracted_amount=Decimal("300.00"),
        supplier_name=None,
        cnpj=None,
        cpf=None,
        document_number="NF-12345",
    )
    assert match is not None and match.id == existing.id


def test_logical_duplicate_matches_by_supplier_name_case_insensitive(db_session):
    existing = _document(
        db_session,
        extracted_date=date(2024, 6, 1),
        extracted_amount=Decimal("50.00"),
        extracted_supplier_name="Gráfica São José",
    )
    match = find_logical_duplicate(
        db_session,
        extracted_date=date(2024, 6, 1),
        extracted_amount=Decimal("50.00"),
        supplier_name="  GRÁFICA SÃO JOSÉ  ",
        cnpj=None,
        cpf=None,
        document_number=None,
    )
    assert match is not None and match.id == existing.id


def test_logical_duplicate_no_match_when_amount_differs(db_session):
    _document(
        db_session, extracted_date=date(2024, 7, 1), extracted_amount=Decimal("100.00"), extracted_cnpj="11.111.111/0001-11"
    )
    match = find_logical_duplicate(
        db_session,
        extracted_date=date(2024, 7, 1),
        extracted_amount=Decimal("200.00"),  # different
        supplier_name=None,
        cnpj="11.111.111/0001-11",
        cpf=None,
        document_number=None,
    )
    assert match is None


def test_logical_duplicate_no_match_when_date_differs(db_session):
    _document(
        db_session, extracted_date=date(2024, 8, 1), extracted_amount=Decimal("100.00"), extracted_cnpj="22.222.222/0001-22"
    )
    match = find_logical_duplicate(
        db_session,
        extracted_date=date(2024, 8, 2),  # different
        extracted_amount=Decimal("100.00"),
        supplier_name=None,
        cnpj="22.222.222/0001-22",
        cpf=None,
        document_number=None,
    )
    assert match is None


def test_logical_duplicate_requires_date_and_amount():
    """Sparse OCR results (missing date or amount) must never be treated
    as a duplicate match, even with an identifier — avoids false
    positives on documents OCR barely extracted anything from."""
    assert (
        find_logical_duplicate(
            None,  # never reaches the query — short-circuits before touching db
            extracted_date=None,
            extracted_amount=Decimal("100.00"),
            supplier_name=None,
            cnpj="33.333.333/0001-33",
            cpf=None,
            document_number=None,
        )
        is None
    )


def test_logical_duplicate_requires_at_least_one_identifying_field(db_session):
    _document(db_session, extracted_date=date(2024, 9, 1), extracted_amount=Decimal("100.00"))
    match = find_logical_duplicate(
        db_session,
        extracted_date=date(2024, 9, 1),
        extracted_amount=Decimal("100.00"),
        supplier_name=None,
        cnpj=None,
        cpf=None,
        document_number=None,
    )
    assert match is None


def test_check_duplicates_prefers_hash_match_over_logical_match(db_session):
    """When both would match, the cheaper/more certain hash check wins and
    is the only reason reported."""
    existing = _document(
        db_session,
        sha256_hash="shared-hash",
        extracted_date=date(2024, 10, 1),
        extracted_amount=Decimal("100.00"),
        extracted_cnpj="44.444.444/0001-44",
    )
    result = check_duplicates(
        db_session,
        sha256_hash="shared-hash",
        extracted_date=date(2024, 10, 1),
        extracted_amount=Decimal("100.00"),
        cnpj="44.444.444/0001-44",
    )
    assert result.is_possible_duplicate is True
    assert result.duplicate_document_id == existing.id
    assert result.reasons == ["same_file_hash"]


def test_check_duplicates_falls_back_to_logical_match(db_session):
    existing = _document(
        db_session,
        extracted_date=date(2024, 11, 1),
        extracted_amount=Decimal("250.00"),
        extracted_document_number="NF-999",
    )
    result = check_duplicates(
        db_session,
        sha256_hash="a-completely-different-hash",
        extracted_date=date(2024, 11, 1),
        extracted_amount=Decimal("250.00"),
        document_number="NF-999",
    )
    assert result.is_possible_duplicate is True
    assert result.duplicate_document_id == existing.id
    assert result.reasons == ["matching_date_amount_and_identifier"]


def test_check_duplicates_no_match_at_all(db_session):
    result = check_duplicates(
        db_session,
        sha256_hash="totally-unique-hash",
        extracted_date=date(2024, 12, 1),
        extracted_amount=Decimal("500.00"),
        supplier_name="Fornecedor Nunca Visto",
    )
    assert result.is_possible_duplicate is False
    assert result.duplicate_document_id is None
    assert result.reasons == []
