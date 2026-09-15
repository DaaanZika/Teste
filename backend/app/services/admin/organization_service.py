"""Platform administration (PROMPT 4 FASE 6/7) — organization CRUD and the
real (never fabricated) metrics behind the SUPER_ADMIN dashboard. Every
number returned here is a direct aggregate query run at request time.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.password import hash_password
from app.models.audit import AuditLog
from app.models.campaign import Campaign
from app.models.document import Document
from app.models.enums import AuditAction, DocumentStatus, OrganizationStatus, Role
from app.models.expense import Expense
from app.models.organization import Organization
from app.models.revenue import Revenue
from app.models.user import User
from app.services.audit.audit_service import record as record_audit
from app.services.ocr.engine import is_tesseract_available


def list_organizations(
    db: Session, *, search: str | None = None, status: OrganizationStatus | None = None
) -> list[Organization]:
    stmt = select(Organization).order_by(Organization.created_at.desc())
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(Organization.name).like(like) | func.lower(Organization.slug).like(like))
    if status is not None:
        stmt = stmt.where(Organization.status == status)
    return list(db.execute(stmt).scalars())


def get_organization(db: Session, organization_id: str) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError(f"Organização {organization_id} não encontrada.")
    return org


def create_organization(
    db: Session,
    *,
    name: str,
    slug: str,
    plan: str,
    storage_limit_bytes: int | None,
    owner_name: str,
    owner_email: str,
    owner_password: str,
    actor_id: str | None,
) -> Organization:
    if db.execute(select(Organization).where(Organization.slug == slug)).scalar_one_or_none() is not None:
        raise ConflictError(f"Já existe uma organização com o identificador '{slug}'.")
    if db.execute(select(User).where(User.email == owner_email)).scalar_one_or_none() is not None:
        raise ConflictError(f"Já existe um usuário com o e-mail '{owner_email}'.")

    org = Organization(name=name, slug=slug, plan=plan, storage_limit_bytes=storage_limit_bytes)
    db.add(org)
    db.flush()

    owner = User(
        name=owner_name,
        email=owner_email,
        role=Role.OWNER,
        active=True,
        organization_id=org.id,
        password_hash=hash_password(owner_password),
    )
    db.add(owner)
    db.flush()

    org.owner_user_id = owner.id

    record_audit(
        db,
        entity="organization",
        entity_id=org.id,
        action=AuditAction.ORGANIZATION_CREATED,
        new_value={"name": name, "slug": slug, "owner_email": owner_email},
        user_id=actor_id,
        organization_id=org.id,
    )
    db.commit()
    db.refresh(org)
    return org


def update_organization(db: Session, organization_id: str, updates: dict, *, actor_id: str | None) -> Organization:
    org = get_organization(db, organization_id)
    for field, value in updates.items():
        setattr(org, field, value)
    record_audit(
        db,
        entity="organization",
        entity_id=org.id,
        action=AuditAction.ORGANIZATION_UPDATED,
        new_value=updates,
        user_id=actor_id,
        organization_id=org.id,
    )
    db.commit()
    db.refresh(org)
    return org


def set_organization_status(
    db: Session, organization_id: str, new_status: OrganizationStatus, *, actor_id: str | None
) -> Organization:
    org = get_organization(db, organization_id)
    old_status = org.status
    org.status = new_status
    record_audit(
        db,
        entity="organization",
        entity_id=org.id,
        action=AuditAction.ORGANIZATION_STATUS_CHANGED,
        old_value={"status": old_status.value},
        new_value={"status": new_status.value},
        user_id=actor_id,
        organization_id=org.id,
    )
    db.commit()
    db.refresh(org)
    return org


def _campaign_ids_for_org(db: Session, organization_id: str) -> list[str]:
    return list(db.execute(select(Campaign.id).where(Campaign.organization_id == organization_id)).scalars())


def get_organization_usage(db: Session, organization_id: str) -> dict:
    get_organization(db, organization_id)  # 404s if missing
    campaign_ids = _campaign_ids_for_org(db, organization_id)

    users_count = db.execute(
        select(func.count()).select_from(User).where(User.organization_id == organization_id)
    ).scalar_one()
    active_users_count = db.execute(
        select(func.count())
        .select_from(User)
        .where(User.organization_id == organization_id, User.active.is_(True))
    ).scalar_one()

    if not campaign_ids:
        documents_count = documents_processed_count = expenses_count = revenues_count = storage_used_bytes = 0
    else:
        documents_count = db.execute(
            select(func.count()).select_from(Document).where(Document.campaign_id.in_(campaign_ids))
        ).scalar_one()
        documents_processed_count = db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.campaign_id.in_(campaign_ids), Document.status == DocumentStatus.PROCESSED)
        ).scalar_one()
        expenses_count = db.execute(
            select(func.count()).select_from(Expense).where(Expense.campaign_id.in_(campaign_ids))
        ).scalar_one()
        revenues_count = db.execute(
            select(func.count()).select_from(Revenue).where(Revenue.campaign_id.in_(campaign_ids))
        ).scalar_one()
        storage_used_bytes = db.execute(
            select(func.coalesce(func.sum(Document.file_size_bytes), 0)).where(
                Document.campaign_id.in_(campaign_ids)
            )
        ).scalar_one()

    return {
        "organization_id": organization_id,
        "campaigns_count": len(campaign_ids),
        "users_count": users_count,
        "active_users_count": active_users_count,
        "documents_count": documents_count,
        "documents_processed_count": documents_processed_count,
        "expenses_count": expenses_count,
        "revenues_count": revenues_count,
        "storage_used_bytes": int(storage_used_bytes),
    }


def get_platform_metrics(db: Session) -> dict:
    """The SUPER_ADMIN dashboard's numbers — every one a real query run
    right now against this database, not a cached or fabricated value."""
    from app.core.health import check_database

    orgs_by_status = dict(
        db.execute(select(Organization.status, func.count()).group_by(Organization.status)).all()
    )
    users_total = db.execute(select(func.count()).select_from(User)).scalar_one()
    users_active = db.execute(select(func.count()).select_from(User).where(User.active.is_(True))).scalar_one()

    documents_total = db.execute(select(func.count()).select_from(Document)).scalar_one()
    documents_processed = db.execute(
        select(func.count()).select_from(Document).where(Document.status == DocumentStatus.PROCESSED)
    ).scalar_one()
    documents_failed = db.execute(
        select(func.count()).select_from(Document).where(Document.status == DocumentStatus.FAILED)
    ).scalar_one()

    expenses_total = db.execute(select(func.count()).select_from(Expense)).scalar_one()
    revenues_total = db.execute(select(func.count()).select_from(Revenue)).scalar_one()
    storage_used_bytes = db.execute(select(func.coalesce(func.sum(Document.file_size_bytes), 0))).scalar_one()

    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_audit_events = db.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.timestamp >= since)
    ).scalar_one()

    db_check = check_database(db)

    return {
        "organizations_total": sum(orgs_by_status.values()),
        "organizations_active": orgs_by_status.get(OrganizationStatus.ACTIVE, 0),
        "organizations_suspended": orgs_by_status.get(OrganizationStatus.SUSPENDED, 0),
        "organizations_blocked": orgs_by_status.get(OrganizationStatus.BLOCKED, 0),
        "users_total": users_total,
        "users_active": users_active,
        "documents_total": documents_total,
        "documents_processed": documents_processed,
        "documents_failed": documents_failed,
        "expenses_total": expenses_total,
        "revenues_total": revenues_total,
        "storage_used_bytes": int(storage_used_bytes),
        "ocr_available": is_tesseract_available(),
        "database_healthy": db_check.healthy,
        "recent_audit_events": recent_audit_events,
    }
