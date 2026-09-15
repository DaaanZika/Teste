from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope, resolve_campaign_scope
from app.models.enums import TransactionType
from app.schemas.finance import FinanceBalance, FinanceSummary
from app.services.finance import calculator
from app.services.reports import report_service

router = APIRouter(prefix="/finance", tags=["finance"], dependencies=[Depends(require_permission(Permission.VIEW_FINANCE))])


@router.get("/summary", response_model=FinanceSummary)
def finance_summary(
    campaign_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> FinanceSummary:
    """`start_date`/`end_date` scope the totals/balance to a period (used by the
    Financeiro screen's period filter); pending-information and missing-document
    counts stay campaign-wide since they flag data-quality issues, not a period.
    No `campaign_id` means every campaign in the caller's own organization —
    never every campaign in the database."""
    resolved_campaign_id, campaign_ids = resolve_campaign_scope(db, organization_id, campaign_id)
    # expenses_without_document/pending counts are always campaign(s)-wide data-quality
    # flags, not scoped to a period — reused as-is from summary_report() below
    # regardless of whether a date range narrows the totals.
    summary = report_service.summary_report(db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids)

    if start_date is not None or end_date is not None:
        total_revenues = calculator.total_revenues(
            db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids, start_date=start_date, end_date=end_date
        )
        total_expenses = calculator.total_expenses(
            db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids, start_date=start_date, end_date=end_date
        )
        balance_value = total_revenues - total_expenses
    else:
        total_revenues = summary["total_revenues"]
        total_expenses = summary["total_expenses"]
        balance_value = summary["balance"]

    return FinanceSummary(
        total_revenues=total_revenues,
        total_expenses=total_expenses,
        balance=balance_value,
        pending_information_expenses=summary["pending_information_expenses"],
        pending_information_revenues=summary["pending_information_revenues"],
        expenses_without_document=summary["expenses_without_document"],
    )


@router.get("/balance", response_model=FinanceBalance)
def finance_balance(
    campaign_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> FinanceBalance:
    resolved_campaign_id, campaign_ids = resolve_campaign_scope(db, organization_id, campaign_id)
    return FinanceBalance(
        balance=calculator.balance(
            db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids, start_date=start_date, end_date=end_date
        ),
        total_revenues=calculator.total_revenues(
            db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids, start_date=start_date, end_date=end_date
        ),
        total_expenses=calculator.total_expenses(
            db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids, start_date=start_date, end_date=end_date
        ),
    )


@router.get("/totals/period")
def finance_totals_by_period(
    campaign_id: str | None = None,
    granularity: str = "day",
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> list[dict]:
    """Powers the dashboard chart's period filters (hoje/7 dias/30 dias/personalizado):
    the caller picks `start_date`/`end_date` and `granularity`; this backend does the
    aggregation so the frontend never sums money itself."""
    resolved_campaign_id, campaign_ids = resolve_campaign_scope(db, organization_id, campaign_id)
    return calculator.totals_by_period(
        db,
        campaign_id=resolved_campaign_id,
        campaign_ids=campaign_ids,
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/totals/category")
def finance_totals_by_category(
    campaign_id: str | None = None,
    type: TransactionType = TransactionType.EXPENSE,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> list[dict]:
    """`type` lets the Financeiro screen break down either expenses or
    revenues by category — without it this only ever reported expenses."""
    resolved_campaign_id, campaign_ids = resolve_campaign_scope(db, organization_id, campaign_id)
    return calculator.totals_by_category(
        db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids, type_=type
    )


@router.get("/totals/supplier")
def finance_totals_by_supplier(
    campaign_id: str | None = None,
    db: Session = Depends(get_db),
    organization_id: str = Depends(require_organization_scope),
) -> list[dict]:
    resolved_campaign_id, campaign_ids = resolve_campaign_scope(db, organization_id, campaign_id)
    return calculator.totals_by_supplier(db, campaign_id=resolved_campaign_id, campaign_ids=campaign_ids)
