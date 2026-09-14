"""Append-only audit trail.

Every service that mutates a record important enough to matter for
accountability (documents, expenses, revenues, manual corrections) calls
`record` instead of writing to `audit_logs` directly, so the log format
stays consistent and nothing ever overwrites or deletes a prior entry.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction


def _serialize(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except TypeError:
        return str(value)


def record(
    db: Session,
    *,
    entity: str,
    entity_id: str,
    action: AuditAction,
    old_value: Any = None,
    new_value: Any = None,
    user_id: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        entity=entity,
        entity_id=entity_id,
        action=action,
        old_value=_serialize(old_value),
        new_value=_serialize(new_value),
        user_id=user_id,
    )
    db.add(entry)
    db.flush()
    return entry
