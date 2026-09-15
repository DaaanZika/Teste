"""Builds the structured JSON payloads behind the /reports/* endpoints.

Everything here reads from the database and from `finance.calculator`; no
report performs its own ad-hoc math on money, keeping a single source of
truth for every total (PROMPT 1 section 16).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compliance import ComplianceAlert
from app.models.document import Document
from app.models.enums import AlertStatus, DocumentLinkStatus, DocumentStatus, ExpenseStatus, RevenueStatus
from app.models.expense import Expense
from app.models.revenue import Revenue
from app.services.finance import calculator


def summary_report(db: Session, *, campaign_id: str | None = None, campaign_ids: list[str] | None = None) -> dict:
    total_revenues = calculator.total_revenues(db, campaign_id=campaign_id, campaign_ids=campaign_ids)
    total_expenses = calculator.total_expenses(db, campaign_id=campaign_id, campaign_ids=campaign_ids)

    pending_expenses_stmt = select(Expense).where(Expense.status == ExpenseStatus.PENDING_INFORMATION)
    pending_revenues_stmt = select(Revenue).where(Revenue.status == RevenueStatus.PENDING_INFORMATION)
    without_document_stmt = select(Expense).where(Expense.document_status != DocumentLinkStatus.ATTACHED)
    if campaign_id is not None:
        pending_expenses_stmt = pending_expenses_stmt.where(Expense.campaign_id == campaign_id)
        pending_revenues_stmt = pending_revenues_stmt.where(Revenue.campaign_id == campaign_id)
        without_document_stmt = without_document_stmt.where(Expense.campaign_id == campaign_id)
    elif campaign_ids is not None:
        pending_expenses_stmt = pending_expenses_stmt.where(Expense.campaign_id.in_(campaign_ids))
        pending_revenues_stmt = pending_revenues_stmt.where(Revenue.campaign_id.in_(campaign_ids))
        without_document_stmt = without_document_stmt.where(Expense.campaign_id.in_(campaign_ids))

    return {
        "total_revenues": total_revenues,
        "total_expenses": total_expenses,
        "balance": total_revenues - total_expenses,
        "pending_information_expenses": len(list(db.execute(pending_expenses_stmt).scalars())),
        "pending_information_revenues": len(list(db.execute(pending_revenues_stmt).scalars())),
        "expenses_without_document": len(list(db.execute(without_document_stmt).scalars())),
    }


def expenses_report(
    db: Session, *, campaign_id: str | None = None, campaign_ids: list[str] | None = None
) -> list[dict]:
    stmt = select(Expense).order_by(Expense.date.desc().nullslast())
    if campaign_id is not None:
        stmt = stmt.where(Expense.campaign_id == campaign_id)
    elif campaign_ids is not None:
        stmt = stmt.where(Expense.campaign_id.in_(campaign_ids))
    rows = db.execute(stmt).scalars()
    return [
        {
            "id": e.id,
            "date": e.date,
            "supplier_name": e.supplier_name,
            "amount": e.amount,
            "category": e.category,
            "document_id": e.document_id,
            "document_status": e.document_status,
            "status": e.status,
        }
        for e in rows
    ]


def revenues_report(
    db: Session, *, campaign_id: str | None = None, campaign_ids: list[str] | None = None
) -> list[dict]:
    stmt = select(Revenue).order_by(Revenue.date.desc().nullslast())
    if campaign_id is not None:
        stmt = stmt.where(Revenue.campaign_id == campaign_id)
    elif campaign_ids is not None:
        stmt = stmt.where(Revenue.campaign_id.in_(campaign_ids))
    rows = db.execute(stmt).scalars()
    return [
        {
            "id": r.id,
            "source_type": r.source_type,
            "amount": r.amount,
            "date": r.date,
            "document_id": r.document_id,
            "document_status": r.document_status,
            "status": r.status,
        }
        for r in rows
    ]


def documents_report(
    db: Session, *, campaign_id: str | None = None, campaign_ids: list[str] | None = None
) -> dict:
    stmt = select(Document)
    if campaign_id is not None:
        stmt = stmt.where(Document.campaign_id == campaign_id)
    elif campaign_ids is not None:
        stmt = stmt.where(Document.campaign_id.in_(campaign_ids))
    documents = list(db.execute(stmt).scalars())

    return {
        "total": len(documents),
        "processed": sum(1 for d in documents if d.status == DocumentStatus.PROCESSED),
        "pending": sum(
            1 for d in documents if d.status in (DocumentStatus.UPLOADED, DocumentStatus.PROCESSING)
        ),
        "human_review": sum(1 for d in documents if d.status == DocumentStatus.HUMAN_REVIEW),
        "duplicated": sum(1 for d in documents if d.status == DocumentStatus.POSSIBLE_DUPLICATE),
        "failed": sum(1 for d in documents if d.status == DocumentStatus.FAILED),
    }


def audit_report(
    db: Session,
    *,
    entity: str | None = None,
    entity_id: str | None = None,
    organization_id: str | None = None,
) -> dict:
    from app.models.audit import AuditLog

    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if entity is not None:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if organization_id is not None:
        stmt = stmt.where(AuditLog.organization_id == organization_id)
    logs = list(db.execute(stmt).scalars())

    open_alerts = list(db.execute(select(ComplianceAlert).where(ComplianceAlert.status == AlertStatus.OPEN)))

    return {
        "changes": logs,
        "open_alerts": open_alerts,
        "pending_count": len(open_alerts),
    }
