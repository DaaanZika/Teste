"""RBAC per new-role (PROMPT 4), exercised against real routes — test_rbac.py
already proves the permission matrix is correct in isolation; this proves
it's actually wired into the endpoints for every role the spec names:
SUPER_ADMIN, OWNER, FINANCEIRO, OPERACIONAL, VISUALIZADOR (CUSTOM is
covered separately since its capabilities are per-user, not per-role)."""
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
def as_role(db_session):
    def _use(role: Role) -> User:
        unique = uuid.uuid4().hex[:8]
        org = Organization(name=f"Org {unique}", slug=f"org-{unique}")
        db_session.add(org)
        db_session.flush()
        campaign = Campaign(name="Campanha", organization_id=org.id)
        db_session.add(campaign)
        user = User(
            name=f"Test {role.value}",
            email=f"rbac2-{role.value.lower()}-{unique}@example.com",
            role=role,
            active=True,
            organization_id=org.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        db_session.refresh(campaign)
        fastapi_app.dependency_overrides[get_current_user] = lambda: user
        user.campaign = campaign  # stash for convenience in tests below
        return user

    yield _use
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def test_owner_has_full_access(client, as_role):
    as_role(Role.OWNER)
    assert client.get("/campaigns").status_code == 200
    assert client.get("/users").status_code == 200
    assert client.get("/organization").status_code == 200
    assert client.post("/campaigns", json={"name": "Nova"}).status_code == 200


def test_financeiro_can_manage_finance_but_not_users(client, as_role):
    user = as_role(Role.FINANCEIRO)
    assert client.get("/expenses").status_code == 200
    assert client.post("/expenses", json={"campaign_id": user.campaign.id, "description": "x"}).status_code == 200
    assert client.get("/users").status_code == 403


def test_operacional_can_view_and_manage_documents_but_not_create_finance(client, as_role):
    as_role(Role.OPERACIONAL)
    assert client.get("/documents").status_code == 200
    assert client.get("/expenses").status_code == 200
    response = client.post("/expenses", json={"description": "tentativa"})
    assert response.status_code == 403


def test_visualizador_can_only_view(client, as_role):
    user = as_role(Role.VISUALIZADOR)
    assert client.get("/expenses").status_code == 200
    assert client.get("/documents").status_code == 200
    assert client.get("/finance/summary").status_code == 200
    assert client.post("/expenses", json={"campaign_id": user.campaign.id}).status_code == 403
    assert client.post("/campaigns", json={"name": "x"}).status_code == 403


def test_visualizador_cannot_manage_users_or_organization(client, as_role):
    as_role(Role.VISUALIZADOR)
    assert client.get("/users").status_code == 403
    assert client.patch("/organization", json={"name": "x"}).status_code == 403


def test_super_admin_reaches_admin_area_every_org_role_is_blocked_from(client, as_role):
    for role in (Role.OWNER, Role.FINANCEIRO, Role.OPERACIONAL, Role.VISUALIZADOR):
        as_role(role)
        assert client.get("/admin/metrics").status_code == 403
