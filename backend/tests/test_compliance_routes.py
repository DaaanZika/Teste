"""app/api/routes/compliance.py — rule management (create/supersede/
activate/deactivate) is ADMIN-only (Permission.MANAGE_RULES); everyone
with VIEW_REPORTS can read the registry and its version history."""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.main import app as fastapi_app
from app.models.enums import Role
from app.models.user import User


@pytest.fixture()
def as_role(db_session):
    def _use(role: Role) -> User:
        unique = uuid.uuid4().hex[:8]
        user = User(name=f"Test {role.value}", email=f"compliance-{role.value.lower()}-{unique}@example.com", role=role, active=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        fastapi_app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _use
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def _rule_id() -> str:
    return f"REGRA-ROTA-{uuid.uuid4().hex[:8]}"


def test_non_admin_cannot_create_rule(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.post(
        "/compliance/rules",
        json={"rule_id": _rule_id(), "rule_name": "x", "effective_from": "2024-01-01"},
    )
    assert response.status_code == 403


def test_admin_can_create_rule_and_it_starts_inactive(client, as_role):
    as_role(Role.ADMIN)
    rid = _rule_id()
    response = client.post(
        "/compliance/rules",
        json={
            "rule_id": rid,
            "rule_name": "Regra de teste",
            "effective_from": "2024-01-01",
            "legal_source": "Fonte de teste",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rule_id"] == rid
    assert body["active"] is False
    assert body["effective_until"] is None


def test_creating_duplicate_rule_id_returns_409(client, as_role):
    as_role(Role.ADMIN)
    rid = _rule_id()
    payload = {"rule_id": rid, "rule_name": "v1", "effective_from": "2024-01-01"}
    first = client.post("/compliance/rules", json=payload)
    assert first.status_code == 200

    second = client.post("/compliance/rules", json=payload)
    assert second.status_code == 409


def test_admin_can_supersede_and_history_shows_both_versions(client, as_role):
    as_role(Role.ADMIN)
    rid = _rule_id()
    client.post("/compliance/rules", json={"rule_id": rid, "rule_name": "v1", "effective_from": "2024-01-01"})

    supersede_response = client.post(
        f"/compliance/rules/{rid}/supersede",
        json={"rule_name": "v2", "effective_from": "2024-07-01", "legal_source": "Nova resolução"},
    )
    assert supersede_response.status_code == 200
    assert supersede_response.json()["rule_name"] == "v2"

    history_response = client.get(f"/compliance/rules/{rid}/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert [r["rule_name"] for r in history] == ["v1", "v2"]
    assert history[0]["effective_until"] == "2024-06-30"


def test_list_rules_current_only_hides_superseded_versions(client, as_role):
    as_role(Role.ADMIN)
    rid = _rule_id()
    client.post("/compliance/rules", json={"rule_id": rid, "rule_name": "v1", "effective_from": "2024-01-01"})
    client.post(f"/compliance/rules/{rid}/supersede", json={"rule_name": "v2", "effective_from": "2024-07-01"})

    current = client.get("/compliance/rules", params={"current_only": True}).json()
    matching_current = [r for r in current if r["rule_id"] == rid]
    assert len(matching_current) == 1
    assert matching_current[0]["rule_name"] == "v2"

    everything = client.get("/compliance/rules", params={"current_only": False}).json()
    matching_all = [r for r in everything if r["rule_id"] == rid]
    assert len(matching_all) == 2


def test_activate_and_deactivate_require_admin(client, as_role):
    as_role(Role.ADMIN)
    rid = _rule_id()
    create_response = client.post(
        "/compliance/rules", json={"rule_id": rid, "rule_name": "v1", "effective_from": "2024-01-01"}
    )
    rule_row_id = create_response.json()["id"]

    as_role(Role.FINANCIAL)
    forbidden = client.post(f"/compliance/rules/{rule_row_id}/activate")
    assert forbidden.status_code == 403

    as_role(Role.ADMIN)
    activated = client.post(f"/compliance/rules/{rule_row_id}/activate")
    assert activated.status_code == 200
    assert activated.json()["active"] is True

    deactivated = client.post(f"/compliance/rules/{rule_row_id}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False


def test_supersede_unknown_rule_returns_404(client, as_role):
    as_role(Role.ADMIN)
    response = client.post(
        f"/compliance/rules/{_rule_id()}/supersede", json={"rule_name": "v2", "effective_from": "2024-01-01"}
    )
    assert response.status_code == 404
