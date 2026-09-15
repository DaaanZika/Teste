from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db, require_permission
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope, resolve_campaign_id
from app.models.enums import RevenueStatus
from app.schemas.revenue import RevenueCreate, RevenueRead
from app.services.finance import revenue_service

router = APIRouter(prefix="/revenues", tags=["revenues"])

_can_manage = Depends(require_permission(Permission.MANAGE_FINANCE))
_can_view = Depends(require_permission(Permission.VIEW_FINANCE))


@router.post("", response_model=RevenueRead, dependencies=[_can_manage])
def create_revenue(
    payload: RevenueCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(require_organization_scope),
) -> RevenueRead:
    data = payload.model_dump(exclude_unset=True)
    data["campaign_id"] = resolve_campaign_id(db, organization_id, data.get("campaign_id"))
    revenue = revenue_service.create_revenue(db, data, user_id=user_id)
    return RevenueRead.model_validate(revenue)


@router.get("", response_model=list[RevenueRead], dependencies=[_can_view])
def list_revenues(
    campaign_id: str | None = None,
    status: RevenueStatus | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> list[RevenueRead]:
    revenues = revenue_service.list_revenues(db, organization_id=organization_id, campaign_id=campaign_id, status=status)
    return [RevenueRead.model_validate(r) for r in revenues]


@router.get("/{revenue_id}", response_model=RevenueRead, dependencies=[_can_view])
def get_revenue(
    revenue_id: str, db: Session = Depends(get_db), organization_id: str = Depends(require_organization_scope)
) -> RevenueRead:
    revenue = revenue_service.get_revenue_in_org(db, revenue_id, organization_id=organization_id)
    return RevenueRead.model_validate(revenue)
