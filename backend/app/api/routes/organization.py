"""Own-organization self-service (PROMPT 4 FASE 7) — the org "Administração"
tab's "Organização" section. Strictly the caller's own organization; never
takes an organization_id from the client (see require_organization_scope).
Platform-wide organization management (creating orgs, changing plan/
limits, activate/suspend/block) is SUPER_ADMIN-only — see admin.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope
from app.models.user import User
from app.schemas.organization import OrganizationRead, OrganizationSelfUpdate, OrganizationUsage
from app.services.admin import organization_service

router = APIRouter(prefix="/organization", tags=["organization"])


@router.get("", response_model=OrganizationRead, dependencies=[Depends(require_permission(Permission.ORGANIZATION_VIEW))])
def get_own_organization(
    db: Session = Depends(get_db), organization_id: str = Depends(require_organization_scope)
) -> OrganizationRead:
    return OrganizationRead.model_validate(organization_service.get_organization(db, organization_id))


@router.get(
    "/usage", response_model=OrganizationUsage, dependencies=[Depends(require_permission(Permission.ORGANIZATION_VIEW))]
)
def get_own_organization_usage(
    db: Session = Depends(get_db), organization_id: str = Depends(require_organization_scope)
) -> OrganizationUsage:
    return OrganizationUsage(**organization_service.get_organization_usage(db, organization_id))


@router.patch(
    "", response_model=OrganizationRead, dependencies=[Depends(require_permission(Permission.ORGANIZATION_EDIT))]
)
def update_own_organization(
    payload: OrganizationSelfUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ORGANIZATION_EDIT)),
    organization_id: str = Depends(require_organization_scope),
) -> OrganizationRead:
    """Only `name` is editable here — plan/storage limits are SUPER_ADMIN
    territory (PATCH /admin/organizations/{id})."""
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    org = organization_service.update_organization(db, organization_id, updates, actor_id=actor.id)
    return OrganizationRead.model_validate(org)
