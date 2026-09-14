"""app/integrations/storage_adapter.py — provider selection.

`get_storage_provider` must always follow the *current* global setting;
`get_storage_provider_for_document` must always follow whatever provider a
given document was actually stored under, even after the global setting
has since changed (PROMPT 3 §11 — old documents must stay readable).
"""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.integrations.google_drive_storage import GoogleDriveStorage
from app.integrations.storage_adapter import (
    LocalStorage,
    get_backup_storage_provider,
    get_storage_provider,
    get_storage_provider_for_document,
)


@pytest.fixture()
def restore_settings():
    settings = get_settings()
    original_storage_provider = settings.storage_provider
    original_backup_provider = settings.backup_storage_provider
    yield settings
    settings.storage_provider = original_storage_provider
    settings.backup_storage_provider = original_backup_provider


def test_get_storage_provider_defaults_to_local(db_session, restore_settings):
    restore_settings.storage_provider = "local"
    provider = get_storage_provider(db_session)
    assert isinstance(provider, LocalStorage)


def test_get_storage_provider_follows_current_setting(db_session, restore_settings):
    restore_settings.storage_provider = "google_drive"
    provider = get_storage_provider(db_session)
    assert isinstance(provider, GoogleDriveStorage)


def test_get_storage_provider_for_document_ignores_current_setting(db_session, restore_settings):
    """A document stored under 'local' stays readable via LocalStorage even
    after the global default has moved on to google_drive."""
    restore_settings.storage_provider = "google_drive"
    provider = get_storage_provider_for_document(db_session, "local")
    assert isinstance(provider, LocalStorage)


def test_get_storage_provider_for_document_google_drive(db_session, restore_settings):
    restore_settings.storage_provider = "local"
    provider = get_storage_provider_for_document(db_session, "google_drive")
    assert isinstance(provider, GoogleDriveStorage)


def test_unknown_provider_raises(db_session):
    with pytest.raises(NotImplementedError):
        get_storage_provider_for_document(db_session, "dropbox")


def test_get_backup_storage_provider_none_when_unset(db_session, restore_settings):
    restore_settings.backup_storage_provider = None
    assert get_backup_storage_provider(db_session) is None


def test_get_backup_storage_provider_google_drive(db_session, restore_settings):
    restore_settings.backup_storage_provider = "google_drive"
    provider = get_backup_storage_provider(db_session)
    assert isinstance(provider, GoogleDriveStorage)


def test_get_backup_storage_provider_unknown_raises(db_session, restore_settings):
    restore_settings.backup_storage_provider = "dropbox"
    with pytest.raises(NotImplementedError):
        get_backup_storage_provider(db_session)
