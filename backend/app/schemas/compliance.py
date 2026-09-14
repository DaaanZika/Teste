from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertStatus, AlertType


class ComplianceAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str | None
    rule_id: str | None
    type: AlertType
    status: AlertStatus
    title: str
    message: str
    entity: str | None
    entity_id: str | None
    created_at: datetime


class ComplianceRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    election_year: int | None
    rule_name: str
    description: str | None
    legal_source: str | None
    article: str | None
    paragraph: str | None
    inciso: str | None
    severity: str
    active: bool
    validation_logic: str | None
