"""Application configuration.

All settings are environment-driven so the same codebase can move between
local SQLite storage and, later, PostgreSQL / cloud storage without code
changes. See `.env.example` for the full list of supported variables.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General
    app_name: str = "Campanhas Eleitorais - Backend"
    environment: str = "local"
    debug: bool = True

    # CORS. Comma-separated origins allowed to call this API with
    # credentials (cookies). "*" is intentionally never accepted here:
    # browsers reject a wildcard origin combined with credentialed
    # requests, and session cookies (auth_provider="google") depend on
    # credentialed cross-origin requests working correctly.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Database. Defaults to local SQLite; set DATABASE_URL to a
    # postgresql+psycopg://... URL later to migrate without code changes.
    database_url: str = f"sqlite:///{BASE_DIR / 'storage' / 'app.db'}"

    # Storage (local filesystem only in V1). A future STORAGE_PROVIDER
    # setting will select between "local", "google_drive", etc.
    storage_provider: str = "local"
    storage_root: Path = BASE_DIR / "storage"
    storage_originals_dir: Path = BASE_DIR / "storage" / "originals"
    storage_processed_dir: Path = BASE_DIR / "storage" / "processed"
    storage_temporary_dir: Path = BASE_DIR / "storage" / "temporary"

    # Upload limits / security
    max_upload_size_bytes: int = 20 * 1024 * 1024  # 20 MB
    allowed_upload_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".pdf")
    allowed_upload_mime_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    )

    # Auth. "local" keeps the V1 single-operator behavior (core/security.py);
    # "google" activates real Google OAuth (core/auth/google_oauth.py) once
    # GOOGLE_CLIENT_ID/SECRET are set. Session cookies carry a random
    # 256-bit opaque token (secrets.token_urlsafe) that the database only
    # ever stores hashed (app/services/auth/session_service.py) — NOT a
    # value signed with secret_key below. secret_key is currently unused by
    # any code path; it's kept as a required, must-be-rotated placeholder
    # so a future stateless/signed-token scheme has a secret already wired
    # through config/docker-compose/.env.example instead of one added
    # later under time pressure. Never commit a real value here — FASE H
    # audit note, not a claim that this key currently protects anything.
    auth_provider: str = "local"
    secret_key: str = "change-me-in-production-local-dev-secret"
    session_cookie_name: str = "campanhas_session"
    session_ttl_hours: int = 12

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    # Where /auth/google/callback sends the browser after a successful login.
    frontend_url: str = "http://localhost:5173"

    # Cloud storage (used only when storage_provider != "local", see
    # app/integrations/storage_adapter.py). backup_storage_provider is
    # optional and independent — PRIMARY storage never depends on it.
    storage_bucket: str | None = None
    storage_region: str | None = None
    backup_storage_provider: str | None = None

    # Redis: only required when queue_backend="redis" (see app/queue/).
    # queue_backend="inline" (the default) runs jobs synchronously in the
    # request, exactly like V1 — Redis is never mandatory for local use.
    redis_url: str | None = None
    queue_backend: str = "inline"

    # Outbound email (Gmail import notifications, future use). Optional.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    # OCR
    tesseract_cmd: str | None = None  # if None, relies on PATH
    ocr_language: str = "por"

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for directory in (
        settings.storage_root,
        settings.storage_originals_dir,
        settings.storage_processed_dir,
        settings.storage_temporary_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return settings
