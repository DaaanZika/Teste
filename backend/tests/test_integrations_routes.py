"""app/api/routes/integrations.py — /integrations/status must reflect real
state (never assume), and connect/disconnect must be ADMIN-only (RBAC
wired the same way as everything else — see test_permission_enforcement.py)."""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.main import app as fastapi_app
from app.models.enums import Role
from app.models.user import User


@pytest.fixture()
def as_role(db_session):
    created_users: list[User] = []

    def _use(role: Role) -> User:
        unique = uuid.uuid4().hex[:8]
        user = User(name=f"Test {role.value}", email=f"integrations-{role.value.lower()}-{unique}@example.com", role=role, active=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        created_users.append(user)
        fastapi_app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _use

    fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def restore_backup_setting():
    settings = get_settings()
    original = settings.backup_storage_provider
    yield settings
    settings.backup_storage_provider = original


def test_status_reports_all_sections(client, as_role, restore_backup_setting):
    restore_backup_setting.backup_storage_provider = None
    as_role(Role.VIEWER)  # VIEW_REPORTS is enough to see integration status

    response = client.get("/integrations/status")
    assert response.status_code == 200
    body = response.json()
    for key in ("google_oauth", "google_drive", "gmail", "backup", "database", "ocr"):
        assert key in body
        assert "connected" in body[key]

    assert body["google_drive"]["connected"] is False
    assert body["backup"]["connected"] is False
    assert body["database"]["connected"] is True


def test_status_reflects_configured_backup(client, as_role, restore_backup_setting):
    restore_backup_setting.backup_storage_provider = "google_drive"
    as_role(Role.VIEWER)

    response = client.get("/integrations/status")
    assert response.json()["backup"]["connected"] is True


def test_connect_requires_admin(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.get("/integrations/google-drive/connect", follow_redirects=False)
    assert response.status_code == 403


def test_disconnect_requires_admin(client, as_role):
    as_role(Role.VIEWER)
    response = client.post("/integrations/google-drive/disconnect")
    assert response.status_code == 403


def test_admin_can_disconnect_even_when_not_connected(client, as_role):
    as_role(Role.ADMIN)
    response = client.post("/integrations/google-drive/disconnect")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "disconnected"
