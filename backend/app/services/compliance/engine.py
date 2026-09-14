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


def get_active_rules(db: Session) -> list[ComplianceRule]:
    stmt = select(ComplianceRule).where(ComplianceRule.active.is_(True))
    return list(db.execute(stmt).scalars())


def run_active_rules(db: Session, context: dict[str, Any]) -> list[RuleViolation]:
    """Runs every active, source-verified rule against `context` and returns violations.

    Returns an empty list whenever no rules are active — which is the
    expected state for V1 until rules are confirmed and entered.
    """
    violations: list[RuleViolation] = []
    for rule in get_active_rules(db):
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
