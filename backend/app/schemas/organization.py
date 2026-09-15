from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrganizationStatus


class OrganizationCreate(BaseModel):
    """SUPER_ADMIN only (POST /admin/organizations). Creates the
    organization AND its first OWNER user in one call — an organization
    with no owner is not a useful state to leave the system in."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    plan: str = "standard"
    storage_limit_bytes: int | None = None
    owner_name: str = Field(min_length=1, max_length=255)
    owner_email: str = Field(min_length=1, max_length=255)
    owner_password: str = Field(min_length=8, max_length=255)


class OrganizationUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    storage_limit_bytes: int | None = None


class OrganizationSelfUpdate(BaseModel):
    """What an org OWNER/ADMIN may change about their own organization
    (PATCH /organization) — plan/storage_limit_bytes are SUPER_ADMIN-only
    (PATCH /admin/organizations/{id})."""

    name: str | None = Field(default=None, min_length=1, max_length=255)


class OrganizationStatusUpdate(BaseModel):
    status: OrganizationStatus


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    status: OrganizationStatus
    owner_user_id: str | None
    plan: str
    storage_limit_bytes: int | None
    created_at: datetime
    updated_at: datetime


class OrganizationUsage(BaseModel):
    """Real counts, never fabricated — every field here is a direct
    aggregate query against this organization's own data."""

    organization_id: str
    campaigns_count: int
    users_count: int
    active_users_count: int
    documents_count: int
    documents_processed_count: int
    expenses_count: int
    revenues_count: int
    storage_used_bytes: int


class PlatformMetrics(BaseModel):
    """SUPER_ADMIN dashboard (GET /admin/metrics) — every field is a real
    aggregate query at request time, never a placeholder/fake value."""

    organizations_total: int
    organizations_active: int
    organizations_suspended: int
    organizations_blocked: int
    users_total: int
    users_active: int
    documents_total: int
    documents_processed: int
    documents_failed: int
    expenses_total: int
    revenues_total: int
    storage_used_bytes: int
    ocr_available: bool
    database_healthy: bool
    recent_audit_events: int
