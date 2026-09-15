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

    # PROMPT 4 — multi-tenant/admin event types. Additive: every value above
    # keeps meaning exactly what it meant before (native_enum=False stores
    # the string, so old rows never need to change).
    USER_CREATED = "USER_CREATED"
    USER_DISABLED = "USER_DISABLED"
    USER_LOGIN = "USER_LOGIN"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    USER_LOGOUT = "USER_LOGOUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET = "PASSWORD_RESET"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    EXPENSE_CREATED = "EXPENSE_CREATED"
    EXPENSE_UPDATED = "EXPENSE_UPDATED"
    EXPENSE_DELETED = "EXPENSE_DELETED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_UPDATED = "DOCUMENT_UPDATED"
    ORGANIZATION_CREATED = "ORGANIZATION_CREATED"
    ORGANIZATION_UPDATED = "ORGANIZATION_UPDATED"
    ORGANIZATION_STATUS_CHANGED = "ORGANIZATION_STATUS_CHANGED"
    SUPPORT_ACCESS_STARTED = "SUPPORT_ACCESS_STARTED"
    SUPPORT_ACCESS_ENDED = "SUPPORT_ACCESS_ENDED"


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
    """RBAC roles. Permission matrix lives in app/core/rbac.py, not
    scattered across routes — a role's actual capabilities are never
    assumed at the call site.

    ADMIN/CAMPAIGN_MANAGER/FINANCIAL/ACCOUNTANT/VIEWER are the original
    (PROMPT 3 §8) roles — kept byte-identical, same permissions, so nothing
    that already relies on them changes behavior.

    SUPER_ADMIN/OWNER/FINANCEIRO/OPERACIONAL/VISUALIZADOR/CUSTOM are added
    for PROMPT 4 (multi-tenant/admin). SUPER_ADMIN is a platform-level role
    that does NOT depend on the permission matrix at all (see
    app/core/rbac.py::role_has_permission) — it is not "a role with every
    permission", it is structurally outside organization-scoped RBAC.
    """

    ADMIN = "ADMIN"
    CAMPAIGN_MANAGER = "CAMPAIGN_MANAGER"
    FINANCIAL = "FINANCIAL"
    ACCOUNTANT = "ACCOUNTANT"
    VIEWER = "VIEWER"

    SUPER_ADMIN = "SUPER_ADMIN"
    OWNER = "OWNER"
    FINANCEIRO = "FINANCEIRO"
    OPERACIONAL = "OPERACIONAL"
    VISUALIZADOR = "VISUALIZADOR"
    CUSTOM = "CUSTOM"


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


class UserStatus(str, enum.Enum):
    """Informational alongside `User.active` (kept as the single boolean
    every existing query already filters on — see app/api/routes/users.py).
    BLOCKED is distinct from a plain deactivation: it also implies
    `active=False`, but records *why* for the admin UI/audit trail."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"
