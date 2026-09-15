from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Role, UserStatus


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An operator account.

    In V1 (auth_provider="local") a single row is auto-created and treated
    as ADMIN — see app.core.security. Once auth_provider="google", rows are
    created on first successful Google login (google_id populated) with the
    safest default role (VIEWER); an ADMIN promotes them via PATCH /users/{id}.

    PROMPT 4 (multi-tenant): `organization_id` is NULL only for SUPER_ADMIN
    (a platform-level account, not scoped to any single organization) —
    every other user belongs to exactly one organization, set at creation
    and never trusted from client input. `password_hash` is NULL for
    Google-only accounts; login accepts either Google OAuth or a password,
    whichever the account has configured.
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    role: Mapped[Role] = mapped_column(SAEnum(Role, native_enum=False, length=30), default=Role.VIEWER, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, native_enum=False, length=20), default=UserStatus.ACTIVE, nullable=False
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
