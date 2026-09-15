"""Authentication (who are you) and authorization (what can you do) — kept
deliberately separate (PROMPT 3 §6).

Authentication: `get_current_user` resolves the real, active `User` behind
the request. In `auth_provider="local"` (V1's default) there is still no
login flow — a single local operator row is auto-created and always
resolves, exactly like V1's behavior, except it is now a real `User` row
with role=ADMIN instead of a bare string constant. In
`auth_provider="google"`, it reads the signed session cookie
(app.services.auth.session_service) and requires a valid, non-revoked,
non-expired session — no session, no request.

Authorization: `require_permission(...)` is a dependency *factory* routes
use to declare which RBAC permission (app.core.rbac) they require. It
never guesses; a role either has the permission in the matrix or it
doesn't.
"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.rbac import Permission, user_has_permission
from app.models.enums import Role
from app.models.organization import Organization
from app.models.user import User

LOCAL_OPERATOR_EMAIL = "local@campanhas.local"
LOCAL_ORGANIZATION_SLUG = "local"


def _get_or_create_local_organization(db: Session) -> Organization:
    """AUTH_PROVIDER=local (V1's zero-config default, still fully
    supported — PROMPT 4 rule: local use must keep working 100% without
    any multi-tenant setup) needs exactly one implicit tenant so the
    single auto-created operator can create campaigns like it always
    could. Real multi-org setups use AUTH_PROVIDER=google/password."""
    org = db.query(Organization).filter(Organization.slug == LOCAL_ORGANIZATION_SLUG).one_or_none()
    if org is None:
        org = Organization(name="Organização Local", slug=LOCAL_ORGANIZATION_SLUG)
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def _get_or_create_local_user(db: Session) -> User:
    user = db.query(User).filter(User.email == LOCAL_OPERATOR_EMAIL).one_or_none()
    if user is None:
        org = _get_or_create_local_organization(db)
        user = User(
            name="Operador Local",
            email=LOCAL_OPERATOR_EMAIL,
            role=Role.ADMIN,
            active=True,
            organization_id=org.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()

    if settings.auth_provider == "local":
        return _get_or_create_local_user(db)

    from app.services.auth.session_service import get_user_from_cookie  # avoid import cycle at module load

    user = get_user_from_cookie(db, request)
    if user is None:
        raise UnauthorizedError("Autenticação necessária. Faça login com sua conta Google.")
    if not user.active:
        raise UnauthorizedError("Esta conta foi desativada por um administrador.")
    return user


def get_current_user_id(user: User = Depends(get_current_user)) -> str:
    """Kept for existing routes that only need the id (e.g. for audit logs)."""
    return user.id


def require_permission(permission: Permission):
    """FastAPI dependency factory: `Depends(require_permission(Permission.MANAGE_FINANCE))`.

    SUPER_ADMIN always passes (platform-level role, not permission-scoped);
    CUSTOM is checked against per-user grants — see
    app.core.rbac.user_has_permission for both."""

    def _dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not user_has_permission(db, user, permission):
            raise ForbiddenError(
                f"Seu papel ({user.role.value}) não tem permissão para esta ação "
                f"(requer {permission.value})."
            )
        return user

    return _dependency


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """Gate for the platform admin area (`/admin`). Deliberately a plain
    role check, never a permission check — PROMPT 4's explicit rule is that
    SUPER_ADMIN is structurally separate from organization roles, so no
    combination of granted permissions could ever accidentally unlock this
    (see app/core/rbac.py module docstring)."""
    if user.role != Role.SUPER_ADMIN:
        raise ForbiddenError("Esta área é exclusiva da administração da plataforma.")
    return user
