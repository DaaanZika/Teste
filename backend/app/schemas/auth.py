from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class AuthStatus(BaseModel):
    """GET /auth/status — always safe to call, never requires a session.
    Tells the frontend whether Google login is even available (PROMPT 3 §44/§52)."""

    auth_provider: str
    google_configured: bool
    authenticated: bool
    user: UserRead | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=255)
