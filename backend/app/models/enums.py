"""Shared enumerations used across models and schemas."""
from __future__ import annotations

import enum


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FAILED = "FAILED"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"


class OCRConfidence(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class ExpenseStatus(str, enum.Enum):
    COMPLETE = "COMPLETE"
    PENDING_INFORMATION = "PENDING_INFORMATION"


class DocumentLinkStatus(str, enum.Enum):
    """Status of the link between a financial record and its supporting document."""

    ATTACHED = "ATTACHED"
    PENDING = "PENDING"
    NOT_REQUIRED = "NOT_REQUIRED"


class RevenueStatus(str, enum.Enum):
    COMPLETE = "COMPLETE"
    PENDING_INFORMATION = "PENDING_INFORMATION"


class TransactionType(str, enum.Enum):
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class AlertType(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class ProcessingJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingJobType(str, enum.Enum):
    OCR = "OCR"
    DOCUMENT_PROCESSING = "DOCUMENT_PROCESSING"


class RuleSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    STATUS_CHANGE = "STATUS_CHANGE"
    MANUAL_CORRECTION = "MANUAL_CORRECTION"
    LINK_DOCUMENT = "LINK_DOCUMENT"
