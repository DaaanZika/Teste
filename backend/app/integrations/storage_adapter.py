"""Storage adapter interface.

`document_service` depends only on `StorageProvider`, never on the
filesystem directly. `LocalStorage` is the only implementation wired up in
V1; a future `GoogleDriveStorage` (see app/integrations/future) implements
the same interface and can be swapped in via `Settings.storage_provider`
without touching any calling code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings
from app.utils.files import resolve_within, unique_storage_name


class StorageProvider(ABC):
    @abstractmethod
    def save_original(self, filename: str, content: bytes) -> str:
        """Persist the untouched original file and return its storage-relative path."""

    @abstractmethod
    def save_processed(self, filename: str, content: bytes) -> str:
        """Persist a derived/processed artifact and return its storage-relative path."""

    @abstractmethod
    def save_temporary(self, filename: str, content: bytes) -> str:
        """Persist a short-lived intermediate file and return its storage-relative path."""

    @abstractmethod
    def read(self, relative_path: str) -> bytes:
        """Read back a previously stored file by its storage-relative path."""

    @abstractmethod
    def delete_temporary(self, relative_path: str) -> None:
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

    def save_original(self, filename: str, content: bytes) -> str:
        return self._save("originals", filename, content)

    def save_processed(self, filename: str, content: bytes) -> str:
        return self._save("processed", filename, content)

    def save_temporary(self, filename: str, content: bytes) -> str:
        return self._save("temporary", filename, content)

    def read(self, relative_path: str) -> bytes:
        bucket, _, name = relative_path.partition("/")
        base_dir = self._roots[bucket]
        return resolve_within(base_dir, name).read_bytes()

    def delete_temporary(self, relative_path: str) -> None:
        bucket, _, name = relative_path.partition("/")
        if bucket != "temporary":
            return
        path = resolve_within(self._roots[bucket], name)
        if path.exists():
            path.unlink()


def get_storage_provider() -> StorageProvider:
    """Selects the active storage backend based on `Settings.storage_provider`.

    Only "local" is implemented in V1. Any other value fails loudly instead
    of silently falling back, so a misconfigured `.env` cannot pretend to
    upload documents to a cloud provider that was never wired up.
    """
    settings = get_settings()
    if settings.storage_provider != "local":
        raise NotImplementedError(
            f"Storage provider '{settings.storage_provider}' is not implemented in V1. "
            "Only 'local' is supported. See app/integrations/future/ for planned adapters."
        )
    return LocalStorage()
