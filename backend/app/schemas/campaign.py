from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    name: str
    candidate_name: str | None = None
    candidate_document: str | None = None
    campaign_cnpj: str | None = None
    election_year: int | None = None
    election_type: str | None = None
    office: str | None = None
    party: str | None = None
    state: str | None = None
    city: str | None = None


class CampaignUpdate(CampaignCreate):
    name: str | None = None
    status: str | None = None


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    candidate_name: str | None
    candidate_document: str | None
    campaign_cnpj: str | None
    election_year: int | None
    election_type: str | None
    office: str | None
    party: str | None
    state: str | None
    city: str | None
    status: str
    created_at: datetime
    updated_at: datetime
