from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Supplier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deduplicated supplier/vendor directory, used for reporting and quick-entry matching."""

    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    document: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
