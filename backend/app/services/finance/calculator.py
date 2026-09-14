"""The single source of financial truth for the whole backend.

Every total, balance and percentage the API returns is computed here, from
`Decimal` values read out of the `transactions` ledger — never `float`,
per PROMPT 1 section 17. No frontend and no other service is expected to
re-derive a balance; they call these functions (through /finance and
/reports routes) and use the result as-is.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.transaction import Transaction

TWO_PLACES = Decimal("0.01")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _transactions(
    db: Session,
    *,
    campaign_id: str | None = None,
    type_: TransactionType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Transaction]:
    stmt = select(Transaction)
    if campaign_id is not None:
        stmt = stmt.where(Transaction.campaign_id == campaign_id)
    if type_ is not None:
        stmt = stmt.where(Transaction.type == type_)
    if start_date is not None:
        stmt = stmt.where(Transaction.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Transaction.date <= end_date)
    return list(db.execute(stmt).scalars())


def total_revenues(db: Session, *, campaign_id: str | None = None) -> Decimal:
    rows = _transactions(db, campaign_id=campaign_id, type_=TransactionType.REVENUE)
    return _quantize(sum((r.amount for r in rows), Decimal("0")))


def total_expenses(db: Session, *, campaign_id: str | None = None) -> Decimal:
    rows = _transactions(db, campaign_id=campaign_id, type_=TransactionType.EXPENSE)
    return _quantize(sum((r.amount for r in rows), Decimal("0")))


def balance(db: Session, *, campaign_id: str | None = None) -> Decimal:
    return _quantize(total_revenues(db, campaign_id=campaign_id) - total_expenses(db, campaign_id=campaign_id))


def totals_by_period(
    db: Session, *, campaign_id: str | None = None, granularity: str = "month"
) -> list[dict]:
    """Aggregates revenues/expenses/balance per period (`month` -> YYYY-MM, `year` -> YYYY).

    Rows with no date are excluded — they cannot be attributed to a period.
    """
    if granularity not in ("month", "year"):
        raise ValueError("granularity must be 'month' or 'year'")

    rows = _transactions(db, campaign_id=campaign_id)
    totals: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        if row.date is None:
            continue
        key = row.date.strftime("%Y-%m") if granularity == "month" else row.date.strftime("%Y")
        bucket = totals.setdefault(key, {"revenues": Decimal("0"), "expenses": Decimal("0")})
        if row.type == TransactionType.REVENUE:
            bucket["revenues"] += row.amount
        else:
            bucket["expenses"] += row.amount

    return [
        {
            "period": period,
            "total_revenues": _quantize(values["revenues"]),
            "total_expenses": _quantize(values["expenses"]),
            "balance": _quantize(values["revenues"] - values["expenses"]),
        }
        for period, values in sorted(totals.items())
    ]


def _percentage_breakdown(rows: list[Transaction], key_fn) -> list[dict]:
    totals: dict[str, Decimal] = {}
    for row in rows:
        key = key_fn(row)
        if not key:
            continue
        totals[key] = totals.get(key, Decimal("0")) + row.amount

    grand_total = sum(totals.values(), Decimal("0"))
    result = []
    for key, value in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
        percentage = _quantize((value / grand_total) * Decimal("100")) if grand_total > 0 else Decimal("0.00")
        result.append({"key": key, "total": _quantize(value), "percentage_of_total": percentage})
    return result


def totals_by_category(
    db: Session, *, campaign_id: str | None = None, type_: TransactionType = TransactionType.EXPENSE
) -> list[dict]:
    rows = _transactions(db, campaign_id=campaign_id, type_=type_)
    breakdown = _percentage_breakdown(rows, lambda r: r.category)
    return [{"category": item["key"], **{k: v for k, v in item.items() if k != "key"}} for item in breakdown]


def totals_by_supplier(db: Session, *, campaign_id: str | None = None) -> list[dict]:
    rows = _transactions(db, campaign_id=campaign_id, type_=TransactionType.EXPENSE)
    breakdown = _percentage_breakdown(rows, lambda r: r.counterparty)
    return [{"supplier_name": item["key"], **{k: v for k, v in item.items() if k != "key"}} for item in breakdown]
