from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db, require_permission
from app.core.rbac import Permission
from app.models.compliance import ComplianceAlert, ComplianceRule
from app.models.enums import AlertStatus
from app.schemas.compliance import (
    ComplianceAlertRead,
    ComplianceRuleCreate,
    ComplianceRuleRead,
    ComplianceRuleSupersede,
)
from app.services.compliance import rule_registry

router = APIRouter(
    prefix="/compliance", tags=["compliance"], dependencies=[Depends(require_permission(Permission.VIEW_REPORTS))]
)

_can_manage_rules = Depends(require_permission(Permission.MANAGE_RULES))


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
def list_rules(current_only: bool = True, db: Session = Depends(get_db)) -> list[ComplianceRuleRead]:
    """Returns the compliance rule registry. Empty in V1 — see
    app/rules/electoral/README.md. `current_only=true` (default) hides
    superseded historical versions (effective_until IS NOT NULL); pass
    `current_only=false` to see every version ever entered."""
    stmt = select(ComplianceRule).order_by(ComplianceRule.rule_id, ComplianceRule.effective_from)
    if current_only:
        stmt = stmt.where(ComplianceRule.effective_until.is_(None))
    rules = db.execute(stmt).scalars()
    return [ComplianceRuleRead.model_validate(r) for r in rules]


@router.get("/rules/{rule_id}/history", response_model=list[ComplianceRuleRead])
def rule_history(rule_id: str, db: Session = Depends(get_db)) -> list[ComplianceRuleRead]:
    """Every version ever entered for `rule_id`, oldest first — the full,
    never-overwritten audit trail of how this rule's text/threshold/citation
    changed over time."""
    versions = rule_registry.get_rule_history(db, rule_id)
    return [ComplianceRuleRead.model_validate(v) for v in versions]


@router.post("/rules", response_model=ComplianceRuleRead, dependencies=[_can_manage_rules])
def create_rule(
    payload: ComplianceRuleCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> ComplianceRuleRead:
    """ADMIN only. Always created inactive — a separate, deliberate call to
    POST /compliance/rules/{id}/activate is required (see
    app/rules/electoral/README.md: no rule is ever auto-enforced)."""
    rule = rule_registry.create_rule(db, **payload.model_dump(), user_id=user_id)
    return ComplianceRuleRead.model_validate(rule)


@router.post("/rules/{rule_id}/supersede", response_model=ComplianceRuleRead, dependencies=[_can_manage_rules])
def supersede_rule(
    rule_id: str,
    payload: ComplianceRuleSupersede,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ComplianceRuleRead:
    """ADMIN only. Closes the current version's effective range and inserts
    a new one — the old version's row is never modified beyond that date
    stamp, so a document from before the change stays judged correctly."""
    rule = rule_registry.supersede_rule(db, rule_id=rule_id, **payload.model_dump(), user_id=user_id)
    return ComplianceRuleRead.model_validate(rule)


@router.post("/rules/{id}/activate", response_model=ComplianceRuleRead, dependencies=[_can_manage_rules])
def activate_rule(id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)) -> ComplianceRuleRead:
    rule = rule_registry.activate_rule(db, id, user_id=user_id)
    return ComplianceRuleRead.model_validate(rule)


@router.post("/rules/{id}/deactivate", response_model=ComplianceRuleRead, dependencies=[_can_manage_rules])
def deactivate_rule(id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)) -> ComplianceRuleRead:
    rule = rule_registry.deactivate_rule(db, id, user_id=user_id)
    return ComplianceRuleRead.model_validate(rule)
