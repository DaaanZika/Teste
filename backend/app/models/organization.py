from __future__ import annotations

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import OrganizationStatus


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tenant (PROMPT 4). Owns one or more `Campaign`s — every campaign,
    and everything that hangs off a campaign_id (documents, expenses,
    revenues, compliance alerts), belongs to exactly one organization.

    `plan`/`storage_limit_bytes` exist so future real billing/limits have a
    column to read instead of being bolted on later — no billing logic
    runs against them yet (PROMPT 4 explicitly does not ask for real
    billing in this phase).
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        SAEnum(OrganizationStatus, native_enum=False, length=20),
        default=OrganizationStatus.ACTIVE,
        nullable=False,
    )
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    storage_limit_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
