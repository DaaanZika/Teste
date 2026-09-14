from __future__ import annotations

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Role


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An operator account.

    In V1 (auth_provider="local") a single row is auto-created and treated
    as ADMIN — see app.core.security. Once auth_provider="google", rows are
    created on first successful Google login (google_id populated) with the
    safest default role (VIEWER); an ADMIN promotes them via PATCH /users/{id}.
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    role: Mapped[Role] = mapped_column(SAEnum(Role, native_enum=False, length=30), default=Role.VIEWER, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
