from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AuditAction


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity: str
    entity_id: str
    action: AuditAction
    old_value: str | None
    new_value: str | None
    timestamp: datetime
    user_id: str | None
    organization_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
