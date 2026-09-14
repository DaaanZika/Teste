from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import get_current_user as resolve_current_user
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.auth import AuthStatus
from app.schemas.user import UserRead
from app.services.audit.audit_service import record as record_audit
from app.services.auth import google_oauth, session_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE_NAME = "campanhas_oauth_state"


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


@router.get("/google/login")
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


@router.get("/google/callback")
def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)) -> RedirectResponse:
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
