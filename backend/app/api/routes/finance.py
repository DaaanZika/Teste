from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import DocumentLinkStatus
from app.models.expense import Expense
from app.schemas.finance import FinanceBalance, FinanceSummary
from app.services.finance import calculator
from app.services.reports import report_service

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary", response_model=FinanceSummary)
def finance_summary(campaign_id: str | None = None, db: Session = Depends(get_db)) -> FinanceSummary:
    summary = report_service.summary_report(db, campaign_id=campaign_id)

    without_document_stmt = select(Expense).where(Expense.document_status != DocumentLinkStatus.ATTACHED)
    if campaign_id is not None:
        without_document_stmt = without_document_stmt.where(Expense.campaign_id == campaign_id)
    expenses_without_document = len(list(db.execute(without_document_stmt).scalars()))

    return FinanceSummary(
        total_revenues=summary["total_revenues"],
        total_expenses=summary["total_expenses"],
        balance=summary["balance"],
        pending_information_expenses=summary["pending_information_expenses"],
        pending_information_revenues=summary["pending_information_revenues"],
        expenses_without_document=expenses_without_document,
    )


@router.get("/balance", response_model=FinanceBalance)
def finance_balance(campaign_id: str | None = None, db: Session = Depends(get_db)) -> FinanceBalance:
    return FinanceBalance(
        balance=calculator.balance(db, campaign_id=campaign_id),
        total_revenues=calculator.total_revenues(db, campaign_id=campaign_id),
        total_expenses=calculator.total_expenses(db, campaign_id=campaign_id),
    )


@router.get("/totals/period")
def finance_totals_by_period(
    campaign_id: str | None = None, granularity: str = "month", db: Session = Depends(get_db)
) -> list[dict]:
    return calculator.totals_by_period(db, campaign_id=campaign_id, granularity=granularity)


@router.get("/totals/category")
def finance_totals_by_category(campaign_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return calculator.totals_by_category(db, campaign_id=campaign_id)


@router.get("/totals/supplier")
def finance_totals_by_supplier(campaign_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return calculator.totals_by_supplier(db, campaign_id=campaign_id)
