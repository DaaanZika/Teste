from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.services.documents.document_service import get_document_in_org
from app.services.finance.expense_service import get_expense_in_org
from app.services.finance.revenue_service import get_revenue_in_org

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_permission(Permission.VIEW_AUDIT))])


def _verify_entity_in_org(db: Session, entity: str, entity_id: str, organization_id: str) -> None:
    """404s (never leaking cross-org existence) when `entity_id` belongs to
    another organization. Every entity type audited here is checked with
    the exact same org-ownership rule its own route/service already uses."""
    if entity == "document":
        get_document_in_org(db, entity_id, organization_id=organization_id)
    elif entity == "expense":
        get_expense_in_org(db, entity_id, organization_id=organization_id)
    elif entity == "revenue":
        get_revenue_in_org(db, entity_id, organization_id=organization_id)
    elif entity == "campaign":
        campaign = db.get(Campaign, entity_id)
        if campaign is None or campaign.organization_id != organization_id:
            raise NotFoundError(f"Campanha {entity_id} não encontrada.")
    elif entity == "user":
        user = db.get(User, entity_id)
        if user is None or user.organization_id != organization_id:
            raise NotFoundError(f"Usuário {entity_id} não encontrado.")
    # Any other entity type (e.g. "integration", "compliance_rule" — platform/
    # global-ish concepts with no organization_id of their own) falls through
    # unchecked; those audit trails were never organization-scoped data.


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    entity: str | None = None,
    entity_id: str | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> list[AuditLogRead]:
    from app.services.reports.report_service import audit_report

    if entity is not None and entity_id is not None:
        _verify_entity_in_org(db, entity, entity_id, organization_id)
        result = audit_report(db, entity=entity, entity_id=entity_id)
    else:
        # No specific entity requested — only ever show entries this
        # organization's own actions recorded (never entries with no
        # organization_id, and never another organization's).
        result = audit_report(db, entity=entity, entity_id=entity_id, organization_id=organization_id)

    return [AuditLogRead.model_validate(log) for log in result["changes"]]
