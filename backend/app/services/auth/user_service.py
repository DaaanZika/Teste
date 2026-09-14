"""Upserts a local User row from a verified Google profile.

Role defaults to the safest option (VIEWER) on first login — nobody is
ever auto-granted write access just by signing in with Google; an ADMIN
must explicitly promote them (PATCH /users/{id}).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import AuditAction, Role
from app.models.user import User
from app.services.audit.audit_service import record as record_audit
from app.services.auth.google_oauth import GoogleProfile


def get_or_create_user_from_google(db: Session, profile: GoogleProfile) -> User:
    stmt = select(User).where(User.google_id == profile.google_id)
    user = db.execute(stmt).scalar_one_or_none()

    if user is not None:
        changed = False
        if profile.name and user.name != profile.name:
            user.name = profile.name
            changed = True
        if profile.avatar and user.avatar != profile.avatar:
            user.avatar = profile.avatar
            changed = True
        if changed:
            db.commit()
        return user

    user = User(
        name=profile.name or profile.email or "Usuário Google",
        email=profile.email,
        google_id=profile.google_id,
        avatar=profile.avatar,
        role=Role.VIEWER,
        active=True,
    )
    db.add(user)
    db.flush()
    record_audit(db, entity="user", entity_id=user.id, action=AuditAction.CREATE, new_value={"via": "google_oauth"})
    db.commit()
    db.refresh(user)
    return user
