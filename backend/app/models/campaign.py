from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An electoral campaign. All financial records belong to one campaign,
    and one campaign belongs to exactly one `Organization` (PROMPT 4) — the
    tenant boundary. Every document/expense/revenue/compliance-alert is
    reachable only via its campaign's organization_id; nothing below this
    model carries its own organization_id column."""

    __tablename__ = "campaigns"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_document: Mapped[str | None] = mapped_column(String(20), nullable=True)
    campaign_cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    election_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    election_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    office: Mapped[str | None] = mapped_column(String(255), nullable=True)
    party: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="campaign")  # noqa: F821
    expenses: Mapped[list["Expense"]] = relationship(back_populates="campaign")  # noqa: F821
    revenues: Mapped[list["Revenue"]] = relationship(back_populates="campaign")  # noqa: F821
