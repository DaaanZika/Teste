"""RBAC permission matrix (PROMPT 3 §8).

The matrix is the single source of truth for "can this role do X" — routes
call `require_permission(Permission.X)`, never `if role == Role.ADMIN`.
That keeps the rule in one place instead of scattered `if` checks that
drift out of sync with each other.

Scope of what this enforces (documented, not silently implied): a
permission controls WHAT an authenticated user's role may do. It does NOT
yet scope WHICH campaign's data a user may see — in this phase every
authenticated user can read every campaign's records. Per-campaign
membership is a separate, not-yet-built feature; see docs/audit for the
gap this leaves.
"""
from __future__ import annotations

import enum

from app.models.enums import Role


class Permission(str, enum.Enum):
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


_ALL_VIEW = {
    Permission.VIEW_FINANCE,
    Permission.VIEW_DOCUMENTS,
    Permission.VIEW_REPORTS,
    Permission.VIEW_AUDIT,
}

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
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
}


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
