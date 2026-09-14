"""app/services/compliance/rule_registry.py — a rule's legal content is
immutable once created; "changing" it always means a new version row,
never an UPDATE of the old one (PROMPT 3 FASE I)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.models.enums import RuleSeverity
from app.services.compliance import rule_registry


def _rule_id() -> str:
    return f"REGRA-TESTE-{uuid.uuid4().hex[:8]}"


def test_create_rule_starts_inactive_and_open_ended(db_session):
    rid = _rule_id()
    rule = rule_registry.create_rule(
        db_session,
        rule_id=rid,
        rule_name="Limite de doação PF (exemplo de teste)",
        effective_from=date(2024, 1, 1),
        legal_source="Fonte de teste — não é uma regra real",
        article="Art. 1",
        severity=RuleSeverity.WARNING,
    )
    assert rule.active is False  # README: never auto-activate
    assert rule.effective_from == date(2024, 1, 1)
    assert rule.effective_until is None
    assert rule.supersedes_id is None


def test_create_rule_twice_with_same_id_raises_conflict(db_session):
    rid = _rule_id()
    rule_registry.create_rule(db_session, rule_id=rid, rule_name="v1", effective_from=date(2024, 1, 1))

    with pytest.raises(ConflictError):
        rule_registry.create_rule(db_session, rule_id=rid, rule_name="v1 outra vez", effective_from=date(2024, 6, 1))


def test_supersede_closes_old_version_without_mutating_its_content(db_session):
    rid = _rule_id()
    v1 = rule_registry.create_rule(
        db_session, rule_id=rid, rule_name="Texto original", effective_from=date(2024, 1, 1), legal_source="Fonte A"
    )
    v1_id = v1.id

    v2 = rule_registry.supersede_rule(
        db_session,
        rule_id=rid,
        rule_name="Texto atualizado",
        effective_from=date(2024, 7, 1),
        legal_source="Fonte B (nova resolução)",
    )

    db_session.refresh(v1)
    assert v1.id == v1_id
    assert v1.rule_name == "Texto original"  # never mutated
    assert v1.legal_source == "Fonte A"  # never mutated
    assert v1.effective_until == date(2024, 6, 30)  # closed the day before v2 starts

    assert v2.rule_name == "Texto atualizado"
    assert v2.effective_until is None
    assert v2.supersedes_id == v1_id


def test_supersede_unknown_rule_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        rule_registry.supersede_rule(db_session, rule_id=_rule_id(), rule_name="x", effective_from=date(2024, 1, 1))


def test_supersede_with_effective_from_not_after_current_raises_validation_error(db_session):
    rid = _rule_id()
    rule_registry.create_rule(db_session, rule_id=rid, rule_name="v1", effective_from=date(2024, 6, 1))

    with pytest.raises(ValidationFailedError):
        rule_registry.supersede_rule(db_session, rule_id=rid, rule_name="v2", effective_from=date(2024, 6, 1))

    with pytest.raises(ValidationFailedError):
        rule_registry.supersede_rule(db_session, rule_id=rid, rule_name="v2", effective_from=date(2024, 1, 1))


def test_get_rule_history_returns_every_version_oldest_first(db_session):
    rid = _rule_id()
    rule_registry.create_rule(db_session, rule_id=rid, rule_name="v1", effective_from=date(2023, 1, 1))
    rule_registry.supersede_rule(db_session, rule_id=rid, rule_name="v2", effective_from=date(2024, 1, 1))
    rule_registry.supersede_rule(db_session, rule_id=rid, rule_name="v3", effective_from=date(2025, 1, 1))

    history = rule_registry.get_rule_history(db_session, rid)
    assert [r.rule_name for r in history] == ["v1", "v2", "v3"]
    assert history[0].effective_until == date(2023, 12, 31)
    assert history[1].effective_until == date(2024, 12, 31)
    assert history[2].effective_until is None


def test_activate_and_deactivate_toggle_without_creating_a_new_version(db_session):
    rid = _rule_id()
    rule = rule_registry.create_rule(db_session, rule_id=rid, rule_name="v1", effective_from=date(2024, 1, 1))

    activated = rule_registry.activate_rule(db_session, rule.id)
    assert activated.id == rule.id
    assert activated.active is True

    deactivated = rule_registry.deactivate_rule(db_session, rule.id)
    assert deactivated.id == rule.id
    assert deactivated.active is False

    assert len(rule_registry.get_rule_history(db_session, rid)) == 1  # still just one row


def test_activate_unknown_id_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        rule_registry.activate_rule(db_session, "does-not-exist")
