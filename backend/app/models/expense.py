from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentLinkStatus, ExpenseStatus


class Expense(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A campaign expense.

    A record may be created with incomplete information (see
    `services.finance.quick_expense_parser`) and/or before its supporting
    document exists. `status` tracks data completeness and
    `document_status` tracks whether a document is attached, independently.
    """

    __tablename__ = "expenses"

    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)

    date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_document: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)

    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    document_status: Mapped[DocumentLinkStatus] = mapped_column(
        SAEnum(DocumentLinkStatus, native_enum=False, length=20),
        default=DocumentLinkStatus.PENDING,
        nullable=False,
    )

    status: Mapped[ExpenseStatus] = mapped_column(
        SAEnum(ExpenseStatus, native_enum=False, length=30),
        default=ExpenseStatus.PENDING_INFORMATION,
        nullable=False,
    )
    missing_fields: Mapped[str | None] = mapped_column(
        String(500), nullable=True, doc="Comma-separated list of fields still missing."
    )

    source_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Original free text used to create this expense via /expenses/quick."
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="expenses")  # noqa: F821
    document: Mapped["Document | None"] = relationship()  # noqa: F821
