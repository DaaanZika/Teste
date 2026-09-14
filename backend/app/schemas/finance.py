from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class PeriodTotal(BaseModel):
    period: str
    total_revenues: Decimal
    total_expenses: Decimal
    balance: Decimal


class CategoryTotal(BaseModel):
    category: str
    total: Decimal
    percentage_of_total: Decimal


class SupplierTotal(BaseModel):
    supplier_name: str
    total: Decimal
    percentage_of_total: Decimal


class FinanceSummary(BaseModel):
    total_revenues: Decimal
    total_expenses: Decimal
    balance: Decimal
    pending_information_expenses: int
    pending_information_revenues: int
    expenses_without_document: int


class FinanceBalance(BaseModel):
    balance: Decimal
    total_revenues: Decimal
    total_expenses: Decimal
