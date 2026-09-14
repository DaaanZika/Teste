"""app/integrations/google_drive_storage.py — folder lookup/creation and
upload/read/delete against the Drive API. All httpx calls are mocked (no
real network call is made or should ever be needed for this suite); what's
under test is the request shape (folder query, multipart upload) and the
NotConfiguredError contract when Drive isn't connected."""
from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import NotConfiguredError
from app.integrations.google_drive_storage import (
    DRIVE_FILES_ENDPOINT,
    FOLDER_MIME_TYPE,
    REFERENCE_PREFIX,
    ROOT_FOLDER_NAME,
    GoogleDriveStorage,
)


@pytest.fixture()
def connected_user(db_session):
    from app.models.enums import Role
    from app.models.user import User

    unique = uuid.uuid4().hex[:8]
    u = User(name="Admin", email=f"drive-admin-{unique}@example.com", role=Role.ADMIN, active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture()
def connected_drive(db_session, connected_user):
    from app.services.integrations import google_tokens

    google_tokens.save_connection(
        db_session,
        user_id=connected_user.id,
        provider="google_drive",
        scope="drive.file",
        access_token="tok-valid",
        refresh_token="refresh-1",
        expires_in_seconds=3600,
    )
    yield GoogleDriveStorage(db_session)
    # The DB in this test suite isn't reset between tests (see conftest.py) —
    # leaving this connection active would leak into other test modules that
    # assume "no active google_drive connection" as their starting state.
    google_tokens.revoke_connection(db_session, "google_drive")


def test_not_connected_raises_not_configured_error(db_session):
    storage = GoogleDriveStorage(db_session)
    with pytest.raises(NotConfiguredError):
        storage.save_original("nota.pdf", b"conteudo")


class _FakeResponse:
    def __init__(self, json_body=None, content=b"", status_code=200):
        self._json = json_body or {}
        self.content = content
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_upload_creates_folder_chain_and_uploads(monkeypatch, connected_drive):
    calls = {"get": [], "post": []}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["get"].append((url, params))
        assert url == DRIVE_FILES_ENDPOINT
        assert FOLDER_MIME_TYPE in params["q"]
        return _FakeResponse(json_body={"files": []})  # no folder exists yet -> must create

    created_folder_ids = iter(["root-folder-id", "originals-folder-id"])

    def fake_post(url, headers=None, params=None, json=None, files=None, timeout=None):
        calls["post"].append((url, json, files))
        if url == DRIVE_FILES_ENDPOINT:
            return _FakeResponse(json_body={"id": next(created_folder_ids)})
        assert url.endswith("/upload/drive/v3/files")
        return _FakeResponse(json_body={"id": "uploaded-file-id"})

    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.get", fake_get)
    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.post", fake_post)

    reference = connected_drive.save_original("nota.pdf", b"conteudo", campaign_id="camp-1")

    assert reference == f"{REFERENCE_PREFIX}uploaded-file-id"
    # root folder + bucket folder both looked up, both created (none existed)
    assert len(calls["get"]) == 2
    assert len(calls["post"]) == 3  # 2 folder creates + 1 file upload

    root_folder_call = calls["post"][0]
    assert root_folder_call[1]["name"] == ROOT_FOLDER_NAME


def test_upload_reuses_existing_folder(monkeypatch, connected_drive):
    def fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse(json_body={"files": [{"id": "existing-folder-id", "name": "x"}]})

    upload_calls = []

    def fake_post(url, headers=None, params=None, json=None, files=None, timeout=None):
        upload_calls.append((url, files))
        return _FakeResponse(json_body={"id": "uploaded-file-id"})

    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.get", fake_get)
    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.post", fake_post)

    connected_drive.save_processed("recibo.png", b"bytes")

    # only the upload POST — folders were found via GET, never created via POST
    assert len(upload_calls) == 1


def test_folder_cache_avoids_duplicate_lookups(monkeypatch, connected_drive):
    get_calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        get_calls.append(params["q"])
        return _FakeResponse(json_body={"files": [{"id": "folder-id", "name": "x"}]})

    def fake_post(url, headers=None, params=None, json=None, files=None, timeout=None):
        return _FakeResponse(json_body={"id": "file-id"})

    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.get", fake_get)
    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.post", fake_post)

    connected_drive.save_temporary("a.pdf", b"1")
    connected_drive.save_temporary("b.pdf", b"2")

    # second upload to the same bucket must hit the in-instance folder cache,
    # not re-query Drive for the same two folders again
    assert len(get_calls) == 2


def test_read_requires_gdrive_reference(connected_drive):
    with pytest.raises(ValueError):
        connected_drive.read("originals/some-local-file.pdf")


def test_read_fetches_media(monkeypatch, connected_drive):
    def fake_get(url, headers=None, params=None, timeout=None):
        assert url == f"{DRIVE_FILES_ENDPOINT}/file-123"
        assert params == {"alt": "media"}
        return _FakeResponse(content=b"file bytes")

    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.get", fake_get)

    content = connected_drive.read(f"{REFERENCE_PREFIX}file-123")
    assert content == b"file bytes"


def test_delete_temporary_ignores_non_gdrive_reference(connected_drive):
    # must not raise / not attempt any HTTP call for a local-style reference
    connected_drive.delete_temporary("temporary/local-file.pdf")


def test_delete_temporary_calls_drive_delete(monkeypatch, connected_drive):
    delete_calls = []

    def fake_delete(url, headers=None, timeout=None):
        delete_calls.append(url)
        return _FakeResponse()

    monkeypatch.setattr("app.integrations.google_drive_storage.httpx.delete", fake_delete)

    connected_drive.delete_temporary(f"{REFERENCE_PREFIX}file-456")
    assert delete_calls == [f"{DRIVE_FILES_ENDPOINT}/file-456"]
