from unittest.mock import patch

from app.core.config import Settings
from app.services.auth.google_oauth import GoogleProfile


def _configured_settings(**overrides) -> Settings:
    return Settings(
        google_client_id="test-client-id",
        google_client_secret="test-secret",
        google_redirect_uri="http://localhost:8000/auth/google/callback",
        frontend_url="http://localhost:5173",
        **overrides,
    )


def test_auth_status_in_local_mode_is_always_authenticated_as_admin(client):
    response = client.get("/auth/status")
    assert response.status_code == 200
    body = response.json()
    assert body["auth_provider"] == "local"
    assert body["google_configured"] is False
    assert body["authenticated"] is True
    assert body["user"]["role"] == "ADMIN"


def test_google_login_returns_503_when_not_configured(client):
    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "NOT_CONFIGURED"


def test_google_login_redirects_to_google_when_configured(client):
    with patch("app.services.auth.google_oauth.get_settings", return_value=_configured_settings()):
        response = client.get("/auth/google/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=test-client-id" in response.headers["location"]
    assert "campanhas_oauth_state" in response.cookies


def test_google_callback_rejects_mismatched_state(client):
    response = client.get(
        "/auth/google/callback",
        params={"code": "irrelevant", "state": "does-not-match-cookie"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_google_callback_creates_user_and_session_on_success(client):
    configured = _configured_settings()

    with patch("app.services.auth.google_oauth.get_settings", return_value=configured):
        login_response = client.get("/auth/google/login", follow_redirects=False)
    state = login_response.cookies["campanhas_oauth_state"]

    fake_profile = GoogleProfile(google_id="g-123", email="new@example.com", name="Nova Pessoa", avatar=None)
    with (
        patch("app.api.routes.auth.google_oauth.exchange_code_for_profile", return_value=fake_profile),
        patch("app.api.routes.auth.get_settings", return_value=configured),
    ):
        callback_response = client.get(
            "/auth/google/callback",
            params={"code": "valid-code", "state": state},
            follow_redirects=False,
        )

    assert callback_response.status_code == 302
    assert callback_response.headers["location"] == "http://localhost:5173"
    assert "campanhas_session" in callback_response.cookies
