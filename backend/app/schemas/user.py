from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Role


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


class UserUpdate(BaseModel):
    """Admin-only: change a user's role or activate/deactivate them.
    Never accepts an email/google_id override — identity comes only from Google."""

    role: Role | None = None
    active: bool | None = None
