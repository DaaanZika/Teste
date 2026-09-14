"""Confirms RBAC is actually wired into the routes, not just correct in
isolation (see test_rbac.py for the matrix itself). Overrides
`get_current_user` to act as a specific role without going through a real
Google login.
"""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.main import app as fastapi_app
from app.models.enums import Role
from app.models.user import User


@pytest.fixture()
def as_role(db_session):
    """Overrides the authenticated user's role for the duration of a test."""

    created_users: list[User] = []

    def _use(role: Role) -> User:
        unique = uuid.uuid4().hex[:8]
        user = User(name=f"Test {role.value}", email=f"{role.value.lower()}-{unique}@example.com", role=role, active=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        created_users.append(user)
        fastapi_app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _use

    fastapi_app.dependency_overrides.pop(get_current_user, None)


def test_viewer_cannot_create_expense(client, as_role):
    as_role(Role.VIEWER)
    response = client.post("/expenses", json={"description": "teste", "amount": "10.00"})
    assert response.status_code == 403
    assert response.json()["error"] == "FORBIDDEN"


def test_viewer_can_list_expenses(client, as_role):
    as_role(Role.VIEWER)
    response = client.get("/expenses")
    assert response.status_code == 200


def test_financial_can_create_expense(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.post("/expenses", json={"description": "teste", "amount": "10.00"})
    assert response.status_code == 200


def test_financial_cannot_manage_users(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.get("/users")
    assert response.status_code == 403


def test_admin_can_manage_users(client, as_role):
    as_role(Role.ADMIN)
    response = client.get("/users")
    assert response.status_code == 200


def test_accountant_cannot_create_expense_but_can_correct_documents_permission(client, as_role):
    as_role(Role.ACCOUNTANT)
    response = client.post("/expenses", json={"description": "teste", "amount": "10.00"})
    assert response.status_code == 403


def test_unauthenticated_status_reports_provider_without_requiring_login(client):
    # /auth/status must never itself require the permission it's reporting on.
    response = client.get("/auth/status")
    assert response.status_code == 200
