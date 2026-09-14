"""Server-side session management (PROMPT 3 §7).

A session's raw token is set as an httponly cookie and returned to the
browser exactly once, at login. The database only ever stores its SHA-256
hash — the same reasoning as a password hash: a database leak alone can't
be replayed as a valid session.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.config import get_settings
from app.models.session import Session
from app.models.user import User


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite has no real timezone-aware storage: a `DateTime(timezone=True)`
    column round-trips as a naive datetime even though it was written with
    `datetime.now(timezone.utc)`. Treat a naive value as UTC (it always is,
    here) instead of crashing when compared against an aware "now" —
    PostgreSQL doesn't need this (it preserves tzinfo), but must not break
    from it either."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def create_session(db: DBSession, user: User, *, request: Request | None = None) -> str:
    """Creates a session row and returns the RAW token (only time it's ever available)."""
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    session = Session(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours),
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=request.client.host if request and request.client else None,
    )
    db.add(session)
    db.commit()
    return raw_token


def get_user_from_token(db: DBSession, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    token_hash = _hash_token(raw_token)
    stmt = select(Session).where(Session.token_hash == token_hash)
    session = db.execute(stmt).scalar_one_or_none()
    if session is None:
        return None
    if session.revoked_at is not None:
        return None
    if _as_aware_utc(session.expires_at) < datetime.now(timezone.utc):
        return None
    return db.get(User, session.user_id)


def get_user_from_cookie(db: DBSession, request: Request) -> User | None:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    return get_user_from_token(db, raw_token)


def revoke_token(db: DBSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    token_hash = _hash_token(raw_token)
    stmt = select(Session).where(Session.token_hash == token_hash)
    session = db.execute(stmt).scalar_one_or_none()
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
