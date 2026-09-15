from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope
from app.models.campaign import Campaign
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from app.services.audit.audit_service import record as record_audit

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignRead], dependencies=[Depends(require_permission(Permission.VIEW_FINANCE))])
def list_campaigns(
    db: Session = Depends(get_db), organization_id: str = Depends(require_organization_scope)
) -> list[CampaignRead]:
    campaigns = db.execute(
        select(Campaign).where(Campaign.organization_id == organization_id).order_by(Campaign.created_at.desc())
    ).scalars()
    return [CampaignRead.model_validate(c) for c in campaigns]


@router.get(
    "/{campaign_id}",
    response_model=CampaignRead,
    dependencies=[Depends(require_permission(Permission.VIEW_FINANCE))],
)
def get_campaign(
    campaign_id: str, db: Session = Depends(get_db), organization_id: str = Depends(require_organization_scope)
) -> CampaignRead:
    campaign = db.get(Campaign, campaign_id)
    # A campaign that exists but belongs to another organization 404s the
    # same as one that doesn't exist at all — never reveal cross-org
    # existence (PROMPT 4: never trust/leak across the tenant boundary).
    if campaign is None or campaign.organization_id != organization_id:
        raise NotFoundError(f"Campanha {campaign_id} não encontrada.")
    return CampaignRead.model_validate(campaign)


@router.post("", response_model=CampaignRead)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CAMPAIGNS)),
    organization_id: str = Depends(require_organization_scope),
) -> CampaignRead:
    # organization_id always comes from the caller's own session, never
    # from the request body (CampaignCreate has no such field to begin with).
    campaign = Campaign(**payload.model_dump(exclude_unset=True), organization_id=organization_id)
    db.add(campaign)
    db.flush()
    record_audit(
        db,
        entity="campaign",
        entity_id=campaign.id,
        action=AuditAction.CREATE,
        user_id=user.id,
        organization_id=organization_id,
    )
    db.commit()
    db.refresh(campaign)
    return CampaignRead.model_validate(campaign)


@router.put("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CAMPAIGNS)),
    organization_id: str = Depends(require_organization_scope),
) -> CampaignRead:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or campaign.organization_id != organization_id:
        raise NotFoundError(f"Campanha {campaign_id} não encontrada.")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(campaign, field, value)

    record_audit(
        db,
        entity="campaign",
        entity_id=campaign.id,
        action=AuditAction.UPDATE,
        new_value=updates,
        user_id=user.id,
        organization_id=organization_id,
    )
    db.commit()
    db.refresh(campaign)
    return CampaignRead.model_validate(campaign)
