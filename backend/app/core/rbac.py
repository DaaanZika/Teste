"""RBAC permission matrix.

The matrix is the single source of truth for "can this role do X" — routes
call `require_permission(Permission.X)`, never `if role == Role.ADMIN`.
That keeps the rule in one place instead of scattered `if` checks that
drift out of sync with each other.

Two permission vocabularies coexist on purpose, both enforced through this
same matrix:

- The original (PROMPT 3 §8) MANAGE_*/VIEW_* members — every existing route
  still checks these exactly as before; their meaning for the five original
  roles (ADMIN/CAMPAIGN_MANAGER/FINANCIAL/ACCOUNTANT/VIEWER) is unchanged.
- The granular dotted-name members added for PROMPT 4 (multi-tenant admin:
  `users.create`, `organization.manage`, etc.) — used by the new admin
  surface. New roles (OWNER/FINANCEIRO/OPERACIONAL/VISUALIZADOR) are given
  BOTH vocabularies so they can use existing endpoints (still gated by the
  old members) as well as the new admin endpoints (gated by the new ones).

SUPER_ADMIN is a platform-level role, not an organization role, and does
NOT depend on this matrix at all — `user_has_permission` below short-
circuits to True for it, matching PROMPT 4's explicit rule that the
platform admin never depends on "common" (organization-scoped)
permissions. Access to `/admin` itself is additionally never
permission-gated — see `app.core.security.require_super_admin`, a plain
role check, so nothing that expands a role's permission set could ever
accidentally unlock the platform admin area.

CUSTOM is the one role this matrix does not fully decide: its baseline is
view-only, and per-user grants come from the `user_permissions` table
(see `user_has_permission`) — a CUSTOM user's actual capabilities are
never assumed from their role alone.
"""
from __future__ import annotations

import enum

from app.models.enums import Role


class Permission(str, enum.Enum):
    # --- Original (PROMPT 3 §8) ---------------------------------------
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_CAMPAIGNS = "MANAGE_CAMPAIGNS"
    MANAGE_RULES = "MANAGE_RULES"
    MANAGE_INTEGRATIONS = "MANAGE_INTEGRATIONS"  # connect/disconnect Google Drive, Gmail, etc.
    MANAGE_FINANCE = "MANAGE_FINANCE"  # create/edit expenses & revenues
    MANAGE_DOCUMENTS = "MANAGE_DOCUMENTS"  # upload/process/correct/link
    VIEW_FINANCE = "VIEW_FINANCE"
    VIEW_DOCUMENTS = "VIEW_DOCUMENTS"
    VIEW_REPORTS = "VIEW_REPORTS"
    VIEW_AUDIT = "VIEW_AUDIT"

    # --- Granular (PROMPT 4) --------------------------------------------
    DASHBOARD_VIEW = "dashboard.view"
    DOCUMENTS_VIEW = "documents.view"
    DOCUMENTS_UPLOAD = "documents.upload"
    DOCUMENTS_EDIT = "documents.edit"
    DOCUMENTS_DELETE = "documents.delete"
    DOCUMENTS_OCR = "documents.ocr"
    DOCUMENTS_CONFIRM = "documents.confirm"
    EXPENSES_VIEW = "expenses.view"
    EXPENSES_CREATE = "expenses.create"
    EXPENSES_EDIT = "expenses.edit"
    EXPENSES_DELETE = "expenses.delete"
    REVENUES_VIEW = "revenues.view"
    REVENUES_CREATE = "revenues.create"
    REVENUES_EDIT = "revenues.edit"
    REVENUES_DELETE = "revenues.delete"
    FINANCE_VIEW = "finance.view"
    REPORTS_VIEW = "reports.view"
    REPORTS_CREATE = "reports.create"
    REPORTS_EXPORT = "reports.export"
    COMPLIANCE_VIEW = "compliance.view"
    AUDIT_VIEW = "audit.view"
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_EDIT = "users.edit"
    USERS_DISABLE = "users.disable"
    USERS_RESET_PASSWORD = "users.reset_password"
    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_EDIT = "organization.edit"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"
    ADMIN_ACCESS = "admin.access"  # can see an "Administração" area (org-scoped)
    PLATFORM_MANAGE = "platform.manage"  # platform-wide — SUPER_ADMIN only, never granted to an org role
    ORGANIZATION_MANAGE = "organization.manage"


_ALL_VIEW = {
    Permission.VIEW_FINANCE,
    Permission.VIEW_DOCUMENTS,
    Permission.VIEW_REPORTS,
    Permission.VIEW_AUDIT,
}

_GRANULAR_VIEW = {
    Permission.DASHBOARD_VIEW,
    Permission.DOCUMENTS_VIEW,
    Permission.EXPENSES_VIEW,
    Permission.REVENUES_VIEW,
    Permission.FINANCE_VIEW,
    Permission.REPORTS_VIEW,
    Permission.COMPLIANCE_VIEW,
    Permission.AUDIT_VIEW,
}

# Never granted to an organization-scoped role, no matter which role —
# platform.manage is what distinguishes the platform admin from even the
# most privileged organization OWNER (who still gets everything else).
_PLATFORM_ONLY = {Permission.PLATFORM_MANAGE}

_ORG_ADMIN_EXTRAS = {
    Permission.USERS_VIEW,
    Permission.USERS_CREATE,
    Permission.USERS_EDIT,
    Permission.USERS_DISABLE,
    Permission.USERS_RESET_PASSWORD,
    Permission.ORGANIZATION_VIEW,
    Permission.ORGANIZATION_EDIT,
    Permission.ORGANIZATION_MANAGE,
    Permission.SETTINGS_VIEW,
    Permission.SETTINGS_EDIT,
    Permission.ADMIN_ACCESS,
}

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    # --- Original five (PROMPT 3 §8) — unchanged permission sets ---------
    Role.ADMIN: frozenset(set(Permission) - _PLATFORM_ONLY),
    Role.CAMPAIGN_MANAGER: frozenset(
        _ALL_VIEW
        | {
            Permission.MANAGE_CAMPAIGNS,
            Permission.MANAGE_FINANCE,
            Permission.MANAGE_DOCUMENTS,
        }
    ),
    Role.FINANCIAL: frozenset(
        _ALL_VIEW
        | {
            Permission.MANAGE_FINANCE,
            Permission.MANAGE_DOCUMENTS,
        }
    ),
    # Reviews and corrects records (e.g. OCR corrections, document linking)
    # but does not originate new expenses/revenues.
    Role.ACCOUNTANT: frozenset(_ALL_VIEW | {Permission.MANAGE_DOCUMENTS}),
    Role.VIEWER: frozenset(_ALL_VIEW),
    # --- PROMPT 4 — multi-tenant/admin roles ------------------------------
    # OWNER: full control of their own organization — same ceiling as
    # ADMIN, minus platform.manage (platform-exclusive, see _PLATFORM_ONLY).
    Role.OWNER: frozenset(set(Permission) - _PLATFORM_ONLY),
    Role.FINANCEIRO: frozenset(
        _ALL_VIEW
        | _GRANULAR_VIEW
        | {
            Permission.MANAGE_FINANCE,
            Permission.MANAGE_DOCUMENTS,
            Permission.EXPENSES_CREATE,
            Permission.EXPENSES_EDIT,
            Permission.REVENUES_CREATE,
            Permission.REVENUES_EDIT,
            Permission.DOCUMENTS_UPLOAD,
            Permission.DOCUMENTS_EDIT,
            Permission.DOCUMENTS_OCR,
            Permission.DOCUMENTS_CONFIRM,
            Permission.REPORTS_CREATE,
            Permission.REPORTS_EXPORT,
        }
    ),
    Role.OPERACIONAL: frozenset(
        _ALL_VIEW
        | _GRANULAR_VIEW
        | {
            Permission.MANAGE_DOCUMENTS,
            Permission.DOCUMENTS_UPLOAD,
            Permission.DOCUMENTS_EDIT,
            Permission.DOCUMENTS_OCR,
            Permission.DOCUMENTS_CONFIRM,
        }
    ),
    Role.VISUALIZADOR: frozenset(_ALL_VIEW | _GRANULAR_VIEW),
    # CUSTOM's baseline is view-only; real capabilities come from
    # per-user grants in `user_permissions` — see user_has_permission.
    Role.CUSTOM: frozenset(_ALL_VIEW | _GRANULAR_VIEW),
}

# SUPER_ADMIN is deliberately absent from ROLE_PERMISSIONS — it is not "a
# role with every permission", it is structurally outside this matrix (see
# module docstring and user_has_permission below).


def role_has_permission(role: Role, permission: Permission) -> bool:
    """Role-only check — does not know about per-user CUSTOM grants or the
    SUPER_ADMIN bypass. Prefer `user_has_permission` from a request context
    that has a `User` and a `db` session; this is kept for the few call
    sites that only ever see the two original providers' roles."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def user_has_permission(db, user, permission: Permission) -> bool:
    """The real authorization check every route dependency uses.

    SUPER_ADMIN always passes (platform-level, not permission-scoped — see
    module docstring). CUSTOM checks the per-user `user_permissions` table
    instead of a fixed role set. Every other role falls back to the matrix
    above, unchanged from before CUSTOM/SUPER_ADMIN existed.
    """
    if user.role == Role.SUPER_ADMIN:
        return True
    if user.role == Role.CUSTOM:
        from app.models.user_permission import UserPermission

        if permission in ROLE_PERMISSIONS.get(Role.CUSTOM, frozenset()):
            return True
        granted = (
            db.query(UserPermission)
            .filter(UserPermission.user_id == user.id, UserPermission.permission == permission.value)
            .first()
        )
        return granted is not None
    return role_has_permission(user.role, permission)
