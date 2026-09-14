from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An electoral campaign. All financial records belong to one campaign."""

    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    election_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    office: Mapped[str | None] = mapped_column(String(255), nullable=True)
    party: Mapped[str | None] = mapped_column(String(100), nullable=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="campaign")  # noqa: F821
    expenses: Mapped[list["Expense"]] = relationship(back_populates="campaign")  # noqa: F821
    revenues: Mapped[list["Revenue"]] = relationship(back_populates="campaign")  # noqa: F821
