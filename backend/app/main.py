"""FastAPI application entrypoint.

Run locally with:

    uvicorn app.main:app --reload

See README.md for full setup instructions (Tesseract installation,
environment variables, database migrations).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, compliance, documents, expenses, finance, health, reports, revenues
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend V1 (local) para organização financeira e documental de campanhas "
        "eleitorais. Roda inteiramente local nesta fase: sem Docker, sem Google Drive/Gmail/"
        "OAuth, sem serviços de nuvem. Ver app/integrations/future/ para integrações planejadas."
    ),
    version="0.1.0",
)

# Local-only V1: CORS is permissive by default since there is no cloud
# deployment yet. Tighten this before exposing the API beyond localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(expenses.router)
app.include_router(revenues.router)
app.include_router(finance.router)
app.include_router(reports.router)
app.include_router(compliance.router)
app.include_router(audit.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "success": True,
        "data": {
            "name": settings.app_name,
            "environment": settings.environment,
            "docs": "/docs",
        },
    }
