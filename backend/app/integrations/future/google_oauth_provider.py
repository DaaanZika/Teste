"""Planned Google OAuth login adapter. NOT implemented in V1.

Should eventually implement `app.core.security.AuthProvider` so it can
replace `LocalAuthProvider` behind `get_current_user_id()` without route
changes.
"""
from __future__ import annotations

from app.core.security import AuthProvider


class GoogleOAuthProvider(AuthProvider):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "GoogleOAuthProvider is not implemented in V1. Auth is local-only; see app/core/security.py."
        )

    def get_current_user_id(self) -> str:  # pragma: no cover
        raise NotImplementedError
