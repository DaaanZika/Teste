"""Planned cloud storage adapter. NOT implemented or wired up in V1.

When implemented, `GoogleDriveStorage` should satisfy
`app.integrations.storage_adapter.StorageProvider` exactly, so
`get_storage_provider()` can return it based on `Settings.storage_provider`
without any change to `document_service` or the API layer.
"""
from __future__ import annotations

from app.integrations.storage_adapter import StorageProvider


class GoogleDriveStorage(StorageProvider):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "GoogleDriveStorage is not implemented in V1. This backend runs "
            "entirely on local storage; see app/integrations/storage_adapter.py."
        )
