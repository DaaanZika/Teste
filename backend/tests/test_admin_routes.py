"""/admin — exclusive to SUPER_ADMIN (PROMPT 4 FASE 6). Every test here
proves both the happy path (a real organization gets created, real metrics
come back) and that no other role can reach this area at all."""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.main import app as fastapi_app
from app.models.enums import Role
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture()
def as_super_admin(db_session):
    unique = uuid.uuid4().hex[:8]
    actor = User(
        name="Platform Admin", email=f"super-{unique}@example.com", role=Role.SUPER_ADMIN, active=True
    )
    db_session.add(actor)
    db_session.commit()
    db_session.refresh(actor)
    fastapi_app.dependency_overrides[get_current_user] = lambda: actor
    yield actor
    fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def as_role(db_session):
    def _use(role: Role) -> User:
        unique = uuid.uuid4().hex[:8]
        org = Organization(name=f"Org {unique}", slug=f"org-{unique}")
        db_session.add(org)
        db_session.flush()
        user = User(
            name=f"Test {role.value}",
            email=f"{role.value.lower()}-{unique}@example.com",
            role=role,
            active=True,
            organization_id=org.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        fastapi_app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _use
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def test_admin_area_is_invisible_to_every_organization_role(client, as_role):
    for role in (Role.OWNER, Role.ADMIN, Role.FINANCEIRO, Role.OPERACIONAL, Role.VISUALIZADOR):
        as_role(role)
        response = client.get("/admin/metrics")
        assert response.status_code == 403, role

    response = client.get("/admin/organizations")
    assert response.status_code == 403


def test_admin_area_requires_authentication(client):
    response = client.get("/admin/metrics")
    assert response.status_code in (401, 403)


def test_super_admin_can_create_organization_with_owner(client, as_super_admin):
    unique = uuid.uuid4().hex[:8]
    response = client.post(
        "/admin/organizations",
        json={
            "name": "Campanha Teste Ltda",
            "slug": f"campanha-teste-{unique}",
            "owner_name": "Dona da Campanha",
            "owner_email": f"owner-{unique}@example.com",
            "owner_password": "SenhaForte123!",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Campanha Teste Ltda"
    assert body["status"] == "ACTIVE"
    assert body["owner_user_id"] is not None

    # The owner user was really created, with role OWNER, in this org.
    users_response = client.get(f"/admin/organizations/{body['id']}/users")
    assert users_response.status_code == 200
    users = users_response.json()
    assert len(users) == 1
    assert users[0]["role"] == "OWNER"
    assert users[0]["email"] == f"owner-{unique}@example.com"


def test_creating_organization_with_duplicate_slug_conflicts(client, as_super_admin):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": "Org A",
        "slug": f"dup-slug-{unique}",
        "owner_name": "Dono A",
        "owner_email": f"a-{unique}@example.com",
        "owner_password": "SenhaForte123!",
    }
    first = client.post("/admin/organizations", json=payload)
    assert first.status_code == 200

    payload2 = dict(payload, owner_email=f"b-{unique}@example.com")
    second = client.post("/admin/organizations", json=payload2)
    assert second.status_code == 409


def test_super_admin_can_suspend_and_reactivate_organization(client, as_super_admin):
    unique = uuid.uuid4().hex[:8]
    created = client.post(
        "/admin/organizations",
        json={
            "name": "Org Suspensa",
            "slug": f"org-susp-{unique}",
            "owner_name": "Dono",
            "owner_email": f"susp-{unique}@example.com",
            "owner_password": "SenhaForte123!",
        },
    ).json()

    suspended = client.post(f"/admin/organizations/{created['id']}/status", json={"status": "SUSPENDED"})
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "SUSPENDED"

    reactivated = client.post(f"/admin/organizations/{created['id']}/status", json={"status": "ACTIVE"})
    assert reactivated.json()["status"] == "ACTIVE"


def test_platform_metrics_returns_real_counts(client, as_super_admin, db_session):
    before = client.get("/admin/metrics").json()

    unique = uuid.uuid4().hex[:8]
    client.post(
        "/admin/organizations",
        json={
            "name": "Org Métricas",
            "slug": f"org-metrics-{unique}",
            "owner_name": "Dono",
            "owner_email": f"metrics-{unique}@example.com",
            "owner_password": "SenhaForte123!",
        },
    )

    after = client.get("/admin/metrics").json()
    assert after["organizations_total"] == before["organizations_total"] + 1
    assert after["users_total"] == before["users_total"] + 1
    assert isinstance(after["database_healthy"], bool)


def test_org_admin_cannot_create_super_admin_via_admin_organizations_route(client, as_role):
    """/admin/organizations does not even expose a way to set a role —
    this test documents that no such escalation exists on the org side."""
    as_role(Role.OWNER)
    response = client.post(
        "/admin/organizations",
        json={
            "name": "x",
            "slug": "x",
            "owner_name": "x",
            "owner_email": "x@example.com",
            "owner_password": "SenhaForte123!",
        },
    )
    assert response.status_code == 403
