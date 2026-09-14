from __future__ import annotations

from pydantic import BaseModel

from app.schemas.user import UserRead


class AuthStatus(BaseModel):
    """GET /auth/status — always safe to call, never requires a session.
    Tells the frontend whether Google login is even available (PROMPT 3 §44/§52)."""

    auth_provider: str
    google_configured: bool
    authenticated: bool
    user: UserRead | None = None
