"""First SUPER_ADMIN bootstrap (PROMPT 4).

    python -m app.services.admin.bootstrap

Reads SUPER_ADMIN_BOOTSTRAP_EMAIL / SUPER_ADMIN_BOOTSTRAP_PASSWORD from
the environment — there is no hardcoded credential anywhere in this
codebase, and none is ever printed back. Idempotent: if a SUPER_ADMIN
already exists, this does nothing and exits 0 (safe to run on every
container start, e.g. as a Docker Compose entrypoint step) — it never
creates a second one or resets an existing one's password.

To remove the bootstrap mechanism once real SUPER_ADMIN accounts exist:
unset SUPER_ADMIN_BOOTSTRAP_EMAIL/PASSWORD from the environment (this
module has no other effect and is never imported by the running app
itself — only invoked explicitly like above). See backend/README.md.
"""
from __future__ import annotations

import os
import sys

from app.core.database import SessionLocal
from app.core.password import hash_password
from app.models.enums import Role
from app.models.user import User


def bootstrap_super_admin() -> User | None:
    """Returns the created User, or None if a SUPER_ADMIN already existed
    (no-op) or the required env vars aren't set."""
    email = os.environ.get("SUPER_ADMIN_BOOTSTRAP_EMAIL")
    password = os.environ.get("SUPER_ADMIN_BOOTSTRAP_PASSWORD")
    if not email or not password:
        return None

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == Role.SUPER_ADMIN).first()
        if existing is not None:
            return None

        if db.query(User).filter(User.email == email).first() is not None:
            raise ValueError(
                f"Já existe um usuário com o e-mail '{email}' (com outro papel) — "
                "escolha outro e-mail para SUPER_ADMIN_BOOTSTRAP_EMAIL."
            )

        user = User(
            name="Administrador da Plataforma",
            email=email,
            role=Role.SUPER_ADMIN,
            active=True,
            organization_id=None,  # SUPER_ADMIN is platform-level — belongs to no organization
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def main() -> int:
    from app.core.logging import configure_logging

    configure_logging()
    try:
        user = bootstrap_super_admin()
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    if user is None:
        if not os.environ.get("SUPER_ADMIN_BOOTSTRAP_EMAIL"):
            print(
                "SUPER_ADMIN_BOOTSTRAP_EMAIL/SUPER_ADMIN_BOOTSTRAP_PASSWORD não definidos — nada a fazer.",
            )
        else:
            print("Já existe um SUPER_ADMIN cadastrado — nada a fazer.")
        return 0

    print(f"SUPER_ADMIN criado: {user.email} (id={user.id}).")
    print(
        "Guarde a senha em um gerenciador seguro e remova SUPER_ADMIN_BOOTSTRAP_PASSWORD "
        "do ambiente assim que possível — este mecanismo não a usa novamente depois de criada a conta."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
