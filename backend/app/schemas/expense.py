from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentLinkStatus, ExpenseStatus


class ExpenseCreate(BaseModel):
    campaign_id: str | None = None
    date: date_type | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = None
    category: str | None = None
    supplier_name: str | None = None
    supplier_document: str | None = None
    payment_method: str | None = None
    document_id: str | None = None


class ExpenseQuickCreate(BaseModel):
    """Free-text quick entry, e.g. 'R$ 850 gráfica ABC' or 'Gasolina 230 reais ontem'."""

    text: str
    campaign_id: str | None = None


class ExpenseUpdate(BaseModel):
    date: date_type | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = None
    category: str | None = None
    supplier_name: str | None = None
    supplier_document: str | None = None
    payment_method: str | None = None
    document_id: str | None = None


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str | None
    date: date_type | None
    amount: Decimal | None
    description: str | None
    category: str | None
    supplier_name: str | None
    supplier_document: str | None
    payment_method: str | None
    document_id: str | None
    document_status: DocumentLinkStatus
    status: ExpenseStatus
    missing_fields: str | None
    source_text: str | None
    created_at: datetime
    updated_at: datetime
