from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentStatus, OCRConfidence


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A source document (receipt, invoice, contract, ...).

    The original file is never modified after upload. `original_path` and
    `processed_path` point at files on disk under `storage/`; only the
    storage *adapter* changes when we move to cloud storage later, this
    row stays the same shape.
    """

    __tablename__ = "documents"

    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)

    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    original_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    processed_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, native_enum=False, length=30),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )

    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[OCRConfidence] = mapped_column(
        SAEnum(OCRConfidence, native_enum=False, length=10),
        default=OCRConfidence.NONE,
        nullable=False,
    )

    # Extracted fields (nullable: "campo não encontrado = null", never guessed)
    extracted_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    extracted_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    extracted_supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extracted_razao_social: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extracted_cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    extracted_cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    extracted_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extracted_payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)

    possible_duplicate_of_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)

    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="documents")  # noqa: F821
    items: Mapped[list["DocumentItem"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A line item extracted from a document (e.g. one product on a receipt)."""

    __tablename__ = "document_items"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    unit_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    document: Mapped[Document] = relationship(back_populates="items")
