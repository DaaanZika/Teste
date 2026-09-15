"""app/api/routes/users.py — PATCH /users/{id} is ADMIN-only (RBAC, covered
in test_permission_enforcement.py) and must never leave the system without
an active ADMIN, even by accident. Every change is audited."""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.main import app as fastapi_app
from app.models.enums import AuditAction, Role
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture()
def as_admin(db_session):
    unique = uuid.uuid4().hex[:8]
    org = Organization(name=f"Org {unique}", slug=f"org-{unique}")
    db_session.add(org)
    db_session.flush()
    actor = User(
        name="Acting Admin",
        email=f"acting-admin-{unique}@example.com",
        role=Role.ADMIN,
        active=True,
        organization_id=org.id,
    )
    db_session.add(actor)
    db_session.commit()
    db_session.refresh(actor)
    fastapi_app.dependency_overrides[get_current_user] = lambda: actor
    yield actor
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def _make_user(db_session, role: Role, *, active: bool = True, organization_id: str | None = None) -> User:
    unique = uuid.uuid4().hex[:8]
    if organization_id is None:
        org = Organization(name=f"Org {unique}", slug=f"org-{unique}")
        db_session.add(org)
        db_session.flush()
        organization_id = org.id
    user = User(
        name=f"User {unique}",
        email=f"user-{unique}@example.com",
        role=role,
        active=active,
        organization_id=organization_id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_admin_can_change_a_viewer_role(client, as_admin, db_session):
    target = _make_user(db_session, Role.VIEWER, organization_id=as_admin.organization_id)

    response = client.patch(f"/users/{target.id}", json={"role": "FINANCIAL"})

    assert response.status_code == 200
    assert response.json()["role"] == "FINANCIAL"


def test_update_records_audit_log(client, as_admin, db_session):
    target = _make_user(db_session, Role.VIEWER, organization_id=as_admin.organization_id)

    client.patch(f"/users/{target.id}", json={"role": "FINANCIAL"})

    response = client.get("/audit", params={"entity": "user", "entity_id": target.id})
    assert response.status_code == 200
    entries = response.json()
    assert any(e["action"] == AuditAction.UPDATE.value for e in entries)


def _deactivate_every_other_admin(db_session, keep: User) -> None:
    """The DB in this test suite isn't reset between tests (see
    conftest.py) — other test files create their own ADMIN users that
    persist. To actually exercise "the last active admin" here, every
    other active admin must be neutralized first."""
    from sqlalchemy import select

    others = db_session.execute(
        select(User).where(User.role == Role.ADMIN, User.active.is_(True), User.id != keep.id)
    ).scalars()
    for other in others:
        other.active = False
    db_session.commit()


def test_cannot_demote_the_last_active_admin(client, as_admin, db_session):
    _deactivate_every_other_admin(db_session, keep=as_admin)

    response = client.patch(f"/users/{as_admin.id}", json={"role": "VIEWER"})

    assert response.status_code == 409
    assert response.json()["error"] == "CONFLICT"


def test_cannot_deactivate_the_last_active_admin(client, as_admin, db_session):
    _deactivate_every_other_admin(db_session, keep=as_admin)

    response = client.patch(f"/users/{as_admin.id}", json={"active": False})

    assert response.status_code == 409


def test_can_demote_an_admin_when_another_active_admin_exists(client, as_admin, db_session):
    other_admin = _make_user(db_session, Role.ADMIN, organization_id=as_admin.organization_id)

    response = client.patch(f"/users/{as_admin.id}", json={"role": "VIEWER"})

    assert response.status_code == 200
    assert response.json()["role"] == "VIEWER"
    assert other_admin.role == Role.ADMIN  # unaffected


def test_can_demote_a_non_admin_freely(client, as_admin, db_session):
    target = _make_user(db_session, Role.FINANCIAL, organization_id=as_admin.organization_id)

    response = client.patch(f"/users/{target.id}", json={"active": False})

    assert response.status_code == 200
    assert response.json()["active"] is False


def test_update_unknown_user_returns_404(client, as_admin):
    response = client.patch("/users/does-not-exist", json={"role": "VIEWER"})
    assert response.status_code == 404
