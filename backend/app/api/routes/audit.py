from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import Permission
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_permission(Permission.VIEW_AUDIT))])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    entity: str | None = None, entity_id: str | None = None, db: Session = Depends(get_db)
) -> list[AuditLogRead]:
    from app.services.reports.report_service import audit_report

    result = audit_report(db, entity=entity, entity_id=entity_id)
    return [AuditLogRead.model_validate(log) for log in result["changes"]]
