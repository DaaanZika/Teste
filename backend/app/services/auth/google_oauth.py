"""Real Google OAuth 2.0 / OIDC login flow.

Uses Google's documented endpoints directly over HTTPS (httpx) — no SDK,
no mock, no simulated response. It is fully functional the moment
GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/GOOGLE_REDIRECT_URI are set; without
them every function here raises NotConfiguredError instead of pretending
to work (PROMPT 3 §45/§52: Google integrations are optional and the app
must never fake a result when they're off).

Flow (PROMPT 3 §6):
    user -> GET /auth/google/login (redirect to Google, with `state`)
    user authorizes on Google's own page
    Google -> GET /auth/google/callback?code=...&state=...
    backend exchanges `code` for tokens, verifies `state`, fetches the
    user's Google profile, upserts a local User row (never stores a
    Google password — OAuth never sees one), creates a session.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.exceptions import NotConfiguredError, UnauthorizedError

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = "openid email profile"


@dataclass
class GoogleProfile:
    google_id: str
    email: str | None
    name: str | None
    avatar: str | None


def _require_configured() -> tuple[str, str, str]:
    settings = get_settings()
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        raise NotConfiguredError(
            "Login com Google não está configurado neste servidor. "
            "Defina GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REDIRECT_URI."
        )
    return settings.google_client_id, settings.google_client_secret, settings.google_redirect_uri


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri)


def generate_state() -> str:
    return secrets.token_urlsafe(24)


def build_authorization_url(state: str) -> str:
    client_id, _secret, redirect_uri = _require_configured()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZATION_ENDPOINT}?{httpx.QueryParams(params)}"


def exchange_code_for_profile(code: str) -> GoogleProfile:
    """Exchanges an authorization code for tokens, then fetches the profile.
    Raises UnauthorizedError on any failure — never returns a partial/guessed profile."""
    client_id, client_secret, redirect_uri = _require_configured()

    with httpx.Client(timeout=10) as client:
        token_response = client.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code != 200:
            raise UnauthorizedError("Não foi possível concluir o login com Google (código inválido ou expirado).")
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise UnauthorizedError("Resposta inválida do Google ao trocar o código de autorização.")

        userinfo_response = client.get(
            USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_response.status_code != 200:
            raise UnauthorizedError("Não foi possível obter o perfil do Google.")
        info = userinfo_response.json()

    google_id = info.get("sub")
    if not google_id:
        raise UnauthorizedError("Perfil do Google sem identificador ('sub').")

    return GoogleProfile(
        google_id=google_id,
        email=info.get("email"),
        name=info.get("name"),
        avatar=info.get("picture"),
    )
