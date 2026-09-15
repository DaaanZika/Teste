from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db, require_permission
from app.core.config import get_settings
from app.core.health import check_database, check_redis
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope
from app.models.enums import GmailSuggestionStatus
from app.models.user import User
from app.schemas.document import DocumentUploadResponse, DocumentRead
from app.schemas.gmail import GmailRejectRequest, GmailScanRequest, GmailScanResponse, GmailSuggestionRead
from app.schemas.integrations import IntegrationStatus, IntegrationsStatusResponse
from app.services.auth import google_oauth
from app.services.integrations import gmail_service, google_tokens
from app.services.ocr.engine import is_tesseract_available

router = APIRouter(prefix="/integrations", tags=["integrations"])

DRIVE_STATE_COOKIE_NAME = "campanhas_oauth_state_drive"
GMAIL_STATE_COOKIE_NAME = "campanhas_oauth_state_gmail"

_can_manage_integrations = Depends(require_permission(Permission.MANAGE_INTEGRATIONS))
_can_manage_documents = Depends(require_permission(Permission.MANAGE_DOCUMENTS))
_can_view_documents = Depends(require_permission(Permission.VIEW_DOCUMENTS))


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
    redis_check = check_redis()  # None when QUEUE_BACKEND != "redis" — not required by current config

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
            detail=None if gmail_connection else "Não conectado",
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
        queue=IntegrationStatus(
            name="Fila assíncrona",
            connected=settings.queue_backend == "redis" and bool(redis_check and redis_check.healthy),
            detail=(
                None
                if settings.queue_backend == "redis" and redis_check and redis_check.healthy
                else "QUEUE_BACKEND=inline (processamento síncrono, padrão) — não requer Redis"
                if settings.queue_backend != "redis"
                else (redis_check.detail if redis_check else "REDIS_URL não configurado")
            ),
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


@router.get("/gmail/connect")
def connect_gmail(user: User = Depends(require_permission(Permission.MANAGE_INTEGRATIONS))) -> RedirectResponse:
    """ADMIN only: starts the incremental-consent flow for read-only Gmail
    access (separate from login — see app/services/auth/google_oauth.py)."""
    state = google_oauth.generate_state()
    authorization_url = google_oauth.build_authorization_url(
        state, scope=google_oauth.GMAIL_SCOPES, access_type="offline", prompt="consent"
    )
    settings = get_settings()
    redirect = RedirectResponse(authorization_url, status_code=302)
    redirect.set_cookie(
        GMAIL_STATE_COOKIE_NAME, state, max_age=600, httponly=True, secure=not settings.debug, samesite="lax"
    )
    return redirect


@router.post("/gmail/disconnect", dependencies=[_can_manage_integrations])
def disconnect_gmail(db: Session = Depends(get_db)) -> dict:
    google_tokens.revoke_connection(db, "gmail")
    return {"success": True, "data": {"status": "disconnected"}}


@router.post("/gmail/scan", response_model=GmailScanResponse, dependencies=[_can_manage_documents])
def scan_gmail(
    payload: GmailScanRequest,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> GmailScanResponse:
    """Detects candidate attachments — never imports anything by itself
    (PROMPT 3 §13/§45). Safe to call repeatedly: already-seen attachments
    are skipped, not duplicated."""
    new_suggestions = gmail_service.scan_inbox(
        db, organization_id=organization_id, campaign_id=payload.campaign_id, max_results=payload.max_results
    )
    return GmailScanResponse(new_suggestions=[GmailSuggestionRead.model_validate(s) for s in new_suggestions])


@router.get("/gmail/suggestions", response_model=list[GmailSuggestionRead], dependencies=[_can_view_documents])
def list_gmail_suggestions(
    status: GmailSuggestionStatus | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> list[GmailSuggestionRead]:
    suggestions = gmail_service.list_suggestions(db, organization_id=organization_id, status=status)
    return [GmailSuggestionRead.model_validate(s) for s in suggestions]


@router.post(
    "/gmail/suggestions/{suggestion_id}/confirm",
    response_model=DocumentUploadResponse,
    dependencies=[_can_manage_documents],
)
def confirm_gmail_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(require_organization_scope),
) -> DocumentUploadResponse:
    """The only path by which a Gmail suggestion becomes a real Document —
    downloads the attachment for real and runs it through the exact same
    upload pipeline as a manual upload (validation, duplicate detection,
    audit log included)."""
    result = gmail_service.confirm_suggestion(db, suggestion_id, user_id=user_id, organization_id=organization_id)
    return DocumentUploadResponse(
        document=DocumentRead.model_validate(result.document),
        possible_duplicate=result.possible_duplicate,
        duplicate_reasons=result.duplicate_reasons,
    )


@router.post(
    "/gmail/suggestions/{suggestion_id}/reject",
    response_model=GmailSuggestionRead,
    dependencies=[_can_manage_documents],
)
def reject_gmail_suggestion(
    suggestion_id: str,
    payload: GmailRejectRequest,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> GmailSuggestionRead:
    suggestion = gmail_service.reject_suggestion(
        db, suggestion_id, reason=payload.reason, organization_id=organization_id
    )
    return GmailSuggestionRead.model_validate(suggestion)
