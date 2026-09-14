"""FastAPI application entrypoint.

Run locally with:

    uvicorn app.main:app --reload

See README.md for full setup instructions (Tesseract installation,
environment variables, database migrations).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    audit,
    auth,
    campaigns,
    compliance,
    documents,
    expenses,
    finance,
    health,
    reports,
    revenues,
    users,
)
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Organização financeira e documental de campanhas eleitorais — assistente de "
        "organização, conferência e auditoria. Não é o CONTA+JE e não substitui a "
        "prestação de contas oficial ao TSE. Roda 100% local por padrão; Google OAuth, "
        "Google Drive, Gmail e Redis são integrações opcionais (ver app/integrations/)."
    ),
    version="0.2.0",
)

# Credentialed CORS (session cookies) requires an explicit origin allowlist —
# a wildcard "*" is rejected by browsers once allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(campaigns.router)
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
