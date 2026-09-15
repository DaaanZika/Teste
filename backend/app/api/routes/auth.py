from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError, ValidationFailedError
from app.core.password import verify_password
from app.core.rate_limit import rate_limit
from app.core.rbac import Permission, role_has_permission
from app.core.security import get_current_user as resolve_current_user
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import (
    AuthStatus,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserRead
from app.services.audit.audit_service import record as record_audit
from app.services.auth import google_oauth, password_service, session_service, user_service
from app.services.integrations import google_tokens
from app.services.notifications import email_service

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE_NAME = "campanhas_oauth_state"
DRIVE_STATE_COOKIE_NAME = "campanhas_oauth_state_drive"
GMAIL_STATE_COOKIE_NAME = "campanhas_oauth_state_gmail"

# Reachable without a session — a flood here wastes this server's time AND
# Google's token endpoint (the callback path) — so both are rate limited
# per client IP (docs/audit/FASE-D-gaps.md "Sem rate limiting no login").
_login_rate_limit = Depends(rate_limit("auth_login", max_attempts=10, window_seconds=60))
_callback_rate_limit = Depends(rate_limit("auth_callback", max_attempts=20, window_seconds=60))
_password_login_rate_limit = Depends(rate_limit("auth_password_login", max_attempts=10, window_seconds=60))
_forgot_password_rate_limit = Depends(rate_limit("auth_forgot_password", max_attempts=5, window_seconds=60))


@router.get("/status", response_model=AuthStatus)
def auth_status(request: Request, db: Session = Depends(get_db)) -> AuthStatus:
    """Never requires a session — the frontend calls this before knowing
    whether the user is logged in at all (PROMPT 3 §44)."""
    settings = get_settings()
    try:
        user = resolve_current_user(request, db)
    except UnauthorizedError:
        user = None

    return AuthStatus(
        auth_provider=settings.auth_provider,
        google_configured=google_oauth.is_configured(),
        authenticated=user is not None,
        user=UserRead.model_validate(user) if user else None,
    )


@router.get("/google/login", dependencies=[_login_rate_limit])
def google_login() -> RedirectResponse:
    state = google_oauth.generate_state()
    authorization_url = google_oauth.build_authorization_url(state)
    response = RedirectResponse(authorization_url, status_code=302)
    settings = get_settings()
    response.set_cookie(
        STATE_COOKIE_NAME,
        state,
        max_age=600,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
    )
    return response


@router.get("/google/callback", dependencies=[_callback_rate_limit])
def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """One registered Google redirect URI serves three purposes, told apart
    by which state cookie matches (see app/services/auth/google_oauth.py):
    a login (STATE_COOKIE_NAME), connecting Google Drive
    (DRIVE_STATE_COOKIE_NAME, started from /integrations/google-drive/connect),
    or connecting Gmail (GMAIL_STATE_COOKIE_NAME, started from
    /integrations/gmail/connect)."""
    if request.cookies.get(DRIVE_STATE_COOKIE_NAME) == state:
        return _handle_integration_connect_callback(
            request, code, db, provider="google_drive", state_cookie_name=DRIVE_STATE_COOKIE_NAME
        )
    if request.cookies.get(GMAIL_STATE_COOKIE_NAME) == state:
        return _handle_integration_connect_callback(
            request, code, db, provider="gmail", state_cookie_name=GMAIL_STATE_COOKIE_NAME
        )
    return _handle_login_callback(request, code, state, db)


def _handle_login_callback(request: Request, code: str, state: str, db: Session) -> RedirectResponse:
    settings = get_settings()
    expected_state = request.cookies.get(STATE_COOKIE_NAME)
    if not expected_state or expected_state != state:
        raise UnauthorizedError("Estado OAuth inválido ou expirado. Tente fazer login novamente.")

    profile = google_oauth.exchange_code_for_profile(code)
    user = user_service.get_or_create_user_from_google(db, profile)

    if not user.active:
        raise UnauthorizedError("Esta conta foi desativada por um administrador.")

    raw_token = session_service.create_session(db, user, request=request)
    record_audit(db, entity="user", entity_id=user.id, action=AuditAction.LOGIN, user_id=user.id)
    db.commit()

    response = RedirectResponse(settings.frontend_url, status_code=302)
    response.delete_cookie(STATE_COOKIE_NAME)
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
    )
    return response


def _handle_integration_connect_callback(
    request: Request, code: str, db: Session, *, provider: str, state_cookie_name: str
) -> RedirectResponse:
    settings = get_settings()
    # Connecting an integration requires an already-authenticated ADMIN —
    # enforced when /integrations/{provider}/connect was first requested,
    # and re-checked here since this callback is reachable directly.
    user = resolve_current_user(request, db)
    if not role_has_permission(user.role, Permission.MANAGE_INTEGRATIONS):
        raise UnauthorizedError(f"Apenas administradores podem conectar {provider}.")

    tokens = google_oauth.exchange_code_for_tokens(code)
    google_tokens.save_connection(
        db,
        user_id=user.id,
        provider=provider,
        scope=tokens.scope,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in_seconds=tokens.expires_in,
    )
    record_audit(db, entity="integration", entity_id=provider, action=AuditAction.CREATE, user_id=user.id)
    db.commit()

    response = RedirectResponse(f"{settings.frontend_url}/configuracoes", status_code=302)
    response.delete_cookie(state_cookie_name)
    return response


@router.post("/login", response_model=UserRead, dependencies=[_password_login_rate_limit])
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> UserRead:
    """Password-based login — a second way to reach the exact same session
    mechanism Google OAuth already uses (session_service.create_session),
    never a parallel auth system. Only meaningful once AUTH_PROVIDER is not
    "local" (that mode's single auto-created operator never checks the
    session cookie at all — see app.core.security.get_current_user)."""
    user = password_service.authenticate(db, email=payload.email, password=payload.password)
    if user is None:
        record_audit(db, entity="user", entity_id=payload.email, action=AuditAction.USER_LOGIN_FAILED)
        db.commit()
        raise UnauthorizedError("E-mail ou senha inválidos.")

    settings = get_settings()
    raw_token = session_service.create_session(db, user, request=request)
    record_audit(
        db,
        entity="user",
        entity_id=user.id,
        action=AuditAction.USER_LOGIN,
        user_id=user.id,
        organization_id=user.organization_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()

    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
    )
    return UserRead.model_validate(user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    # An account with no password yet (created by an admin, or Google-only)
    # sets its first password without proving a current one; any account
    # that already has one must prove it.
    if user.password_hash is not None and not verify_password(payload.current_password, user.password_hash):
        raise UnauthorizedError("Senha atual incorreta.")
    if payload.new_password == payload.current_password:
        raise ValidationFailedError("A nova senha deve ser diferente da atual.")

    password_service.set_password(db, user, payload.new_password)
    record_audit(
        db,
        entity="user",
        entity_id=user.id,
        action=AuditAction.PASSWORD_CHANGED,
        user_id=user.id,
        organization_id=user.organization_id,
    )
    db.commit()
    return {"success": True, "data": {"status": "password_changed"}}


@router.post("/forgot-password", dependencies=[_forgot_password_rate_limit])
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Always returns the same generic response whether or not the e-mail
    matches an account — never lets an attacker use this endpoint to
    enumerate registered e-mails."""
    settings = get_settings()
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is not None and user.active:
        raw_token = password_service.create_reset_token(db, user)
        record_audit(
            db,
            entity="user",
            entity_id=user.id,
            action=AuditAction.PASSWORD_RESET_REQUESTED,
            user_id=user.id,
            organization_id=user.organization_id,
        )
        db.commit()
        reset_link = f"{settings.frontend_url}/redefinir-senha?token={raw_token}"
        email_service.send_email(
            to=user.email,
            subject="Redefinição de senha — Campanhas",
            body=(
                f"Foi solicitada uma redefinição de senha para esta conta.\n\n"
                f"Se foi você, use o link abaixo (válido por {password_service.RESET_TOKEN_TTL_MINUTES} minutos):\n"
                f"{reset_link}\n\n"
                f"Se não foi você, ignore este e-mail — nada foi alterado."
            ),
        )

    return {
        "success": True,
        "data": {
            "status": "if_account_exists_email_sent",
            "message": "Se este e-mail estiver cadastrado, um link de redefinição foi enviado.",
        },
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    user = password_service.consume_reset_token(db, payload.token)
    if user is None:
        raise UnauthorizedError("Token de redefinição inválido, expirado ou já utilizado.")

    password_service.set_password(db, user, payload.new_password)
    record_audit(
        db,
        entity="user",
        entity_id=user.id,
        action=AuditAction.PASSWORD_RESET,
        user_id=user.id,
        organization_id=user.organization_id,
    )
    db.commit()
    return {"success": True, "data": {"status": "password_reset"}}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    session_service.revoke_token(db, raw_token)
    response.delete_cookie(settings.session_cookie_name)
    return {"success": True, "data": {"status": "logged_out"}}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)
