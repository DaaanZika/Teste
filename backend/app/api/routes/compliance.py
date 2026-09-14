from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import Permission
from app.models.compliance import ComplianceAlert, ComplianceRule
from app.models.enums import AlertStatus
from app.schemas.compliance import ComplianceAlertRead, ComplianceRuleRead

router = APIRouter(
    prefix="/compliance", tags=["compliance"], dependencies=[Depends(require_permission(Permission.VIEW_REPORTS))]
)


@router.get("/alerts", response_model=list[ComplianceAlertRead])
def list_alerts(
    status: AlertStatus | None = None, campaign_id: str | None = None, db: Session = Depends(get_db)
) -> list[ComplianceAlertRead]:
    stmt = select(ComplianceAlert).order_by(ComplianceAlert.created_at.desc())
    if status is not None:
        stmt = stmt.where(ComplianceAlert.status == status)
    if campaign_id is not None:
        stmt = stmt.where(ComplianceAlert.campaign_id == campaign_id)
    alerts = db.execute(stmt).scalars()
    return [ComplianceAlertRead.model_validate(a) for a in alerts]


@router.get("/rules", response_model=list[ComplianceRuleRead])
def list_rules(db: Session = Depends(get_db)) -> list[ComplianceRuleRead]:
    """Returns the compliance rule registry. Empty in V1 — see app/rules/electoral/README.md."""
    rules = db.execute(select(ComplianceRule)).scalars()
    return [ComplianceRuleRead.model_validate(r) for r in rules]
