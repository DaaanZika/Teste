"""Multi-tenant scoping (PROMPT 4).

The organization boundary is derived from the authenticated session only —
never from a client-supplied `organization_id` query param, path param, or
request body field. Every route that reads/writes organization-scoped data
depends on `require_organization_scope`, not on trusting the caller.
"""
from __future__ import annotations

from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.core.security import get_current_user
from app.models.enums import Role
from app.models.user import User


def require_organization_scope(user: User = Depends(get_current_user)) -> str:
    """Returns the caller's own organization_id. A SUPER_ADMIN has none by
    design (a platform-level account, not scoped to any single tenant) —
    they use the dedicated `/admin` routes (or support access) to reach a
    specific organization's data, never these regular endpoints."""
    if user.organization_id is None:
        raise ForbiddenError(
            "Esta conta não pertence a uma organização — use a área de administração da "
            "plataforma para acessar dados de uma organização específica."
            if user.role == Role.SUPER_ADMIN
            else "Esta conta não está associada a nenhuma organização."
        )
    return user.organization_id
