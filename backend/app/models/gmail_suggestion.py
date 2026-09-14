from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import GmailSuggestionStatus


class GmailSuggestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One attachment found in a Gmail scan that looks like a receipt/invoice
    (PROMPT 3 §13). Never imported on its own — `document_id` is only set
    once a human confirms it via POST /integrations/gmail/suggestions/{id}/confirm,
    which runs the attachment through the normal upload pipeline
    (duplicate detection included) exactly like a manual upload.
    """

    __tablename__ = "gmail_suggestions"
    __table_args__ = (
        # A message with two attachments produces two suggestion rows — the
        # pair (message, attachment) is the real identity, not the message
        # alone; this also makes a re-scan idempotent (PROMPT 3 §13: never
        # suggest the same attachment twice).
        UniqueConstraint("gmail_message_id", "attachment_id", name="uq_gmail_suggestion_message_attachment"),
    )

    gmail_message_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    attachment_id: Mapped[str] = mapped_column(String(200), nullable=False)
    attachment_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)

    status: Mapped[GmailSuggestionStatus] = mapped_column(
        SAEnum(GmailSuggestionStatus, native_enum=False, length=20),
        default=GmailSuggestionStatus.PENDING,
        nullable=False,
    )
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
