"""Generic cloud storage adapter (S3-compatible, etc.). NOT implemented in V1."""
from __future__ import annotations

from app.integrations.storage_adapter import StorageProvider


class CloudStorageProvider(StorageProvider):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "CloudStorageProvider is not implemented in V1. See app/integrations/storage_adapter.py."
        )
