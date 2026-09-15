"""app/services/admin/bootstrap.py — the only path that creates the first
SUPER_ADMIN. No hardcoded credential anywhere: this reads from the
environment and is idempotent (never creates a second SUPER_ADMIN, never
resets an existing one's password)."""
from __future__ import annotations

import uuid

import pytest

from app.core.password import verify_password
from app.models.enums import Role
from app.models.user import User
from app.services.admin import bootstrap


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SUPER_ADMIN_BOOTSTRAP_EMAIL", raising=False)
    monkeypatch.delenv("SUPER_ADMIN_BOOTSTRAP_PASSWORD", raising=False)


@pytest.fixture(autouse=True)
def _no_pre_existing_super_admin(db_session):
    """The DB in this test suite isn't reset between tests (see
    conftest.py) — other test files (e.g. test_admin_routes.py,
    test_multi_tenant_isolation.py) create their own SUPER_ADMIN users
    that persist. bootstrap_super_admin()'s idempotency check ("does a
    SUPER_ADMIN already exist?") needs a clean slate to actually test
    the "none exists yet" path."""
    from sqlalchemy import delete

    db_session.execute(delete(User).where(User.role == Role.SUPER_ADMIN))
    db_session.commit()
    yield


def test_bootstrap_does_nothing_without_env_vars(db_session):
    assert bootstrap.bootstrap_super_admin() is None


def test_bootstrap_creates_super_admin_from_env(monkeypatch, db_session):
    unique = uuid.uuid4().hex[:8]
    email = f"root-{unique}@example.com"
    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_EMAIL", email)
    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_PASSWORD", "SenhaMuitoForte123!")

    user = bootstrap.bootstrap_super_admin()

    assert user is not None
    assert user.role == Role.SUPER_ADMIN
    assert user.organization_id is None
    assert user.email == email
    assert verify_password("SenhaMuitoForte123!", user.password_hash)


def test_bootstrap_is_idempotent_once_a_super_admin_exists(monkeypatch, db_session):
    unique = uuid.uuid4().hex[:8]
    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_EMAIL", f"first-{unique}@example.com")
    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_PASSWORD", "SenhaMuitoForte123!")
    first = bootstrap.bootstrap_super_admin()
    assert first is not None

    # Even with a different email/password in the env, a second call is a no-op.
    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_EMAIL", f"second-{unique}@example.com")
    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_PASSWORD", "OutraSenha456!")
    second = bootstrap.bootstrap_super_admin()
    assert second is None

    from sqlalchemy import func, select

    count = db_session.execute(
        select(func.count()).select_from(User).where(User.role == Role.SUPER_ADMIN)
    ).scalar_one()
    assert count == 1


def test_bootstrap_rejects_email_already_used_by_another_role(monkeypatch, db_session):
    unique = uuid.uuid4().hex[:8]
    existing_email = f"taken-{unique}@example.com"
    other = User(name="Alguém", email=existing_email, role=Role.VIEWER, active=True)
    db_session.add(other)
    db_session.commit()

    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_EMAIL", existing_email)
    monkeypatch.setenv("SUPER_ADMIN_BOOTSTRAP_PASSWORD", "SenhaMuitoForte123!")

    with pytest.raises(ValueError):
        bootstrap.bootstrap_super_admin()
