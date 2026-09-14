from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.enums import ExpenseStatus
from app.schemas.expense import ExpenseCreate, ExpenseQuickCreate, ExpenseRead, ExpenseUpdate
from app.services.finance import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseRead)
def create_expense(
    payload: ExpenseCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> ExpenseRead:
    expense = expense_service.create_expense(db, payload.model_dump(exclude_unset=True), user_id=user_id)
    return ExpenseRead.model_validate(expense)


@router.post("/quick", response_model=ExpenseRead)
def create_quick_expense(
    payload: ExpenseQuickCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> ExpenseRead:
    expense = expense_service.create_quick_expense(
        db, text=payload.text, campaign_id=payload.campaign_id, user_id=user_id
    )
    return ExpenseRead.model_validate(expense)


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    campaign_id: str | None = None, status: ExpenseStatus | None = None, db: Session = Depends(get_db)
) -> list[ExpenseRead]:
    expenses = expense_service.list_expenses(db, campaign_id=campaign_id, status=status)
    return [ExpenseRead.model_validate(e) for e in expenses]


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: str, db: Session = Depends(get_db)) -> ExpenseRead:
    expense = expense_service.get_expense(db, expense_id)
    return ExpenseRead.model_validate(expense)


@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ExpenseRead:
    expense = expense_service.update_expense(
        db, expense_id, payload.model_dump(exclude_unset=True), user_id=user_id
    )
    return ExpenseRead.model_validate(expense)
