"""Dependency health checks backing GET /health and GET /ready.

`/health` is a liveness probe: the process is up, full stop — it never
touches the database or Redis, so a slow/dead dependency can't make the
container look crashed when it's actually fine.

`/ready` is a readiness probe: can this instance actually serve traffic
right now? It checks every dependency the *current configuration* actually
requires — Redis is only checked when QUEUE_BACKEND=redis, never
otherwise, matching the rule that Redis is optional (PROMPT 3 §3/§34).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings


@dataclass
class DependencyStatus:
    name: str
    healthy: bool
    detail: str | None = None


def check_database(db: Session) -> DependencyStatus:
    try:
        db.execute(text("SELECT 1"))
        return DependencyStatus(name="database", healthy=True)
    except Exception as exc:  # noqa: BLE001 - report, never raise, from a health check
        return DependencyStatus(name="database", healthy=False, detail=str(exc))


def check_redis() -> DependencyStatus | None:
    settings = get_settings()
    if settings.queue_backend != "redis":
        return None  # not required by the current configuration
    if not settings.redis_url:
        return DependencyStatus(name="redis", healthy=False, detail="QUEUE_BACKEND=redis but REDIS_URL is not set")
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return DependencyStatus(name="redis", healthy=True)
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus(name="redis", healthy=False, detail=str(exc))


def collect_readiness(db: Session) -> list[DependencyStatus]:
    checks = [check_database(db), check_redis()]
    return [c for c in checks if c is not None]
