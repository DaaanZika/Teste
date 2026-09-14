from __future__ import annotations

from sqlalchemy import Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ProcessingJobStatus, ProcessingJobType


class ProcessingJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks a unit of asynchronous work (currently OCR/document processing).

    V1 runs jobs synchronously in-process (see services.documents.document_service),
    but persisting them as rows now means the queue can move to Redis/RQ or
    Celery later without changing this table's shape or the API responses
    that reference `job_id`.
    """

    __tablename__ = "processing_jobs"

    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    type: Mapped[ProcessingJobType] = mapped_column(
        SAEnum(ProcessingJobType, native_enum=False, length=30), nullable=False
    )
    status: Mapped[ProcessingJobStatus] = mapped_column(
        SAEnum(ProcessingJobStatus, native_enum=False, length=20),
        default=ProcessingJobStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
