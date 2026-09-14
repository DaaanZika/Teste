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
from app.core.rbac import Permission, role_has_permission
from app.models.enums import Role
from app.models.user import User

LOCAL_OPERATOR_EMAIL = "local@campanhas.local"


def _get_or_create_local_user(db: Session) -> User:
    user = db.query(User).filter(User.email == LOCAL_OPERATOR_EMAIL).one_or_none()
    if user is None:
        user = User(name="Operador Local", email=LOCAL_OPERATOR_EMAIL, role=Role.ADMIN, active=True)
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
    """FastAPI dependency factory: `Depends(require_permission(Permission.MANAGE_FINANCE))`."""

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if not role_has_permission(user.role, permission):
            raise ForbiddenError(
                f"Seu papel ({user.role.value}) não tem permissão para esta ação "
                f"(requer {permission.value})."
            )
        return user

    return _dependency
