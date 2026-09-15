"""Multi-tenant scoping (PROMPT 4).

The organization boundary is derived from the authenticated session only —
never from a client-supplied `organization_id` query param, path param, or
request body field. Every route that reads/writes organization-scoped data
depends on `require_organization_scope`, not on trusting the caller.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import get_current_user
from app.models.campaign import Campaign
from app.models.enums import Role
from app.models.user import User


def campaign_ids_for_org(db: Session, organization_id: str) -> list[str]:
    return list(db.execute(select(Campaign.id).where(Campaign.organization_id == organization_id)).scalars())


def get_or_create_default_campaign(db: Session, organization_id: str) -> Campaign:
    """Every document/expense/revenue must be anchored to a real,
    org-owned campaign — that's the only thing that makes it reachable
    through this organization's isolation boundary (see the routes that
    call `resolve_campaign_id`). A record created without picking a
    specific campaign (still allowed at the API layer, unchanged from V1)
    lands in this organization's oldest campaign, creating one on first use."""
    campaign = db.execute(
        select(Campaign).where(Campaign.organization_id == organization_id).order_by(Campaign.created_at.asc())
    ).scalars().first()
    if campaign is not None:
        return campaign
    campaign = Campaign(name="Campanha Principal", organization_id=organization_id)
    db.add(campaign)
    db.flush()
    return campaign


def resolve_campaign_id(db: Session, organization_id: str, campaign_id: str | None) -> str:
    """A client-supplied campaign_id is validated to belong to the caller's
    organization (404, not 403 — never confirms cross-org existence); no
    campaign_id resolves to the organization's default campaign instead of
    ever leaving the record orgless."""
    if campaign_id is None:
        return get_or_create_default_campaign(db, organization_id).id
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or campaign.organization_id != organization_id:
        raise NotFoundError(f"Campanha {campaign_id} não encontrada.")
    return campaign_id


def resolve_campaign_scope(
    db: Session, organization_id: str, campaign_id: str | None
) -> tuple[str | None, list[str] | None]:
    """For read/aggregate endpoints that accept an OPTIONAL campaign_id
    filter (finance/reports/compliance summaries): a given campaign_id is
    validated to belong to the caller's org (404 otherwise); no campaign_id
    resolves to every campaign in the org (never "every campaign in the
    database" — that would leak every other organization's totals into an
    aggregate with no explicit filter). Returns (campaign_id, campaign_ids)
    — exactly one is non-None, matching finance.calculator's signature."""
    if campaign_id is not None:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None or campaign.organization_id != organization_id:
            raise NotFoundError(f"Campanha {campaign_id} não encontrada.")
        return campaign_id, None
    return None, campaign_ids_for_org(db, organization_id)


def require_organization_scope(user: User = Depends(get_current_user)) -> str:
    """Returns the caller's own organization_id. A SUPER_ADMIN has none by
    design (a platform-level account, not scoped to any single tenant) —
    they use the dedicated `/admin` routes (or support access) to reach a
    specific organization's data, never these regular endpoints."""
    if user.organization_id is None:
        raise ForbiddenError(
            "Esta conta não pertence a uma organização — use a área de administração da "
            "plataforma para acessar dados de uma organização específica."
            if user.role == Role.SUPER_ADMIN
            else "Esta conta não está associada a nenhuma organização."
        )
    return user.organization_id
