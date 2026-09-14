from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db, require_permission
from app.core.rbac import Permission
from app.models.enums import RevenueStatus
from app.schemas.revenue import RevenueCreate, RevenueRead
from app.services.finance import revenue_service

router = APIRouter(prefix="/revenues", tags=["revenues"])

_can_manage = Depends(require_permission(Permission.MANAGE_FINANCE))
_can_view = Depends(require_permission(Permission.VIEW_FINANCE))


@router.post("", response_model=RevenueRead, dependencies=[_can_manage])
def create_revenue(
    payload: RevenueCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> RevenueRead:
    revenue = revenue_service.create_revenue(db, payload.model_dump(exclude_unset=True), user_id=user_id)
    return RevenueRead.model_validate(revenue)


@router.get("", response_model=list[RevenueRead], dependencies=[_can_view])
def list_revenues(
    campaign_id: str | None = None, status: RevenueStatus | None = None, db: Session = Depends(get_db)
) -> list[RevenueRead]:
    revenues = revenue_service.list_revenues(db, campaign_id=campaign_id, status=status)
    return [RevenueRead.model_validate(r) for r in revenues]


@router.get("/{revenue_id}", response_model=RevenueRead, dependencies=[_can_view])
def get_revenue(revenue_id: str, db: Session = Depends(get_db)) -> RevenueRead:
    revenue = revenue_service.get_revenue(db, revenue_id)
    return RevenueRead.model_validate(revenue)
