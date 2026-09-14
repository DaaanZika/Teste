from __future__ import annotations

from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    name: str
    connected: bool
    detail: str | None = None


class IntegrationsStatusResponse(BaseModel):
    """Backs the "INTEGRAÇÕES" panel (PROMPT 3 §44) — every field reflects
    real, just-checked state, never an assumption."""

    google_oauth: IntegrationStatus
    google_drive: IntegrationStatus
    gmail: IntegrationStatus
    backup: IntegrationStatus
    database: IntegrationStatus
    ocr: IntegrationStatus
