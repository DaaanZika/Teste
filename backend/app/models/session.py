from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Session(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A server-side login session (PROMPT 3 §7).

    The raw session token is set as an httponly cookie and never stored —
    only its SHA-256 hash lives here (same principle as a password hash),
    so a database leak alone can't be used to impersonate a session.
    `revoked_at` lets logout (and a future "sign out everywhere") take
    effect immediately without waiting for expiry.
    """

    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
