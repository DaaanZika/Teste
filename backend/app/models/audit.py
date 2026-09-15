from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin
from app.models.enums import AuditAction


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Append-only record of every relevant change. Never deleted or edited."""

    __tablename__ = "audit_logs"

    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction, native_enum=False, length=30), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # PROMPT 4 — all nullable/additive: every pre-existing row (and every
    # call site that doesn't pass them) keeps working unchanged.
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
