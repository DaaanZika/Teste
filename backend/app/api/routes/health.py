from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.health import collect_readiness

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: the process is up. Never checks the database or Redis —
    a slow dependency must not make an otherwise-fine container restart."""
    return {"success": True, "data": {"status": "ok"}}


@router.get("/ready")
def ready(response: Response, db: Session = Depends(get_db)) -> dict:
    """Readiness: only checks dependencies the current configuration
    actually requires (database always; Redis only when QUEUE_BACKEND=redis)."""
    checks = collect_readiness(db)
    all_healthy = all(c.healthy for c in checks)
    response.status_code = 200 if all_healthy else 503
    return {
        "success": all_healthy,
        "data": {
            "status": "ready" if all_healthy else "not_ready",
            "checks": [{"name": c.name, "healthy": c.healthy, "detail": c.detail} for c in checks],
        },
    }
