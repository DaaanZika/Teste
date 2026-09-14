from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.rbac import Permission
from app.models.campaign import Campaign
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from app.services.audit.audit_service import record as record_audit

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignRead], dependencies=[Depends(require_permission(Permission.VIEW_FINANCE))])
def list_campaigns(db: Session = Depends(get_db)) -> list[CampaignRead]:
    campaigns = db.execute(select(Campaign).order_by(Campaign.created_at.desc())).scalars()
    return [CampaignRead.model_validate(c) for c in campaigns]


@router.get(
    "/{campaign_id}",
    response_model=CampaignRead,
    dependencies=[Depends(require_permission(Permission.VIEW_FINANCE))],
)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)) -> CampaignRead:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError(f"Campanha {campaign_id} não encontrada.")
    return CampaignRead.model_validate(campaign)


@router.post("", response_model=CampaignRead)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CAMPAIGNS)),
) -> CampaignRead:
    campaign = Campaign(**payload.model_dump(exclude_unset=True))
    db.add(campaign)
    db.flush()
    record_audit(db, entity="campaign", entity_id=campaign.id, action=AuditAction.CREATE, user_id=user.id)
    db.commit()
    db.refresh(campaign)
    return CampaignRead.model_validate(campaign)


@router.put("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_CAMPAIGNS)),
) -> CampaignRead:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError(f"Campanha {campaign_id} não encontrada.")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(campaign, field, value)

    record_audit(db, entity="campaign", entity_id=campaign.id, action=AuditAction.UPDATE, new_value=updates, user_id=user.id)
    db.commit()
    db.refresh(campaign)
    return CampaignRead.model_validate(campaign)
