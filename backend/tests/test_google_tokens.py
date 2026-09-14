"""app/services/integrations/google_tokens.py — connection storage and
token refresh. Real DB rows, mocked HTTP (the only thing that talks to
Google is a single httpx.post call to the token endpoint)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.services.integrations import google_tokens


@pytest.fixture(autouse=True)
def _cleanup_google_drive_connection(db_session):
    """The DB in this test suite isn't reset between tests (see
    conftest.py) — an active connection left by one test would leak into
    other test modules that assume "no active google_drive connection" as
    their starting state."""
    yield
    google_tokens.revoke_connection(db_session, "google_drive")


@pytest.fixture()
def user(db_session):
    from app.models.enums import Role
    from app.models.user import User

    unique = uuid.uuid4().hex[:8]
    u = User(name="Admin", email=f"admin-tokens-{unique}@example.com", role=Role.ADMIN, active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def test_no_connection_returns_none(db_session):
    assert google_tokens.get_active_connection(db_session, "google_drive") is None
    assert google_tokens.get_valid_access_token(db_session, "google_drive") is None


def test_save_connection_then_get_active(db_session, user):
    conn = google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-1",
        refresh_token="refresh-1",
        expires_in_seconds=3600,
    )
    assert conn.revoked_at is None
    active = google_tokens.get_active_connection(db_session, "google_drive")
    assert active is not None
    assert active.id == conn.id
    assert active.access_token == "tok-1"


def test_new_connection_revokes_previous(db_session, user):
    first = google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-1",
        refresh_token="refresh-1",
        expires_in_seconds=3600,
    )
    google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-2",
        refresh_token="refresh-2",
        expires_in_seconds=3600,
    )
    db_session.refresh(first)
    assert first.revoked_at is not None

    active = google_tokens.get_active_connection(db_session, "google_drive")
    assert active.access_token == "tok-2"


def test_new_connection_without_refresh_token_keeps_previous(db_session, user):
    """A re-consent that Google doesn't hand a fresh refresh_token for
    (it only issues one on first consent) must not lose the ability to
    refresh later."""
    google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-1",
        refresh_token="refresh-1",
        expires_in_seconds=3600,
    )
    second = google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-2",
        refresh_token=None,
        expires_in_seconds=3600,
    )
    assert second.refresh_token == "refresh-1"


def test_revoke_connection(db_session, user):
    google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-1",
        refresh_token="refresh-1",
        expires_in_seconds=3600,
    )
    google_tokens.revoke_connection(db_session, "google_drive")
    assert google_tokens.get_active_connection(db_session, "google_drive") is None


def test_revoke_connection_when_none_active_is_a_noop(db_session):
    google_tokens.revoke_connection(db_session, "google_drive")  # must not raise


def test_get_valid_access_token_returns_stored_token_when_not_near_expiry(db_session, user):
    google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-1",
        refresh_token="refresh-1",
        expires_in_seconds=3600,
    )
    token = google_tokens.get_valid_access_token(db_session, "google_drive")
    assert token == "tok-1"


def test_get_valid_access_token_refreshes_when_near_expiry(db_session, user, monkeypatch):
    conn = google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-old",
        refresh_token="refresh-1",
        expires_in_seconds=60,  # within the 2-minute safety margin
    )

    calls = []

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"access_token": "tok-refreshed", "expires_in": 3600}

    def fake_post(url, data=None, timeout=None):
        calls.append((url, data))
        return _FakeResponse()

    monkeypatch.setattr(google_tokens.httpx, "post", fake_post)

    token = google_tokens.get_valid_access_token(db_session, "google_drive")
    assert token == "tok-refreshed"
    assert len(calls) == 1
    assert calls[0][1]["refresh_token"] == "refresh-1"
    assert calls[0][1]["grant_type"] == "refresh_token"

    db_session.refresh(conn)
    assert conn.access_token == "tok-refreshed"


def test_refresh_without_refresh_token_raises(db_session, user):
    conn = google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-old",
        refresh_token=None,
        expires_in_seconds=60,
    )
    conn.refresh_token = None
    db_session.commit()

    with pytest.raises(RuntimeError):
        google_tokens.get_valid_access_token(db_session, "google_drive")


def test_refresh_failure_raises_runtime_error(db_session, user, monkeypatch):
    google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-old",
        refresh_token="refresh-1",
        expires_in_seconds=60,
    )

    class _FakeResponse:
        status_code = 400
        text = "invalid_grant"

    monkeypatch.setattr(google_tokens.httpx, "post", lambda *a, **k: _FakeResponse())

    with pytest.raises(RuntimeError, match="Failed to refresh"):
        google_tokens.get_valid_access_token(db_session, "google_drive")


def test_as_aware_utc_treats_naive_as_utc():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aware = google_tokens._as_aware_utc(naive)
    assert aware.tzinfo is timezone.utc

    already_aware = datetime.now(timezone.utc)
    assert google_tokens._as_aware_utc(already_aware) is already_aware
