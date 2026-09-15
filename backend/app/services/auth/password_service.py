"""Password-based login (PROMPT 4) — a second way to reach the exact same
session mechanism Google OAuth already uses (app.services.auth.session_service),
never a parallel auth system. A session created here and one created by
Google login are indistinguishable to the rest of the app.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.password import hash_password, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
RESET_TOKEN_TTL_MINUTES = 30


def _as_aware_utc(value: datetime) -> datetime:
    """See session_service._as_aware_utc — SQLite round-trips a naive
    datetime even for a timezone(True) column; treat it as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_locked(user: User) -> bool:
    if user.locked_until is None:
        return False
    return _as_aware_utc(user.locked_until) > datetime.now(timezone.utc)


def authenticate(db: DBSession, *, email: str, password: str) -> User | None:
    """Returns the User on success. On failure, records the attempt against
    the matching account (if any) and returns None — the caller never
    learns whether the email existed, the account was locked, or the
    password was wrong; every case is the same generic error to the client."""
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or user.password_hash is None:
        return None
    if is_locked(user):
        return None
    if not user.active:
        return None
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        db.commit()
        return None

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def set_password(db: DBSession, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()


def create_reset_token(db: DBSession, user: User) -> str:
    """Returns the RAW token (only time it's ever available — only the hash
    is persisted, same principle as a session token)."""
    raw_token = secrets.token_urlsafe(32)
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    )
    db.add(token)
    db.commit()
    return raw_token


def consume_reset_token(db: DBSession, raw_token: str) -> User | None:
    """Returns the associated User and marks the token used, or None if the
    token is invalid/expired/already used. Single-use: calling this twice
    with the same token only ever succeeds once."""
    token_hash = _hash_token(raw_token)
    token = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalar_one_or_none()
    if token is None:
        return None
    if token.used_at is not None:
        return None
    if _as_aware_utc(token.expires_at) < datetime.now(timezone.utc):
        return None

    token.used_at = datetime.now(timezone.utc)
    db.commit()
    return db.get(User, token.user_id)
