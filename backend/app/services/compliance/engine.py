"""Compliance rule engine — architecture only in V1.

Rules are stored as data (`ComplianceRule` rows), never hardcoded values or
legal thresholds. Per PROMPT 1 section 19, no rule with an unconfirmed
legal source is registered in this version: `compliance_rules` starts
empty (see app/rules/electoral/README.md). This module exists so that,
once a rule is entered with a verified official source, activating it
(`active=True`) is enough to make it run — no code change required beyond
registering its validator function here.

`validation_logic` on a rule names a key in `VALIDATORS`. A rule whose
`validation_logic` has no registered validator is skipped and logged,
never guessed at.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compliance import ComplianceRule

logger = logging.getLogger("app.compliance")


@dataclass
class RuleViolation:
    rule_id: str
    message: str


Validator = Callable[[dict[str, Any]], RuleViolation | None]

# Populated as real, source-verified rules are implemented. Empty in V1.
VALIDATORS: dict[str, Validator] = {}


def register_validator(name: str, fn: Validator) -> None:
    VALIDATORS[name] = fn


def get_active_rules(db: Session, *, reference_date: date | None = None) -> list[ComplianceRule]:
    """Active rule VERSIONS in effect on `reference_date` (default: today).

    A rule_id can have several rows over time (see
    app/services/compliance/rule_registry.py) — this returns, per rule_id,
    only the version whose [effective_from, effective_until] window covers
    `reference_date`, so a document dated before a rule changed is judged
    by the text that actually applied to it, not by today's version.
    """
    as_of = reference_date or date.today()
    stmt = select(ComplianceRule).where(
        ComplianceRule.active.is_(True),
        ComplianceRule.effective_from <= as_of,
        (ComplianceRule.effective_until.is_(None)) | (ComplianceRule.effective_until >= as_of),
    )
    return list(db.execute(stmt).scalars())


def run_active_rules(db: Session, context: dict[str, Any], *, reference_date: date | None = None) -> list[RuleViolation]:
    """Runs every active, source-verified rule version in effect on
    `reference_date` (default: today) against `context` and returns
    violations. Pass the transaction's own date (e.g. an expense's `date`)
    to judge it against the rule that was actually law then — falling back
    to today only when no such date is available.

    Returns an empty list whenever no rules are active — which is the
    expected state for V1 until rules are confirmed and entered.
    """
    violations: list[RuleViolation] = []
    for rule in get_active_rules(db, reference_date=reference_date):
        validator = VALIDATORS.get(rule.validation_logic or "")
        if validator is None:
            logger.warning(
                "Compliance rule %s (%s) has no registered validator '%s'; skipping.",
                rule.rule_id, rule.rule_name, rule.validation_logic,
            )
            continue
        violation = validator(context)
        if violation is not None:
            violations.append(violation)
    return violations
