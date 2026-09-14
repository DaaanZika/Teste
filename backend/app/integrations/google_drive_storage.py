"""Google Drive as a StorageProvider (PROMPT 3 §10/§11).

Real Google Drive API v3 calls over HTTPS (httpx) — no SDK. Fully
functional once an admin has connected Google Drive
(POST /integrations/google-drive/connect, see app/api/routes/integrations.py);
until then every method raises NotConfiguredError instead of silently
writing to local disk or pretending to succeed.

Folder layout created lazily under "Campanhas Eleitorais" in the
connected account's Drive: one subfolder per storage bucket (originals,
processed, temporary) — matching the buckets `document_service` already
uses for local storage. This is a simplification of PROMPT 3 §11's
suggested Receitas/Despesas/Documentos/Relatórios/Auditoria layout: which
financial category a document belongs to isn't known at storage time
(only after it's linked to an expense/revenue), so that finer-grained
folder split isn't implemented here — files are organized by processing
stage instead, and the campaign/category association is queryable through
the database.
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import NotConfiguredError
from app.integrations.storage_adapter import StorageProvider
from app.services.integrations.google_tokens import get_valid_access_token

DRIVE_FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/drive/v3/files"
ROOT_FOLDER_NAME = "Campanhas Eleitorais"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

REFERENCE_PREFIX = "gdrive:"


class GoogleDriveStorage(StorageProvider):
    def __init__(self, db: Session) -> None:
        self._db = db
        self._folder_cache: dict[str, str] = {}

    def _access_token(self) -> str:
        token = get_valid_access_token(self._db, "google_drive")
        if token is None:
            raise NotConfiguredError(
                "Google Drive não está conectado. Conecte em Configurações > Integrações "
                "ou use STORAGE_PROVIDER=local."
            )
        return token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token()}"}

    def _find_folder(self, name: str, parent_id: str | None) -> str | None:
        parent_clause = f" and '{parent_id}' in parents" if parent_id else ""
        query = f"name = '{name}' and mimeType = '{FOLDER_MIME_TYPE}' and trashed = false{parent_clause}"
        response = httpx.get(
            DRIVE_FILES_ENDPOINT,
            headers=self._headers(),
            params={"q": query, "fields": "files(id,name)", "spaces": "drive"},
            timeout=10,
        )
        response.raise_for_status()
        files = response.json().get("files", [])
        return files[0]["id"] if files else None

    def _create_folder(self, name: str, parent_id: str | None) -> str:
        metadata = {"name": name, "mimeType": FOLDER_MIME_TYPE}
        if parent_id:
            metadata["parents"] = [parent_id]
        response = httpx.post(
            DRIVE_FILES_ENDPOINT,
            headers={**self._headers(), "Content-Type": "application/json"},
            params={"fields": "id"},
            json=metadata,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["id"]

    def _ensure_folder(self, name: str, parent_id: str | None) -> str:
        cache_key = f"{parent_id}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]
        folder_id = self._find_folder(name, parent_id) or self._create_folder(name, parent_id)
        self._folder_cache[cache_key] = folder_id
        return folder_id

    def _bucket_folder_id(self, bucket: str) -> str:
        root_id = self._ensure_folder(ROOT_FOLDER_NAME, None)
        return self._ensure_folder(bucket, root_id)

    def _upload(self, bucket: str, filename: str, content: bytes) -> str:
        folder_id = self._bucket_folder_id(bucket)
        metadata = {"name": filename, "parents": [folder_id]}

        files = {
            "metadata": (None, json.dumps(metadata), "application/json"),
            "file": (filename, content),
        }
        response = httpx.post(
            DRIVE_UPLOAD_ENDPOINT,
            headers=self._headers(),
            params={"uploadType": "multipart", "fields": "id"},
            files=files,
            timeout=60,
        )
        response.raise_for_status()
        file_id = response.json()["id"]
        return f"{REFERENCE_PREFIX}{file_id}"

    def save_original(self, filename: str, content: bytes, *, campaign_id: str | None = None) -> str:
        return self._upload("originals", filename, content)

    def save_processed(self, filename: str, content: bytes, *, campaign_id: str | None = None) -> str:
        return self._upload("processed", filename, content)

    def save_temporary(self, filename: str, content: bytes) -> str:
        return self._upload("temporary", filename, content)

    def read(self, reference: str) -> bytes:
        if not reference.startswith(REFERENCE_PREFIX):
            raise ValueError(f"Not a Google Drive reference: {reference!r}")
        file_id = reference.removeprefix(REFERENCE_PREFIX)
        response = httpx.get(
            f"{DRIVE_FILES_ENDPOINT}/{file_id}",
            headers=self._headers(),
            params={"alt": "media"},
            timeout=30,
        )
        response.raise_for_status()
        return response.content

    def delete_temporary(self, reference: str) -> None:
        if not reference.startswith(REFERENCE_PREFIX):
            return
        file_id = reference.removeprefix(REFERENCE_PREFIX)
        httpx.delete(f"{DRIVE_FILES_ENDPOINT}/{file_id}", headers=self._headers(), timeout=10)
