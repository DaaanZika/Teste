"""Stores and refreshes OAuth tokens for optional Google integrations
(Drive, Gmail). One row per provider is kept "active" (not revoked); a new
connection supersedes (revokes) the previous one instead of accumulating
duplicates.

Tokens are never included in any Pydantic response schema and never
logged — every call site here works with `IntegrationConnection` ORM rows
directly, not through the API layer.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.integration_connection import IntegrationConnection

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Refresh a bit before actual expiry to avoid a request failing mid-flight.
_EXPIRY_SAFETY_MARGIN = timedelta(minutes=2)


def _as_aware_utc(value: datetime) -> datetime:
    """Same reasoning as app/services/auth/session_service.py: SQLite drops
    tzinfo from DateTime(timezone=True) columns on read."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def get_active_connection(db: Session, provider: str) -> IntegrationConnection | None:
    stmt = (
        select(IntegrationConnection)
        .where(IntegrationConnection.provider == provider, IntegrationConnection.revoked_at.is_(None))
        .order_by(IntegrationConnection.created_at.desc())
    )
    return db.execute(stmt).scalars().first()


def save_connection(
    db: Session,
    *,
    user_id: str,
    provider: str,
    scope: str,
    access_token: str,
    refresh_token: str | None,
    expires_in_seconds: int,
) -> IntegrationConnection:
    existing = get_active_connection(db, provider)
    if existing is not None:
        existing.revoked_at = datetime.now(timezone.utc)

    connection = IntegrationConnection(
        provider=provider,
        connected_by_user_id=user_id,
        scope=scope,
        access_token=access_token,
        refresh_token=refresh_token or (existing.refresh_token if existing else None),
        token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def revoke_connection(db: Session, provider: str) -> None:
    connection = get_active_connection(db, provider)
    if connection is not None:
        connection.revoked_at = datetime.now(timezone.utc)
        db.commit()


def _refresh_access_token(connection: IntegrationConnection) -> tuple[str, int]:
    settings = get_settings()
    if not connection.refresh_token:
        raise RuntimeError(f"No refresh_token stored for {connection.provider}; reconnection required.")

    response = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": connection.refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to refresh Google token for {connection.provider}: {response.text}")
    body = response.json()
    return body["access_token"], int(body.get("expires_in", 3600))


def get_valid_access_token(db: Session, provider: str) -> str | None:
    """Returns a usable access token, refreshing it first if it's near
    expiry. Returns None (never raises) when there is no active connection
    at all — callers treat that as "integration not connected"."""
    connection = get_active_connection(db, provider)
    if connection is None:
        return None

    expires_at = _as_aware_utc(connection.token_expires_at)
    if expires_at - _EXPIRY_SAFETY_MARGIN > datetime.now(timezone.utc):
        return connection.access_token

    access_token, expires_in = _refresh_access_token(connection)
    connection.access_token = access_token
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    db.commit()
    return access_token
