"""Password hashing (PROMPT 4). bcrypt directly (not passlib — passlib's
last release predates bcrypt 4.x's API change and warns/breaks on import
with modern bcrypt). A password is never logged, returned in a response,
or stored anywhere but as this hash.
"""
from __future__ import annotations

import bcrypt

_BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("ascii")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        # Malformed/foreign hash (e.g. None coerced upstream) — never a match.
        return False
