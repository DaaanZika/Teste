"""Local authentication placeholder.

V1 runs single-tenant and local: there is no login flow yet. This module
exposes a small `AuthProvider` interface so a real provider (local users
with hashed passwords, then later Google OAuth) can be swapped in without
touching routes. `get_current_user_id` is a FastAPI dependency every
mutating route can depend on today, and it will start requiring a real
token with no call-site changes once a provider is implemented.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

DEFAULT_LOCAL_USER_ID = "local-user"


class AuthProvider(ABC):
    @abstractmethod
    def get_current_user_id(self) -> str: ...


class LocalAuthProvider(AuthProvider):
    """No-op provider: every request acts as a single local operator.

    This is intentionally trivial. Replace with a real provider (session
    cookies, JWT, Google OAuth, ...) later; nothing else in the app needs
    to change because callers only depend on `AuthProvider`.
    """

    def get_current_user_id(self) -> str:
        return DEFAULT_LOCAL_USER_ID


_provider: AuthProvider = LocalAuthProvider()


def get_current_user_id() -> str:
    """FastAPI dependency returning the acting user's id."""
    return _provider.get_current_user_id()
