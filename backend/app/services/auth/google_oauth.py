"""Real Google OAuth 2.0 / OIDC flow.

Uses Google's documented endpoints directly over HTTPS (httpx) — no SDK,
no mock, no simulated response. It is fully functional the moment
GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/GOOGLE_REDIRECT_URI are set; without
them every function here raises NotConfiguredError instead of pretending
to work (PROMPT 3 §45/§52: Google integrations are optional and the app
must never fake a result when they're off).

Three purposes share this module and the same registered redirect URI (one
Google Cloud Console entry, not three — see app/api/routes/auth.py and
app/api/routes/integrations.py for how the shared /auth/google/callback
tells them apart via which state cookie matched):

  - Login (PROMPT 3 §6): minimal scope, `access_type=online` — we mint our
    own session, we don't need a long-lived Google token for this.
  - Connecting Google Drive (PROMPT 3 §11): drive.file scope,
    `access_type=offline` + `prompt=consent` to guarantee a refresh_token,
    since the backend needs to call the Drive API later, unattended.
  - Connecting Gmail (PROMPT 3 §13): gmail.readonly scope, same
    `offline`/`consent` reasoning — detection only, never send/delete.
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

LOGIN_SCOPES = "openid email profile"
DRIVE_SCOPES = "openid email profile https://www.googleapis.com/auth/drive.file"
# Read-only: this integration only ever detects and suggests candidate
# attachments (PROMPT 3 §13) — it never sends, deletes, or modifies
# anything in the connected mailbox.
GMAIL_SCOPES = "openid email profile https://www.googleapis.com/auth/gmail.readonly"


@dataclass
class GoogleProfile:
    google_id: str
    email: str | None
    name: str | None
    avatar: str | None


@dataclass
class GoogleTokens:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str


def _require_configured() -> tuple[str, str, str]:
    settings = get_settings()
    if not (settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri):
        raise NotConfiguredError(
            "A integração com o Google não está configurada neste servidor. "
            "Defina GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REDIRECT_URI."
        )
    return settings.google_client_id, settings.google_client_secret, settings.google_redirect_uri


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_client_id and settings.google_client_secret and settings.google_redirect_uri)


def generate_state() -> str:
    return secrets.token_urlsafe(24)


def build_authorization_url(
    state: str, *, scope: str = LOGIN_SCOPES, access_type: str = "online", prompt: str = "select_account"
) -> str:
    client_id, _secret, redirect_uri = _require_configured()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,
        "access_type": access_type,
        "prompt": prompt,
    }
    return f"{AUTHORIZATION_ENDPOINT}?{httpx.QueryParams(params)}"


def _exchange_code(code: str) -> dict:
    client_id, client_secret, redirect_uri = _require_configured()
    response = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise UnauthorizedError("Não foi possível concluir o login com Google (código inválido ou expirado).")
    tokens = response.json()
    if not tokens.get("access_token"):
        raise UnauthorizedError("Resposta inválida do Google ao trocar o código de autorização.")
    return tokens


def exchange_code_for_profile(code: str) -> GoogleProfile:
    """Login purpose: exchanges the code, fetches the profile, and discards
    the token (we mint our own session — see app/services/auth/session_service.py)."""
    tokens = _exchange_code(code)
    response = httpx.get(
        USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {tokens['access_token']}"}, timeout=10
    )
    if response.status_code != 200:
        raise UnauthorizedError("Não foi possível obter o perfil do Google.")
    info = response.json()

    google_id = info.get("sub")
    if not google_id:
        raise UnauthorizedError("Perfil do Google sem identificador ('sub').")

    return GoogleProfile(google_id=google_id, email=info.get("email"), name=info.get("name"), avatar=info.get("picture"))


def exchange_code_for_tokens(code: str) -> GoogleTokens:
    """Connect-an-integration purpose (Drive, Gmail): keeps the tokens —
    the backend needs to call that API later, unattended."""
    tokens = _exchange_code(code)
    return GoogleTokens(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=int(tokens.get("expires_in", 3600)),
        scope=tokens.get("scope", ""),
    )
