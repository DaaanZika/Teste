from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class UserPermission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-user permission grant — only consulted for `Role.CUSTOM` (see
    app/core/rbac.py::user_has_permission). Every other role's capabilities
    come from the fixed ROLE_PERMISSIONS matrix, never from this table."""

    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "permission", name="uq_user_permissions_user_permission"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(50), nullable=False)
