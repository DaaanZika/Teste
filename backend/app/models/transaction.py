from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TransactionType


class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Central financial ledger row.

    Every expense/revenue that reaches `status=COMPLETE` (or otherwise
    carries a usable amount) is mirrored here so `finance_calculator` has
    one table to aggregate over instead of unioning expenses and revenues
    on every query. Backend-owned; the frontend never computes balances.
    """

    __tablename__ = "transactions"

    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, native_enum=False, length=10), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(
        String(255), nullable=True, doc="Supplier name for expenses, donor name for revenues."
    )

    expense_id: Mapped[str | None] = mapped_column(ForeignKey("expenses.id"), nullable=True)
    revenue_id: Mapped[str | None] = mapped_column(ForeignKey("revenues.id"), nullable=True)
