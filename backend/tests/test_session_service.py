import uuid
from datetime import datetime, timedelta, timezone

from app.models.enums import Role
from app.models.session import Session
from app.models.user import User
from app.services.auth import session_service


def _make_user(db_session, **overrides) -> User:
    # Unique email per call: tests share one session-wide database, and
    # `users.email` is unique.
    default_email = f"teste-{uuid.uuid4().hex[:8]}@example.com"
    user = User(name="Teste", email=overrides.pop("email", default_email), role=Role.VIEWER, active=True, **overrides)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_session_returns_raw_token_and_stores_only_its_hash(db_session):
    user = _make_user(db_session)
    raw_token = session_service.create_session(db_session, user)

    assert raw_token
    stored = db_session.query(Session).filter(Session.user_id == user.id).one()
    assert stored.token_hash != raw_token
    assert len(stored.token_hash) == 64  # sha256 hex digest


def test_get_user_from_token_resolves_a_valid_session(db_session):
    user = _make_user(db_session)
    raw_token = session_service.create_session(db_session, user)

    resolved = session_service.get_user_from_token(db_session, raw_token)
    assert resolved is not None
    assert resolved.id == user.id


def test_get_user_from_token_rejects_unknown_token(db_session):
    assert session_service.get_user_from_token(db_session, "not-a-real-token") is None


def test_get_user_from_token_rejects_expired_session(db_session):
    user = _make_user(db_session)
    raw_token = session_service.create_session(db_session, user)
    stored = db_session.query(Session).filter(Session.user_id == user.id).one()
    stored.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    assert session_service.get_user_from_token(db_session, raw_token) is None


def test_revoke_token_invalidates_the_session_immediately(db_session):
    user = _make_user(db_session)
    raw_token = session_service.create_session(db_session, user)
    assert session_service.get_user_from_token(db_session, raw_token) is not None

    session_service.revoke_token(db_session, raw_token)

    assert session_service.get_user_from_token(db_session, raw_token) is None
