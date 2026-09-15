"""Platform administration — exclusive to SUPER_ADMIN (PROMPT 4 FASE 6).

Every route here depends on `require_super_admin`, a plain role check
(never a permission check — see app.core.security.require_super_admin for
why) so nothing an organization role is granted could ever unlock this.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_super_admin
from app.models.audit import AuditLog
from app.models.enums import OrganizationStatus
from app.models.organization import Organization
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationStatusUpdate,
    OrganizationUpdate,
    OrganizationUsage,
    PlatformMetrics,
)
from app.schemas.user import UserRead
from app.services.admin import organization_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_super_admin)])


@router.get("/metrics", response_model=PlatformMetrics)
def platform_metrics(db: Session = Depends(get_db)) -> PlatformMetrics:
    return PlatformMetrics(**organization_service.get_platform_metrics(db))


@router.get("/organizations", response_model=list[OrganizationRead])
def list_organizations(
    search: str | None = None, status: OrganizationStatus | None = None, db: Session = Depends(get_db)
) -> list[OrganizationRead]:
    orgs = organization_service.list_organizations(db, search=search, status=status)
    return [OrganizationRead.model_validate(o) for o in orgs]


@router.post("/organizations", response_model=OrganizationRead)
def create_organization(
    payload: OrganizationCreate, db: Session = Depends(get_db), actor: User = Depends(require_super_admin)
) -> OrganizationRead:
    org = organization_service.create_organization(
        db,
        name=payload.name,
        slug=payload.slug,
        plan=payload.plan,
        storage_limit_bytes=payload.storage_limit_bytes,
        owner_name=payload.owner_name,
        owner_email=payload.owner_email,
        owner_password=payload.owner_password,
        actor_id=actor.id,
    )
    return OrganizationRead.model_validate(org)


@router.get("/organizations/{organization_id}", response_model=OrganizationRead)
def get_organization(organization_id: str, db: Session = Depends(get_db)) -> OrganizationRead:
    return OrganizationRead.model_validate(organization_service.get_organization(db, organization_id))


@router.patch("/organizations/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
) -> OrganizationRead:
    updates = payload.model_dump(exclude_unset=True)
    org = organization_service.update_organization(db, organization_id, updates, actor_id=actor.id)
    return OrganizationRead.model_validate(org)


@router.post("/organizations/{organization_id}/status", response_model=OrganizationRead)
def set_organization_status(
    organization_id: str,
    payload: OrganizationStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_super_admin),
) -> OrganizationRead:
    """Activate/suspend/block — one endpoint, the new status says which
    (frontend renders three buttons that all call this)."""
    org = organization_service.set_organization_status(db, organization_id, payload.status, actor_id=actor.id)
    return OrganizationRead.model_validate(org)


@router.get("/organizations/{organization_id}/usage", response_model=OrganizationUsage)
def organization_usage(organization_id: str, db: Session = Depends(get_db)) -> OrganizationUsage:
    return OrganizationUsage(**organization_service.get_organization_usage(db, organization_id))


@router.get("/organizations/{organization_id}/users", response_model=list[UserRead])
def organization_users(organization_id: str, db: Session = Depends(get_db)) -> list[UserRead]:
    organization_service.get_organization(db, organization_id)  # 404s if missing
    users = db.execute(
        select(User).where(User.organization_id == organization_id).order_by(User.created_at.desc())
    ).scalars()
    return [UserRead.model_validate(u) for u in users]


@router.get("/users", response_model=list[UserRead])
def all_users(db: Session = Depends(get_db)) -> list[UserRead]:
    """Cross-org user list — SUPER_ADMIN only; every organization-scoped
    /users endpoint filters to the caller's own organization instead."""
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars()
    return [UserRead.model_validate(u) for u in users]


@router.get("/activity", response_model=list[AuditLogRead])
def recent_activity(limit: int = 100, db: Session = Depends(get_db)) -> list[AuditLogRead]:
    """Recent activity/audit across every organization — the platform-wide
    view; GET /audit (org-scoped) is what an organization's own ADMIN sees."""
    limit = max(1, min(limit, 500))
    logs = db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)).scalars()
    return [AuditLogRead.model_validate(log) for log in logs]
