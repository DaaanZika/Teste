from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.config import get_settings
from app.core.health import check_database
from app.core.rbac import Permission
from app.models.user import User
from app.schemas.integrations import IntegrationStatus, IntegrationsStatusResponse
from app.services.auth import google_oauth
from app.services.integrations import google_tokens
from app.services.ocr.engine import is_tesseract_available

router = APIRouter(prefix="/integrations", tags=["integrations"])

DRIVE_STATE_COOKIE_NAME = "campanhas_oauth_state_drive"


@router.get(
    "/status",
    response_model=IntegrationsStatusResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_REPORTS))],
)
def integrations_status(db: Session = Depends(get_db)) -> IntegrationsStatusResponse:
    settings = get_settings()

    drive_connection = google_tokens.get_active_connection(db, "google_drive")
    gmail_connection = google_tokens.get_active_connection(db, "gmail")
    db_check = check_database(db)
    ocr_available = is_tesseract_available()

    return IntegrationsStatusResponse(
        google_oauth=IntegrationStatus(name="Google", connected=google_oauth.is_configured()),
        google_drive=IntegrationStatus(
            name="Google Drive",
            connected=drive_connection is not None,
            detail=None if drive_connection else "Não conectado",
        ),
        gmail=IntegrationStatus(
            name="Gmail",
            connected=gmail_connection is not None,
            detail="Não implementado nesta fase" if gmail_connection is None else None,
        ),
        backup=IntegrationStatus(
            name="Backup",
            connected=bool(settings.backup_storage_provider),
            detail=None if settings.backup_storage_provider else "Nenhum provedor de backup configurado",
        ),
        database=IntegrationStatus(name="Banco de dados", connected=db_check.healthy, detail=db_check.detail),
        ocr=IntegrationStatus(
            name="OCR (Tesseract)",
            connected=ocr_available,
            detail=None if ocr_available else "Executável tesseract não encontrado",
        ),
    )


@router.get("/google-drive/connect")
def connect_google_drive(user: User = Depends(require_permission(Permission.MANAGE_INTEGRATIONS))) -> RedirectResponse:
    """ADMIN only: starts the incremental-consent flow for Drive access
    (separate from login — see app/services/auth/google_oauth.py)."""
    state = google_oauth.generate_state()
    authorization_url = google_oauth.build_authorization_url(
        state, scope=google_oauth.DRIVE_SCOPES, access_type="offline", prompt="consent"
    )
    settings = get_settings()
    redirect = RedirectResponse(authorization_url, status_code=302)
    redirect.set_cookie(
        DRIVE_STATE_COOKIE_NAME, state, max_age=600, httponly=True, secure=not settings.debug, samesite="lax"
    )
    return redirect


@router.post(
    "/google-drive/disconnect", dependencies=[Depends(require_permission(Permission.MANAGE_INTEGRATIONS))]
)
def disconnect_google_drive(db: Session = Depends(get_db)) -> dict:
    google_tokens.revoke_connection(db, "google_drive")
    return {"success": True, "data": {"status": "disconnected"}}
