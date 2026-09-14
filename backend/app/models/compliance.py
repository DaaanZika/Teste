from __future__ import annotations

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AlertStatus, AlertType, RuleSeverity


class ComplianceRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single electoral compliance rule.

    Rules are data, not code: `validation_logic` names a validator
    implemented in `services.compliance.engine`, so a rule can be
    activated/deactivated or have its legal citation corrected without a
    deploy. No rule is inserted here without a confirmed official source
    (see app/rules/electoral/README.md) — this table starts empty in V1.
    """

    __tablename__ = "compliance_rules"

    rule_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
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
