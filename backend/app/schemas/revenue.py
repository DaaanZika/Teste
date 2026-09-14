from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentLinkStatus, RevenueStatus


class RevenueCreate(BaseModel):
    campaign_id: str | None = None
    date: date_type | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    source_type: str | None = None
    donor_name: str | None = None
    donor_document: str | None = None
    description: str | None = None
    payment_method: str | None = None
    document_id: str | None = None


class RevenueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str | None
    date: date_type | None
    amount: Decimal | None
    source_type: str | None
    donor_name: str | None
    donor_document: str | None
    description: str | None
    payment_method: str | None
    document_id: str | None
    document_status: DocumentLinkStatus
    status: RevenueStatus
    missing_fields: str | None
    created_at: datetime
    updated_at: datetime
