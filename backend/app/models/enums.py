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
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"


class BackupStatus(str, enum.Enum):
    """Status of the OPTIONAL secondary copy of a document (PROMPT 3 §12).
    The primary copy (`Document.original_path`/`storage_provider`) is never
    affected by this — a failed or not-configured backup never blocks
    upload/processing (PROMPT 3 §45)."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GmailSuggestionStatus(str, enum.Enum):
    """A Gmail attachment detected as a possible receipt/invoice is never
    imported automatically (PROMPT 3 §13/§45) — a human confirms or rejects
    each suggestion explicitly."""

    PENDING = "PENDING"
    IMPORTED = "IMPORTED"
    REJECTED = "REJECTED"


class Role(str, enum.Enum):
    """RBAC roles (PROMPT 3 §8). Permission matrix lives in app/core/rbac.py,
    not scattered across routes — a role's actual capabilities are never
    assumed at the call site."""

    ADMIN = "ADMIN"
    CAMPAIGN_MANAGER = "CAMPAIGN_MANAGER"
    FINANCIAL = "FINANCIAL"
    ACCOUNTANT = "ACCOUNTANT"
    VIEWER = "VIEWER"
