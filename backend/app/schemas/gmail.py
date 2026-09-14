from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import GmailSuggestionStatus
from app.schemas.document import DocumentUploadResponse


class GmailSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    gmail_message_id: str
    sender: str | None
    subject: str | None
    received_at: datetime | None
    attachment_filename: str
    mime_type: str
    campaign_id: str | None
    document_id: str | None
    status: GmailSuggestionStatus
    rejected_reason: str | None
    created_at: datetime


class GmailScanRequest(BaseModel):
    campaign_id: str | None = None
    max_results: int = 20


class GmailScanResponse(BaseModel):
    new_suggestions: list[GmailSuggestionRead]


class GmailRejectRequest(BaseModel):
    reason: str | None = None
