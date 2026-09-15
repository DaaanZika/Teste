from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.password import hash_password
from app.core.rbac import Permission
from app.core.tenancy import require_organization_scope
from app.models.enums import AuditAction, Role
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit.audit_service import record as record_audit
from app.services.auth import password_service
from app.services.notifications import email_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead], dependencies=[Depends(require_permission(Permission.MANAGE_USERS))])
def list_users(
    db: Session = Depends(get_db), organization_id: str = Depends(require_organization_scope)
) -> list[UserRead]:
    """Always scoped to the caller's own organization — a SUPER_ADMIN (who
    has no organization_id) uses GET /admin/users or
    GET /admin/organizations/{id}/users instead."""
    users = db.execute(
        select(User).where(User.organization_id == organization_id).order_by(User.created_at.desc())
    ).scalars()
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, dependencies=[Depends(require_permission(Permission.MANAGE_USERS))])
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.MANAGE_USERS)),
    organization_id: str = Depends(require_organization_scope),
) -> UserRead:
    """Administração → Usuários → + Novo Usuário. `organization_id` is
    always the caller's own (never trusted from the payload — PROMPT 4's
    explicit rule) even for a SUPER_ADMIN calling this route; a SUPER_ADMIN
    creating a user directly in another organization is out of scope for
    this endpoint by design — see POST /admin/organizations for the org+
    owner creation flow instead."""
    if payload.role == Role.SUPER_ADMIN:
        raise ForbiddenError("Não é permitido criar um usuário SUPER_ADMIN por esta rota.")
    if db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none() is not None:
        raise ConflictError(f"Já existe um usuário com o e-mail '{payload.email}'.")

    user = User(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        active=payload.active,
        organization_id=organization_id,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        entity="user",
        entity_id=user.id,
        action=AuditAction.USER_CREATED,
        new_value={"name": payload.name, "email": payload.email, "role": payload.role.value},
        user_id=actor.id,
        organization_id=organization_id,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}", response_model=UserRead, dependencies=[Depends(require_permission(Permission.MANAGE_USERS))]
)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.MANAGE_USERS)),
    organization_id: str = Depends(require_organization_scope),
) -> UserRead:
    """Org-scoped (PROMPT 4 FASE 8): a 404, not a 403, for a user outside
    the caller's own organization — never confirms cross-org existence.
    Never lets a caller promote anyone to SUPER_ADMIN, and never lets a
    user demote/deactivate the only remaining ADMIN/OWNER of their org by
    accident (same protection as before, now scoped per-organization)."""
    user = db.get(User, user_id)
    if user is None or user.organization_id != organization_id:
        raise NotFoundError(f"Usuário {user_id} não encontrado.")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("role") == Role.SUPER_ADMIN:
        raise ForbiddenError("Não é permitido promover um usuário a SUPER_ADMIN por esta rota.")

    would_remove_last_admin = (
        user.role in (Role.ADMIN, Role.OWNER)
        and user.active
        and (("role" in updates and updates["role"] not in (Role.ADMIN, Role.OWNER)) or updates.get("active") is False)
    )
    if would_remove_last_admin:
        other_active_admins = db.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.organization_id == organization_id,
                User.role.in_([Role.ADMIN, Role.OWNER]),
                User.active.is_(True),
                User.id != user.id,
            )
        ).scalar_one()
        if other_active_admins == 0:
            raise ConflictError(
                "Não é possível remover ou desativar o último administrador ativo desta organização. "
                "Promova outro usuário a OWNER/ADMIN antes de alterar este."
            )

    old_values = {k: getattr(user, k) for k in updates}

    for field, value in updates.items():
        setattr(user, field, value)

    record_audit(
        db,
        entity="user",
        entity_id=user.id,
        action=AuditAction.USER_DISABLED if updates.get("active") is False else AuditAction.UPDATE,
        old_value={k: (v.value if hasattr(v, "value") else v) for k, v in old_values.items()},
        new_value={k: (v.value if hasattr(v, "value") else v) for k, v in updates.items()},
        user_id=actor.id,
        organization_id=organization_id,
    )
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/reset-password",
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def admin_reset_user_password(
    user_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.MANAGE_USERS)),
    organization_id: str = Depends(require_organization_scope),
) -> dict:
    """An admin-initiated password reset — same token mechanism as
    self-service /auth/forgot-password, e-mailed the same way (or logged if
    SMTP isn't configured). Never returns the token/link in the response."""
    user = db.get(User, user_id)
    if user is None or user.organization_id != organization_id:
        raise NotFoundError(f"Usuário {user_id} não encontrado.")
    if user.email is None:
        raise ConflictError("Este usuário não tem e-mail cadastrado para receber a redefinição.")

    settings = get_settings()
    raw_token = password_service.create_reset_token(db, user)
    record_audit(
        db,
        entity="user",
        entity_id=user.id,
        action=AuditAction.PASSWORD_RESET_REQUESTED,
        user_id=actor.id,
        organization_id=organization_id,
    )
    db.commit()

    reset_link = f"{settings.frontend_url}/redefinir-senha?token={raw_token}"
    email_service.send_email(
        to=user.email,
        subject="Redefinição de senha — Campanhas",
        body=(
            f"Um administrador solicitou a redefinição da sua senha.\n\n"
            f"Use o link abaixo (válido por {password_service.RESET_TOKEN_TTL_MINUTES} minutos):\n{reset_link}"
        ),
    )
    return {"success": True, "data": {"status": "reset_email_sent"}}
