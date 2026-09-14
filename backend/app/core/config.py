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

    # Auth (local-only placeholder in V1; see core/security.py)
    auth_provider: str = "local"
    secret_key: str = "change-me-in-production-local-dev-secret"

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
