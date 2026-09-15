"""Password-based login (PROMPT 4) — a second way to reach the same session
mechanism Google OAuth already uses, exercised end-to-end against real
endpoints (never mocking password_service itself)."""
import uuid
from unittest.mock import patch

from app.core.config import Settings
from app.core.password import hash_password
from app.models.enums import Role
from app.models.organization import Organization
from app.models.user import User
from app.services.auth import password_service


def _password_auth_settings(**overrides) -> Settings:
    # AUTH_PROVIDER=local (the test default) never checks the session
    # cookie at all — password login only matters once it's something else.
    return Settings(auth_provider="google", frontend_url="http://localhost:5173", **overrides)


def _make_user(db_session, *, email, password, role=Role.VIEWER, active=True):
    org = Organization(name="Org Teste", slug=f"org-{uuid.uuid4().hex[:8]}")
    db_session.add(org)
    db_session.flush()
    user = User(
        name="Usuário Teste",
        email=email,
        role=role,
        active=active,
        organization_id=org.id,
        password_hash=hash_password(password),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_with_correct_password_succeeds_and_sets_session_cookie(client, db_session):
    _make_user(db_session, email="pass@example.com", password="Senha123!")
    with patch("app.api.routes.auth.get_settings", return_value=_password_auth_settings()):
        response = client.post("/auth/login", json={"email": "pass@example.com", "password": "Senha123!"})
    assert response.status_code == 200
    assert response.json()["email"] == "pass@example.com"
    assert "campanhas_session" in response.cookies


def test_login_with_wrong_password_returns_401(client, db_session):
    _make_user(db_session, email="pass2@example.com", password="Senha123!")
    response = client.post("/auth/login", json={"email": "pass2@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_login_with_nonexistent_email_returns_same_generic_401(client, db_session):
    """Never distinguishable from a wrong-password 401 — no email enumeration."""
    wrong_password = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever123"}
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["error"] == "UNAUTHORIZED"


def test_login_rejects_deactivated_user(client, db_session):
    _make_user(db_session, email="inactive@example.com", password="Senha123!", active=False)
    response = client.post("/auth/login", json={"email": "inactive@example.com", "password": "Senha123!"})
    assert response.status_code == 401


def test_account_locks_after_five_failed_attempts(client, db_session):
    _make_user(db_session, email="lockout@example.com", password="Senha123!")
    for _ in range(password_service.MAX_FAILED_ATTEMPTS):
        response = client.post("/auth/login", json={"email": "lockout@example.com", "password": "wrong"})
        assert response.status_code == 401

    # Even the correct password is now rejected — account is locked, not
    # just "still guessing wrong".
    response = client.post("/auth/login", json={"email": "lockout@example.com", "password": "Senha123!"})
    assert response.status_code == 401


def test_change_password_requires_correct_current_password(client, db_session):
    _make_user(db_session, email="change@example.com", password="Original123!")
    settings = _password_auth_settings()
    with (
        patch("app.api.routes.auth.get_settings", return_value=settings),
        patch("app.core.security.get_settings", return_value=settings),
    ):
        login_resp = client.post("/auth/login", json={"email": "change@example.com", "password": "Original123!"})
        assert login_resp.status_code == 200

        wrong_current = client.post(
            "/auth/change-password",
            json={"current_password": "not-the-real-one", "new_password": "NovaSenha456!"},
        )
        assert wrong_current.status_code == 401

        ok = client.post(
            "/auth/change-password",
            json={"current_password": "Original123!", "new_password": "NovaSenha456!"},
        )
        assert ok.status_code == 200

    # The old session/cookie stays valid (change-password doesn't revoke
    # sessions), but a fresh login must now use the new password.
    with patch("app.api.routes.auth.get_settings", return_value=settings):
        old_password_login = client.post(
            "/auth/login", json={"email": "change@example.com", "password": "Original123!"}
        )
        assert old_password_login.status_code == 401
        new_password_login = client.post(
            "/auth/login", json={"email": "change@example.com", "password": "NovaSenha456!"}
        )
        assert new_password_login.status_code == 200


def test_forgot_password_returns_identical_generic_response_regardless_of_email(client, db_session):
    _make_user(db_session, email="forgot@example.com", password="Original123!")
    existing = client.post("/auth/forgot-password", json={"email": "forgot@example.com"})
    nonexistent = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert existing.status_code == 200
    assert nonexistent.status_code == 200
    assert existing.json() == nonexistent.json()


def test_reset_password_with_valid_token_lets_new_password_login(client, db_session):
    user = _make_user(db_session, email="reset@example.com", password="Original123!")
    raw_token = password_service.create_reset_token(db_session, user)

    reset_resp = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "NovaSenha789!"})
    assert reset_resp.status_code == 200

    with patch("app.api.routes.auth.get_settings", return_value=_password_auth_settings()):
        login = client.post("/auth/login", json={"email": "reset@example.com", "password": "NovaSenha789!"})
    assert login.status_code == 200


def test_reset_password_token_is_single_use(client, db_session):
    user = _make_user(db_session, email="reset2@example.com", password="Original123!")
    raw_token = password_service.create_reset_token(db_session, user)

    first = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "AAAAbbbb111"})
    assert first.status_code == 200

    second = client.post("/auth/reset-password", json={"token": raw_token, "new_password": "CCCCdddd222"})
    assert second.status_code == 401


def test_reset_password_rejects_unknown_token(client, db_session):
    response = client.post("/auth/reset-password", json={"token": "not-a-real-token", "new_password": "AAAAbbbb111"})
    assert response.status_code == 401
