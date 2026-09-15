from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db, require_permission
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope, resolve_campaign_id
from app.models.enums import ExpenseStatus
from app.schemas.expense import ExpenseCreate, ExpenseQuickCreate, ExpenseRead, ExpenseUpdate
from app.services.finance import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])

_can_manage = Depends(require_permission(Permission.MANAGE_FINANCE))
_can_view = Depends(require_permission(Permission.VIEW_FINANCE))


@router.post("", response_model=ExpenseRead, dependencies=[_can_manage])
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(require_organization_scope),
) -> ExpenseRead:
    data = payload.model_dump(exclude_unset=True)
    data["campaign_id"] = resolve_campaign_id(db, organization_id, data.get("campaign_id"))
    expense = expense_service.create_expense(db, data, user_id=user_id)
    return ExpenseRead.model_validate(expense)


@router.post("/quick", response_model=ExpenseRead, dependencies=[_can_manage])
def create_quick_expense(
    payload: ExpenseQuickCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(require_organization_scope),
) -> ExpenseRead:
    campaign_id = resolve_campaign_id(db, organization_id, payload.campaign_id)
    expense = expense_service.create_quick_expense(db, text=payload.text, campaign_id=campaign_id, user_id=user_id)
    return ExpenseRead.model_validate(expense)


@router.get("", response_model=list[ExpenseRead], dependencies=[_can_view])
def list_expenses(
    campaign_id: str | None = None,
    status: ExpenseStatus | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> list[ExpenseRead]:
    expenses = expense_service.list_expenses(db, organization_id=organization_id, campaign_id=campaign_id, status=status)
    return [ExpenseRead.model_validate(e) for e in expenses]


@router.get("/{expense_id}", response_model=ExpenseRead, dependencies=[_can_view])
def get_expense(
    expense_id: str, db: Session = Depends(get_db), organization_id: str = Depends(require_organization_scope)
) -> ExpenseRead:
    expense = expense_service.get_expense_in_org(db, expense_id, organization_id=organization_id)
    return ExpenseRead.model_validate(expense)


@router.put("/{expense_id}", response_model=ExpenseRead, dependencies=[_can_manage])
def update_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    organization_id: str = Depends(require_organization_scope),
) -> ExpenseRead:
    expense = expense_service.update_expense(
        db, expense_id, payload.model_dump(exclude_unset=True), user_id=user_id, organization_id=organization_id
    )
    return ExpenseRead.model_validate(expense)
