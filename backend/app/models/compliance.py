from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import Boolean, Date, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AlertStatus, AlertType, RuleSeverity


class ComplianceRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One VERSION of an electoral compliance rule, valid for a known date
    range (PROMPT 3 FASE I — a rule text/threshold/citation changes when a
    new TSE resolution supersedes an old one; the old text must stay
    readable forever to correctly judge a document from before the change).

    `rule_id` is a stable business identifier shared by every version of
    "the same" rule — it is intentionally NOT unique on this table; what's
    unique is `(rule_id, effective_from)`. A version is never edited in
    place once created: `app/services/compliance/rule_registry.py` is the
    only way to change a rule, and "changing" it always means inserting a
    new row (`supersede_rule`) with `supersedes_id` pointing at the row it
    replaces, never an UPDATE of the old row's legal fields. `active` is
    the one field that IS mutated in place — it reflects operational
    readiness ("has a human confirmed this version's source and turned the
    validator on"), not the law itself changing.

    Rules are data, not code: `validation_logic` names a validator
    implemented in `services.compliance.engine`, so a rule can be
    activated/deactivated or superseded without a deploy. No rule is
    inserted here without a confirmed official source
    (see app/rules/electoral/README.md) — this table starts empty in V1.
    """

    __tablename__ = "compliance_rules"

    rule_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    election_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    article: Mapped[str | None] = mapped_column(String(50), nullable=True)
    paragraph: Mapped[str | None] = mapped_column(String(50), nullable=True)
    inciso: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[RuleSeverity] = mapped_column(
        SAEnum(RuleSeverity, native_enum=False, length=20), default=RuleSeverity.INFO, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_logic: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Identifier of the validator function in services.compliance.engine"
    )

    # The date range this specific version is/was in effect. `effective_until`
    # is inclusive and NULL means "still current, no known end date" — the
    # normal state for the latest version of an active rule_id.
    effective_from: Mapped[date_type] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    # The previous version this row replaces, if any — NULL for a rule_id's
    # first-ever version. Forms a version chain without ever deleting or
    # mutating the row it points to.
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("compliance_rules.id"), nullable=True)


class ComplianceAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An alert raised by the compliance/document pipeline for human attention."""

    __tablename__ = "compliance_alerts"

    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("compliance_rules.id"), nullable=True)

    type: Mapped[AlertType] = mapped_column(SAEnum(AlertType, native_enum=False, length=20), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(AlertStatus, native_enum=False, length=20), default=AlertStatus.OPEN, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    entity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
