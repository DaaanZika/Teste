"""In-memory rate limiting for sensitive, unauthenticated-reachable
endpoints (login, OAuth callbacks — PROMPT 3 FASE H, closes the gap
tracked in docs/audit/FASE-D-gaps.md "Sem rate limiting no login").

A fixed-window counter per (bucket, client IP), held in process memory —
no external dependency, no Redis requirement (this must work with
QUEUE_BACKEND=inline and no Redis at all, since it protects endpoints that
have nothing to do with the document-processing queue).

This is process-local by design: correct for the single-instance
deployment this system targets (a local operator, or one backend
container). Running multiple backend replicas behind a load balancer would
let each replica track its own count, so the effective limit becomes
`max_attempts * replica_count` — a shared store (e.g. Redis) would be
needed to enforce one true limit across instances. That's a scale-out
concern out of scope for this phase, documented here rather than silently
assumed away.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import Request

from app.core.exceptions import RateLimitExceededError

_lock = Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


def reset_all() -> None:
    """Test-only: clears every tracked window so test runs don't leak rate
    limit state into each other (the counters live in process memory,
    shared across the whole test suite — see conftest.py's single shared
    DATABASE_URL for the same reasoning applied to a different resource)."""
    with _lock:
        _hits.clear()


def enforce_rate_limit(request: Request, *, bucket: str, max_attempts: int, window_seconds: float) -> None:
    key = f"{bucket}:{_client_ip(request)}"
    now = time.monotonic()
    with _lock:
        hits = _hits[key]
        cutoff = now - window_seconds
        while hits and hits[0] < cutoff:
            hits.pop(0)
        if len(hits) >= max_attempts:
            raise RateLimitExceededError(
                "Muitas tentativas em um curto período. Aguarde antes de tentar novamente."
            )
        hits.append(now)


def rate_limit(bucket: str, *, max_attempts: int, window_seconds: float) -> Callable[[Request], None]:
    """FastAPI dependency factory: `dependencies=[Depends(rate_limit("auth_login", max_attempts=10, window_seconds=60))]`."""

    def _dependency(request: Request) -> None:
        enforce_rate_limit(request, bucket=bucket, max_attempts=max_attempts, window_seconds=window_seconds)

    return _dependency
