from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Role, UserStatus


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str | None
    google_id: str | None
    avatar: str | None
    role: Role
    active: bool
    created_at: datetime
    updated_at: datetime
    organization_id: str | None = None
    status: UserStatus = UserStatus.ACTIVE
    last_login_at: datetime | None = None


class UserUpdate(BaseModel):
    """Admin-only: change a user's role or activate/deactivate them.
    Never accepts an email/google_id/password override — identity comes
    only from Google, and a password is only ever changed through the
    dedicated /auth/change-password or admin reset-password flow."""

    role: Role | None = None
    active: bool | None = None
    status: UserStatus | None = None


class UserCreate(BaseModel):
    """POST /users (PROMPT 4): an org OWNER/ADMIN creating a teammate, or
    SUPER_ADMIN creating a user directly in a given organization. The
    caller's own organization_id is always used unless the caller is
    SUPER_ADMIN and supplies one explicitly — never trusted from a
    non-SUPER_ADMIN's request body (see app/api/routes/users.py)."""

    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)
    role: Role = Role.VISUALIZADOR
    active: bool = True
    organization_id: str | None = None
