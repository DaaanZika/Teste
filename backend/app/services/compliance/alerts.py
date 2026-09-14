"""Alert creation helpers used by the document/finance pipelines."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.compliance import ComplianceAlert
from app.models.enums import AlertType


def raise_alert(
    db: Session,
    *,
    type: AlertType,
    title: str,
    message: str,
    entity: str | None = None,
    entity_id: str | None = None,
    campaign_id: str | None = None,
    rule_id: str | None = None,
) -> ComplianceAlert:
    alert = ComplianceAlert(
        type=type,
        title=title,
        message=message,
        entity=entity,
        entity_id=entity_id,
        campaign_id=campaign_id,
        rule_id=rule_id,
    )
    db.add(alert)
    db.flush()
    return alert
