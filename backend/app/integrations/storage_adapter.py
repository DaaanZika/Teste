"""Storage adapter interface.

`document_service` depends only on `StorageProvider`, never on the
filesystem or on Google Drive directly. `LocalStorage` is the default;
`GoogleDriveStorage` (app/integrations/google_drive_storage.py) implements
the same interface and is selected via `STORAGE_PROVIDER=google_drive`
without any calling code changing (PROMPT 3 §10).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.utils.files import resolve_within, unique_storage_name


class StorageProvider(ABC):
    @abstractmethod
    def save_original(self, filename: str, content: bytes, *, campaign_id: str | None = None) -> str:
        """Persist the untouched original file and return its storage-relative path
        (or, for a remote provider, an opaque reference — see `external_storage_id`
        on the Document model; callers never parse this string themselves)."""

    @abstractmethod
    def save_processed(self, filename: str, content: bytes, *, campaign_id: str | None = None) -> str:
        """Persist a derived/processed artifact and return its storage reference."""

    @abstractmethod
    def save_temporary(self, filename: str, content: bytes) -> str:
        """Persist a short-lived intermediate file and return its storage reference."""

    @abstractmethod
    def read(self, reference: str) -> bytes:
        """Read back a previously stored file by the reference `save_*` returned."""

    @abstractmethod
    def delete_temporary(self, reference: str) -> None:
        """Remove a temporary file. Never applies to originals."""


class LocalStorage(StorageProvider):
    """Filesystem-backed storage under `storage/{originals,processed,temporary}`."""

    def __init__(self) -> None:
        settings = get_settings()
        self._roots = {
            "originals": settings.storage_originals_dir,
            "processed": settings.storage_processed_dir,
            "temporary": settings.storage_temporary_dir,
        }

    def _save(self, bucket: str, filename: str, content: bytes) -> str:
        base_dir = self._roots[bucket]
        stored_name = unique_storage_name(filename)
        destination = resolve_within(base_dir, stored_name)
        destination.write_bytes(content)
        return f"{bucket}/{stored_name}"

    def save_original(self, filename: str, content: bytes, *, campaign_id: str | None = None) -> str:
        return self._save("originals", filename, content)

    def save_processed(self, filename: str, content: bytes, *, campaign_id: str | None = None) -> str:
        return self._save("processed", filename, content)

    def save_temporary(self, filename: str, content: bytes) -> str:
        return self._save("temporary", filename, content)

    def read(self, reference: str) -> bytes:
        bucket, _, name = reference.partition("/")
        base_dir = self._roots[bucket]
        return resolve_within(base_dir, name).read_bytes()

    def delete_temporary(self, reference: str) -> None:
        bucket, _, name = reference.partition("/")
        if bucket != "temporary":
            return
        path = resolve_within(self._roots[bucket], name)
        if path.exists():
            path.unlink()


def _build_provider(provider_name: str, db: Session) -> StorageProvider:
    if provider_name == "local":
        return LocalStorage()
    if provider_name == "google_drive":
        from app.integrations.google_drive_storage import GoogleDriveStorage

        return GoogleDriveStorage(db)
    raise NotImplementedError(f"Storage provider '{provider_name}' is not implemented. Supported: 'local', 'google_drive'.")


def get_storage_provider(db: Session) -> StorageProvider:
    """Selects the PRIMARY provider for a NEW document, from `Settings.storage_provider`.

    `db` is required because a remote provider (Google Drive) needs to look
    up its stored OAuth token — LocalStorage simply ignores it.
    """
    return _build_provider(get_settings().storage_provider, db)


def get_storage_provider_for_document(db: Session, storage_provider: str) -> StorageProvider:
    """Selects the provider that was actually used to store a given, already
    existing document (`Document.storage_provider`), NOT whatever
    `Settings.storage_provider` currently says. If the global setting is
    changed later (e.g. local -> google_drive), older documents stored
    under the previous provider must stay readable — reading them with
    today's default would try the wrong backend and fail.
    """
    return _build_provider(storage_provider, db)


def get_backup_storage_provider(db: Session) -> StorageProvider | None:
    """Selects the OPTIONAL secondary/backup provider (PROMPT 3 §12).
    Returns None when none is configured — callers treat that as
    "backup not applicable", never as an error."""
    settings = get_settings()
    if not settings.backup_storage_provider:
        return None
    if settings.backup_storage_provider == "google_drive":
        from app.integrations.google_drive_storage import GoogleDriveStorage

        return GoogleDriveStorage(db)
    raise NotImplementedError(f"Backup storage provider '{settings.backup_storage_provider}' is not implemented.")
