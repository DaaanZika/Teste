from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.rbac import Permission
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.audit.audit_service import record as record_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead], dependencies=[Depends(require_permission(Permission.MANAGE_USERS))])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars()
    return [UserRead.model_validate(u) for u in users]


@router.patch(
    "/{user_id}", response_model=UserRead, dependencies=[Depends(require_permission(Permission.MANAGE_USERS))]
)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.MANAGE_USERS)),
) -> UserRead:
    """ADMIN only (PROMPT 3 §54): changes another user's role or active flag.
    Never lets a user demote/deactivate the only remaining ADMIN account by accident."""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"Usuário {user_id} não encontrado.")

    updates = payload.model_dump(exclude_unset=True)
    old_values = {k: getattr(user, k) for k in updates}

    for field, value in updates.items():
        setattr(user, field, value)

    record_audit(
        db, entity="user", entity_id=user.id, action=AuditAction.UPDATE,
        old_value={k: (v.value if hasattr(v, "value") else v) for k, v in old_values.items()},
        new_value={k: (v.value if hasattr(v, "value") else v) for k, v in updates.items()},
        user_id=actor.id,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
