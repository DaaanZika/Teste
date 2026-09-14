"""Keeps the central `transactions` ledger in sync with expenses/revenues.

Per PROMPT 1 section 16, every revenue and expense feeds the financial
calculations through one central layer, and the frontend never computes
the balance itself. `finance_calculator` reads only from `transactions`;
this module is the only place that writes to it, called by the
expense/revenue services right after they create or update a record.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.revenue import Revenue
from app.models.transaction import Transaction
from app.models.enums import TransactionType


def sync_transaction_for_expense(db: Session, expense: Expense) -> None:
    stmt = select(Transaction).where(Transaction.expense_id == expense.id)
    existing = db.execute(stmt).scalar_one_or_none()

    if expense.amount is None:
        if existing is not None:
            db.delete(existing)
        return

    if existing is None:
        existing = Transaction(expense_id=expense.id, type=TransactionType.EXPENSE)
        db.add(existing)

    existing.campaign_id = expense.campaign_id
    existing.amount = expense.amount
    existing.date = expense.date
    existing.category = expense.category
    existing.counterparty = expense.supplier_name


def sync_transaction_for_revenue(db: Session, revenue: Revenue) -> None:
    stmt = select(Transaction).where(Transaction.revenue_id == revenue.id)
    existing = db.execute(stmt).scalar_one_or_none()

    if revenue.amount is None:
        if existing is not None:
            db.delete(existing)
        return

    if existing is None:
        existing = Transaction(revenue_id=revenue.id, type=TransactionType.REVENUE)
        db.add(existing)

    existing.campaign_id = revenue.campaign_id
    existing.amount = revenue.amount
    existing.date = revenue.date
    existing.category = revenue.source_type
    existing.counterparty = revenue.donor_name
