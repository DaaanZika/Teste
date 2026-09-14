"""Revenue creation, mirroring the expense pipeline (see expense_service)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import AlertType, AuditAction, DocumentLinkStatus, RevenueStatus
from app.models.revenue import Revenue
from app.services.audit.audit_service import record as record_audit
from app.services.compliance.alerts import raise_alert
from app.services.finance.ledger import sync_transaction_for_revenue

_REQUIRED_FIELDS = {
    "amount": "valor",
    "date": "data",
    "donor_name": "doador",
    "document": "documento",
}


def _compute_missing_fields(revenue: Revenue) -> list[str]:
    missing = []
    if revenue.amount is None:
        missing.append(_REQUIRED_FIELDS["amount"])
    if revenue.date is None:
        missing.append(_REQUIRED_FIELDS["date"])
    if not revenue.donor_name:
        missing.append(_REQUIRED_FIELDS["donor_name"])
    if revenue.document_status != DocumentLinkStatus.ATTACHED:
        missing.append(_REQUIRED_FIELDS["document"])
    return missing


def create_revenue(db: Session, data: dict, *, user_id: str | None = None) -> Revenue:
    revenue = Revenue(**data)
    db.add(revenue)
    db.flush()

    if revenue.document_id:
        revenue.document_status = DocumentLinkStatus.ATTACHED

    missing = _compute_missing_fields(revenue)
    revenue.missing_fields = ", ".join(missing) if missing else None
    revenue.status = RevenueStatus.PENDING_INFORMATION if missing else RevenueStatus.COMPLETE

    sync_transaction_for_revenue(db, revenue)
    db.flush()

    record_audit(
        db, entity="revenue", entity_id=revenue.id, action=AuditAction.CREATE, new_value=data, user_id=user_id
    )

    if revenue.document_status != DocumentLinkStatus.ATTACHED:
        raise_alert(
            db,
            type=AlertType.WARNING,
            title="Receita sem documento",
            message=f"A receita {revenue.id} ainda não possui documento anexado.",
            entity="revenue",
            entity_id=revenue.id,
            campaign_id=revenue.campaign_id,
        )

    db.commit()
    db.refresh(revenue)
    return revenue


def get_revenue(db: Session, revenue_id: str) -> Revenue:
    revenue = db.get(Revenue, revenue_id)
    if revenue is None:
        raise NotFoundError(f"Receita {revenue_id} não encontrada.")
    return revenue


def list_revenues(
    db: Session, *, campaign_id: str | None = None, status: RevenueStatus | None = None
) -> list[Revenue]:
    stmt = select(Revenue).order_by(Revenue.created_at.desc())
    if campaign_id is not None:
        stmt = stmt.where(Revenue.campaign_id == campaign_id)
    if status is not None:
        stmt = stmt.where(Revenue.status == status)
    return list(db.execute(stmt).scalars())
