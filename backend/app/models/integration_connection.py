from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A stored OAuth grant for an optional external integration (Google
    Drive, Gmail, ...). Generic across providers so FASE F (Gmail) reuses
    this table instead of inventing a second one.

    Tokens are never returned by any API response schema and never logged
    (see app/services/integrations/google_tokens.py) — this is the one
    place they're persisted, and only here.
    """

    __tablename__ = "integration_connections"

    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "google_drive", "gmail"
    connected_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(500), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
