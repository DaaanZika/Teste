"""Expense creation/update, including the free-text quick-entry endpoint.

Implements PROMPT 1 sections 11-13: a quick or partial entry is never
blocked for missing data. Whatever is missing is recorded in
`missing_fields` and the expense is marked `PENDING_INFORMATION`; a
missing supporting document raises a "DESPESA SEM DOCUMENTO" alert instead
of blocking the record.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.campaign import Campaign
from app.models.enums import AlertType, AuditAction, DocumentLinkStatus, ExpenseStatus
from app.models.expense import Expense
from app.services.audit.audit_service import record as record_audit
from app.services.compliance.alerts import raise_alert
from app.services.finance.ledger import sync_transaction_for_expense
from app.services.finance.quick_expense_parser import parse_quick_expense

_REQUIRED_FIELDS = {
    "amount": "valor",
    "date": "data",
    "supplier_name": "fornecedor",
    "document": "documento",
}


def _compute_missing_fields(expense: Expense) -> list[str]:
    missing = []
    if expense.amount is None:
        missing.append(_REQUIRED_FIELDS["amount"])
    if expense.date is None:
        missing.append(_REQUIRED_FIELDS["date"])
    if not expense.supplier_name:
        missing.append(_REQUIRED_FIELDS["supplier_name"])
    if expense.document_status != DocumentLinkStatus.ATTACHED:
        missing.append(_REQUIRED_FIELDS["document"])
    return missing


def _apply_status(expense: Expense) -> None:
    missing = _compute_missing_fields(expense)
    expense.missing_fields = ", ".join(missing) if missing else None
    expense.status = ExpenseStatus.PENDING_INFORMATION if missing else ExpenseStatus.COMPLETE


def _finalize(db: Session, expense: Expense, *, campaign_id: str | None, user_id: str | None) -> Expense:
    if expense.document_id:
        expense.document_status = DocumentLinkStatus.ATTACHED

    _apply_status(expense)
    sync_transaction_for_expense(db, expense)
    db.flush()

    if expense.document_status != DocumentLinkStatus.ATTACHED:
        raise_alert(
            db,
            type=AlertType.WARNING,
            title="Despesa sem documento",
            message=f"A despesa '{expense.description or expense.id}' ainda não possui documento anexado.",
            entity="expense",
            entity_id=expense.id,
            campaign_id=campaign_id,
        )

    db.commit()
    db.refresh(expense)
    return expense


def create_expense(db: Session, data: dict, *, user_id: str | None = None) -> Expense:
    expense = Expense(**data)
    db.add(expense)
    db.flush()

    record_audit(
        db, entity="expense", entity_id=expense.id, action=AuditAction.CREATE, new_value=data, user_id=user_id
    )
    return _finalize(db, expense, campaign_id=expense.campaign_id, user_id=user_id)


def create_quick_expense(db: Session, *, text: str, campaign_id: str | None, user_id: str | None = None) -> Expense:
    parsed = parse_quick_expense(text)

    expense = Expense(
        campaign_id=campaign_id,
        date=parsed.data,
        amount=parsed.valor,
        description=parsed.descricao,
        category=parsed.categoria,
        supplier_name=parsed.fornecedor,
        source_text=text,
    )
    db.add(expense)
    db.flush()

    record_audit(
        db,
        entity="expense",
        entity_id=expense.id,
        action=AuditAction.CREATE,
        new_value={"source_text": text, "fields_found": parsed.fields_found},
        user_id=user_id,
    )
    return _finalize(db, expense, campaign_id=campaign_id, user_id=user_id)


def get_expense(db: Session, expense_id: str) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError(f"Despesa {expense_id} não encontrada.")
    return expense


def get_expense_in_org(db: Session, expense_id: str, *, organization_id: str) -> Expense:
    """404s (never a bare 403) for an expense outside `organization_id`,
    even one that genuinely exists — never confirms cross-org existence."""
    expense = db.get(Expense, expense_id)
    if expense is None or expense.campaign_id is None:
        raise NotFoundError(f"Despesa {expense_id} não encontrada.")
    campaign = db.get(Campaign, expense.campaign_id)
    if campaign is None or campaign.organization_id != organization_id:
        raise NotFoundError(f"Despesa {expense_id} não encontrada.")
    return expense


def list_expenses(
    db: Session, *, organization_id: str, campaign_id: str | None = None, status: ExpenseStatus | None = None
) -> list[Expense]:
    stmt = (
        select(Expense)
        .join(Campaign, Expense.campaign_id == Campaign.id)
        .where(Campaign.organization_id == organization_id)
        .order_by(Expense.created_at.desc())
    )
    if campaign_id is not None:
        stmt = stmt.where(Expense.campaign_id == campaign_id)
    if status is not None:
        stmt = stmt.where(Expense.status == status)
    return list(db.execute(stmt).scalars())


def update_expense(
    db: Session, expense_id: str, updates: dict, *, user_id: str | None = None, organization_id: str
) -> Expense:
    expense = get_expense_in_org(db, expense_id, organization_id=organization_id)
    old_values = {k: getattr(expense, k) for k in updates}

    if "document_id" in updates and updates["document_id"]:
        from app.services.documents.document_service import get_document_in_org

        # Never let an expense in this org link to another org's document.
        document = get_document_in_org(db, updates["document_id"], organization_id=organization_id)

    for field, value in updates.items():
        if value is not None:
            setattr(expense, field, value)

    record_audit(
        db,
        entity="expense",
        entity_id=expense.id,
        action=AuditAction.LINK_DOCUMENT if "document_id" in updates else AuditAction.UPDATE,
        old_value=old_values,
        new_value=updates,
        user_id=user_id,
    )
    return _finalize(db, expense, campaign_id=expense.campaign_id, user_id=user_id)
