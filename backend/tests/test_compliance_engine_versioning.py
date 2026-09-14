"""app/services/compliance/engine.py — get_active_rules/run_active_rules
must pick the rule VERSION that was actually in effect on the reference
date, not just today's version (PROMPT 3 FASE I: a document from before a
rule changed must be judged by the text that applied to it then)."""
from __future__ import annotations

import uuid
from datetime import date

from app.services.compliance import rule_registry
from app.services.compliance.engine import (
    VALIDATORS,
    RuleViolation,
    get_active_rules,
    register_validator,
    run_active_rules,
)


def _rule_id() -> str:
    return f"REGRA-ENGINE-{uuid.uuid4().hex[:8]}"


def test_inactive_rule_never_runs_regardless_of_date(db_session):
    rid = _rule_id()
    rule_registry.create_rule(db_session, rule_id=rid, rule_name="v1", effective_from=date(2024, 1, 1))
    # never activated

    active_today = get_active_rules(db_session, reference_date=date(2024, 6, 1))
    assert all(r.rule_id != rid for r in active_today)


def test_active_rule_is_selected_within_its_effective_window(db_session):
    rid = _rule_id()
    v1 = rule_registry.create_rule(db_session, rule_id=rid, rule_name="v1", effective_from=date(2024, 1, 1))
    rule_registry.activate_rule(db_session, v1.id)

    within = get_active_rules(db_session, reference_date=date(2024, 6, 1))
    assert any(r.id == v1.id for r in within)

    before = get_active_rules(db_session, reference_date=date(2023, 12, 31))
    assert all(r.id != v1.id for r in before)


def test_a_document_dated_before_a_supersession_is_judged_by_the_old_version(db_session):
    """The core versioning guarantee: pick the rule that was law on the
    transaction's own date, not the rule in force today."""
    rid = _rule_id()
    v1 = rule_registry.create_rule(
        db_session, rule_id=rid, rule_name="Limite antigo", effective_from=date(2023, 1, 1)
    )
    rule_registry.activate_rule(db_session, v1.id)

    v2 = rule_registry.supersede_rule(
        db_session, rule_id=rid, rule_name="Limite novo", effective_from=date(2024, 1, 1)
    )
    rule_registry.activate_rule(db_session, v2.id)

    # A transaction dated in 2023 must resolve to v1, not v2.
    old_transaction_rules = get_active_rules(db_session, reference_date=date(2023, 6, 1))
    assert any(r.id == v1.id for r in old_transaction_rules)
    assert all(r.id != v2.id for r in old_transaction_rules)

    # A transaction dated in 2024 must resolve to v2, not v1.
    new_transaction_rules = get_active_rules(db_session, reference_date=date(2024, 6, 1))
    assert any(r.id == v2.id for r in new_transaction_rules)
    assert all(r.id != v1.id for r in new_transaction_rules)


def test_run_active_rules_uses_reference_date_to_pick_the_right_validator_threshold(db_session):
    rid = _rule_id()
    v1 = rule_registry.create_rule(
        db_session, rule_id=rid, rule_name="v1", effective_from=date(2023, 1, 1), validation_logic="_test_limit_v1"
    )
    rule_registry.activate_rule(db_session, v1.id)
    v2 = rule_registry.supersede_rule(
        db_session, rule_id=rid, rule_name="v2", effective_from=date(2024, 1, 1), validation_logic="_test_limit_v2"
    )
    rule_registry.activate_rule(db_session, v2.id)

    def validator_v1(context: dict) -> RuleViolation | None:
        return RuleViolation(rule_id=rid, message="violou v1")

    def validator_v2(context: dict) -> RuleViolation | None:
        return RuleViolation(rule_id=rid, message="violou v2")

    original = dict(VALIDATORS)
    try:
        register_validator("_test_limit_v1", validator_v1)
        register_validator("_test_limit_v2", validator_v2)

        violations_2023 = run_active_rules(db_session, {}, reference_date=date(2023, 6, 1))
        assert any(v.message == "violou v1" for v in violations_2023)
        assert all(v.message != "violou v2" for v in violations_2023)

        violations_2024 = run_active_rules(db_session, {}, reference_date=date(2024, 6, 1))
        assert any(v.message == "violou v2" for v in violations_2024)
        assert all(v.message != "violou v1" for v in violations_2024)
    finally:
        VALIDATORS.clear()
        VALIDATORS.update(original)


def test_run_active_rules_skips_rules_without_a_registered_validator(db_session):
    rid = _rule_id()
    v1 = rule_registry.create_rule(
        db_session, rule_id=rid, rule_name="v1", effective_from=date(2024, 1, 1), validation_logic="_never_registered"
    )
    rule_registry.activate_rule(db_session, v1.id)

    # Must not raise, even though no validator exists for this rule.
    violations = run_active_rules(db_session, {}, reference_date=date(2024, 6, 1))
    assert all(v.rule_id != rid for v in violations)
