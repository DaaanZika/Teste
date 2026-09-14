"""Creates and versions `ComplianceRule` rows (PROMPT 3 FASE I).

A rule's legal content (name, description, legal_source, article,
paragraph, inciso, severity, validation_logic, effective_from) is
IMMUTABLE once created — there is no `update_rule`. Changing a rule always
means `supersede_rule`: the currently open version (the one with
`effective_until IS NULL`) is closed off and a brand new row is inserted.
This is what makes it possible to correctly judge a document dated before
a rule changed: the old text is still there, unmodified, forever.

Every rule (new or superseding) is created `active=False` — matching
app/rules/electoral/README.md: no rule ever starts enforced. A human must
take the separate, deliberate step of calling `activate_rule` after
confirming the official source. Nothing here invents or assumes a legal
value; every field this module accepts is exactly what the caller passed,
never filled in from a guess.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.models.compliance import ComplianceRule
from app.models.enums import AuditAction, RuleSeverity
from app.services.audit.audit_service import record as record_audit


def _current_version(db: Session, rule_id: str) -> ComplianceRule | None:
    """The one row for `rule_id` with no known end date, if any."""
    stmt = select(ComplianceRule).where(
        ComplianceRule.rule_id == rule_id, ComplianceRule.effective_until.is_(None)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_rule_history(db: Session, rule_id: str) -> list[ComplianceRule]:
    stmt = select(ComplianceRule).where(ComplianceRule.rule_id == rule_id).order_by(ComplianceRule.effective_from)
    return list(db.execute(stmt).scalars())


def create_rule(
    db: Session,
    *,
    rule_id: str,
    rule_name: str,
    effective_from: date,
    description: str | None = None,
    legal_source: str | None = None,
    article: str | None = None,
    paragraph: str | None = None,
    inciso: str | None = None,
    severity: RuleSeverity = RuleSeverity.INFO,
    validation_logic: str | None = None,
    election_year: int | None = None,
    user_id: str | None = None,
) -> ComplianceRule:
    """First version of a new rule_id. Fails if this rule_id already has
    any version — use `supersede_rule` to add a later version instead."""
    if _current_version(db, rule_id) is not None or get_rule_history(db, rule_id):
        raise ConflictError(f"A regra '{rule_id}' já existe. Use supersede_rule para uma nova versão.")

    rule = ComplianceRule(
        rule_id=rule_id,
        rule_name=rule_name,
        description=description,
        legal_source=legal_source,
        article=article,
        paragraph=paragraph,
        inciso=inciso,
        severity=severity,
        validation_logic=validation_logic,
        election_year=election_year,
        effective_from=effective_from,
        effective_until=None,
        active=False,
    )
    db.add(rule)
    db.flush()

    record_audit(
        db,
        entity="compliance_rule",
        entity_id=rule.id,
        action=AuditAction.CREATE,
        new_value={"rule_id": rule_id, "effective_from": effective_from.isoformat()},
        user_id=user_id,
    )
    db.commit()
    db.refresh(rule)
    return rule


def supersede_rule(
    db: Session,
    *,
    rule_id: str,
    rule_name: str,
    effective_from: date,
    description: str | None = None,
    legal_source: str | None = None,
    article: str | None = None,
    paragraph: str | None = None,
    inciso: str | None = None,
    severity: RuleSeverity = RuleSeverity.INFO,
    validation_logic: str | None = None,
    election_year: int | None = None,
    user_id: str | None = None,
) -> ComplianceRule:
    """Closes the current open version of `rule_id` and inserts a new one.
    The old version's row is never modified beyond stamping its
    `effective_until` — its legal content stays exactly as it was entered."""
    current = _current_version(db, rule_id)
    if current is None:
        raise NotFoundError(f"Regra '{rule_id}' não encontrada. Use create_rule para a primeira versão.")
    if effective_from <= current.effective_from:
        raise ValidationFailedError(
            f"A nova versão precisa começar depois de {current.effective_from.isoformat()} "
            f"(início da versão atual)."
        )

    current.effective_until = effective_from - timedelta(days=1)

    new_version = ComplianceRule(
        rule_id=rule_id,
        rule_name=rule_name,
        description=description,
        legal_source=legal_source,
        article=article,
        paragraph=paragraph,
        inciso=inciso,
        severity=severity,
        validation_logic=validation_logic,
        election_year=election_year,
        effective_from=effective_from,
        effective_until=None,
        active=False,
        supersedes_id=current.id,
    )
    db.add(new_version)
    db.flush()

    record_audit(
        db,
        entity="compliance_rule",
        entity_id=new_version.id,
        action=AuditAction.CREATE,
        old_value={"supersedes_id": current.id, "previous_effective_until": current.effective_until.isoformat()},
        new_value={"rule_id": rule_id, "effective_from": effective_from.isoformat()},
        user_id=user_id,
    )
    db.commit()
    db.refresh(new_version)
    return new_version


def _get_rule_row(db: Session, id: str) -> ComplianceRule:
    rule = db.get(ComplianceRule, id)
    if rule is None:
        raise NotFoundError(f"Versão de regra {id} não encontrada.")
    return rule


def activate_rule(db: Session, id: str, *, user_id: str | None = None) -> ComplianceRule:
    """Turns a specific rule VERSION on — a deliberate, separate action
    from creating/superseding it (README: never auto-activate)."""
    rule = _get_rule_row(db, id)
    if not rule.active:
        rule.active = True
        record_audit(
            db,
            entity="compliance_rule",
            entity_id=rule.id,
            action=AuditAction.STATUS_CHANGE,
            old_value={"active": False},
            new_value={"active": True},
            user_id=user_id,
        )
        db.commit()
        db.refresh(rule)
    return rule


def deactivate_rule(db: Session, id: str, *, user_id: str | None = None) -> ComplianceRule:
    rule = _get_rule_row(db, id)
    if rule.active:
        rule.active = False
        record_audit(
            db,
            entity="compliance_rule",
            entity_id=rule.id,
            action=AuditAction.STATUS_CHANGE,
            old_value={"active": True},
            new_value={"active": False},
            user_id=user_id,
        )
        db.commit()
        db.refresh(rule)
    return rule
