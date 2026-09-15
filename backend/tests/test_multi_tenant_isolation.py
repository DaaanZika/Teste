"""Cross-organization isolation (PROMPT 4's explicit, non-negotiable rule):
a user in Org A must never see, edit, or delete Org B's data, and this
must be enforced in the backend, never assumed from frontend filtering.
Every test here creates two REAL, separate organizations and proves one
cannot reach the other's data — not "code review says it can't."
"""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.main import app as fastapi_app
from app.models.campaign import Campaign
from app.models.enums import Role
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture()
def two_orgs(db_session):
    """Org A (with a campaign) and Org B (with its own OWNER), fully
    independent tenants."""
    unique = uuid.uuid4().hex[:8]
    org_a = Organization(name=f"Org A {unique}", slug=f"org-a-{unique}")
    org_b = Organization(name=f"Org B {unique}", slug=f"org-b-{unique}")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    campaign_a = Campaign(name="Campanha A", organization_id=org_a.id)
    db_session.add(campaign_a)

    owner_a = User(
        name="Owner A", email=f"owner-a-{unique}@example.com", role=Role.OWNER, active=True, organization_id=org_a.id
    )
    owner_b = User(
        name="Owner B", email=f"owner-b-{unique}@example.com", role=Role.OWNER, active=True, organization_id=org_b.id
    )
    db_session.add_all([owner_a, owner_b])
    db_session.commit()
    for obj in (org_a, org_b, campaign_a, owner_a, owner_b):
        db_session.refresh(obj)
    return org_a, org_b, campaign_a, owner_a, owner_b


def _act_as(user: User) -> None:
    fastapi_app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
def _cleanup_override():
    yield
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def test_user_b_cannot_list_org_a_campaign(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/campaigns")
    assert response.status_code == 200
    assert all(c["id"] != campaign_a.id for c in response.json())


def test_user_b_cannot_get_org_a_campaign_by_id(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get(f"/campaigns/{campaign_a.id}")
    assert response.status_code == 404


def test_user_b_cannot_update_org_a_campaign(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.put(f"/campaigns/{campaign_a.id}", json={"name": "Hijacked"})
    assert response.status_code == 404


def test_created_campaign_is_forced_into_callers_own_org_not_client_supplied(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.post("/campaigns", json={"name": "Nova Campanha B"})
    assert response.status_code == 200
    created_id = response.json()["id"]

    # Owner A must never see it.
    _act_as(owner_a)
    listing = client.get("/campaigns")
    assert all(c["id"] != created_id for c in listing.json())


def test_user_b_cannot_see_org_a_users(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/users")
    assert response.status_code == 200
    assert all(u["id"] != owner_a.id for u in response.json())


def test_user_b_cannot_edit_org_a_user(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.patch(f"/users/{owner_a.id}", json={"active": False})
    assert response.status_code == 404


def test_created_user_lands_in_callers_own_org_never_a_client_supplied_one(client, two_orgs, db_session):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.post(
        "/users",
        json={
            "name": "Nova Pessoa",
            "email": f"nova-{uuid.uuid4().hex[:8]}@example.com",
            "password": "SenhaForte123!",
            "role": "VISUALIZADOR",
            # Attempting to smuggle a different org id — must be ignored.
            "organization_id": org_a.id,
        },
    )
    assert response.status_code == 200
    created = db_session.get(User, response.json()["id"])
    assert created.organization_id == org_b.id


def test_user_a_cannot_create_super_admin(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_a)
    response = client.post(
        "/users",
        json={
            "name": "Tentativa",
            "email": f"escalate-{uuid.uuid4().hex[:8]}@example.com",
            "password": "SenhaForte123!",
            "role": "SUPER_ADMIN",
        },
    )
    assert response.status_code == 403


def test_org_a_owner_cannot_reach_admin_area(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_a)
    response = client.get("/admin/metrics")
    assert response.status_code == 403
    response = client.get("/admin/organizations")
    assert response.status_code == 403


def test_own_organization_endpoint_only_ever_returns_callers_own_org(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_a)
    response = client.get("/organization")
    assert response.status_code == 200
    assert response.json()["id"] == org_a.id

    _act_as(owner_b)
    response = client.get("/organization")
    assert response.json()["id"] == org_b.id


def test_super_admin_without_organization_gets_403_on_regular_org_routes(client, db_session):
    unique = uuid.uuid4().hex[:8]
    super_admin = User(
        name="Platform Admin", email=f"su-{unique}@example.com", role=Role.SUPER_ADMIN, active=True
    )
    db_session.add(super_admin)
    db_session.commit()
    db_session.refresh(super_admin)

    _act_as(super_admin)
    response = client.get("/campaigns")
    assert response.status_code == 403
    response = client.get("/organization")
    assert response.status_code == 403
