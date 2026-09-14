from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentLinkStatus, RevenueStatus


class Revenue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A campaign revenue (donation or other legally recognized source).

    `source_type` is a free-text field in V1: official categorization of
    revenue sources under TSE rules is not encoded here without a
    confirmed legal source (see app/rules/electoral). REVISÃO HUMANA.
    """

    __tablename__ = "revenues"

    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)

    date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    donor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    donor_document: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)

    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    document_status: Mapped[DocumentLinkStatus] = mapped_column(
        SAEnum(DocumentLinkStatus, native_enum=False, length=20),
        default=DocumentLinkStatus.PENDING,
        nullable=False,
    )

    status: Mapped[RevenueStatus] = mapped_column(
        SAEnum(RevenueStatus, native_enum=False, length=30),
        default=RevenueStatus.PENDING_INFORMATION,
        nullable=False,
    )
    missing_fields: Mapped[str | None] = mapped_column(String(500), nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="revenues")  # noqa: F821
    document: Mapped["Document | None"] = relationship()  # noqa: F821
