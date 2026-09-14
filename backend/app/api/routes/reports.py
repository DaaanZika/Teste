from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.reports import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def reports_summary(campaign_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    return report_service.summary_report(db, campaign_id=campaign_id)


@router.get("/expenses")
def reports_expenses(campaign_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return report_service.expenses_report(db, campaign_id=campaign_id)


@router.get("/revenues")
def reports_revenues(campaign_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return report_service.revenues_report(db, campaign_id=campaign_id)


@router.get("/documents")
def reports_documents(campaign_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    return report_service.documents_report(db, campaign_id=campaign_id)
