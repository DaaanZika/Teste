from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertStatus, AlertType, RuleSeverity


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
    effective_from: date
    effective_until: date | None
    supersedes_id: str | None


class ComplianceRuleCreate(BaseModel):
    """First version of a new rule (ADMIN only). Every field here is
    exactly what a human confirmed against an official source — nothing is
    filled in from a guess (see app/rules/electoral/README.md)."""

    rule_id: str
    rule_name: str
    effective_from: date
    description: str | None = None
    legal_source: str | None = None
    article: str | None = None
    paragraph: str | None = None
    inciso: str | None = None
    severity: RuleSeverity = RuleSeverity.INFO
    validation_logic: str | None = None
    election_year: int | None = None


class ComplianceRuleSupersede(BaseModel):
    """A new version of an existing rule_id (ADMIN only) — the current open
    version is closed, never edited in place."""

    rule_name: str
    effective_from: date
    description: str | None = None
    legal_source: str | None = None
    article: str | None = None
    paragraph: str | None = None
    inciso: str | None = None
    severity: RuleSeverity = RuleSeverity.INFO
    validation_logic: str | None = None
    election_year: int | None = None
