"""app/services/documents/backup_service.py — a backup must never affect
the primary upload it's attached to, whatever happens to the backup
provider (PROMPT 3 §12/§45)."""
from __future__ import annotations

import uuid

import pytest

from app.core.config import get_settings
from app.models.campaign import Campaign
from app.models.compliance import ComplianceAlert
from app.models.document import Document
from app.models.enums import BackupStatus
from app.models.organization import Organization
from app.services.documents import backup_service


@pytest.fixture()
def restore_backup_setting():
    settings = get_settings()
    original = settings.backup_storage_provider
    yield settings
    settings.backup_storage_provider = original


@pytest.fixture()
def campaign(db_session):
    org = Organization(name="Org Teste", slug=f"org-{uuid.uuid4().hex[:8]}")
    db_session.add(org)
    db_session.flush()
    c = Campaign(name=f"Campanha {uuid.uuid4().hex[:8]}", organization_id=org.id)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture()
def document(db_session, campaign):
    doc = Document(
        campaign_id=campaign.id,
        original_filename="nota.pdf",
        mime_type="application/pdf",
        file_extension="pdf",
        file_size_bytes=10,
        sha256_hash=uuid.uuid4().hex,
        original_path="originals/nota.pdf",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def test_no_backup_provider_leaves_status_not_configured(db_session, document, restore_backup_setting):
    restore_backup_setting.backup_storage_provider = None
    backup_service.backup_document(db_session, document, content=b"x", filename="nota.pdf")
    assert document.backup_status == BackupStatus.NOT_CONFIGURED


def test_successful_backup_marks_completed(db_session, document, restore_backup_setting, monkeypatch):
    restore_backup_setting.backup_storage_provider = "google_drive"

    class _FakeProvider:
        def save_original(self, filename, content, *, campaign_id=None):
            return "gdrive:backup-file-id"

    monkeypatch.setattr(backup_service, "get_backup_storage_provider", lambda db: _FakeProvider())

    backup_service.backup_document(db_session, document, content=b"x", filename="nota.pdf")

    assert document.backup_status == BackupStatus.COMPLETED
    assert document.backup_storage_provider == "google_drive"
    assert document.backup_external_id == "gdrive:backup-file-id"
    assert document.backup_completed_at is not None
    assert document.backup_error is None


def test_failed_backup_marks_failed_and_raises_alert(db_session, document, restore_backup_setting, monkeypatch):
    restore_backup_setting.backup_storage_provider = "google_drive"

    class _FakeProvider:
        def save_original(self, filename, content, *, campaign_id=None):
            raise RuntimeError("network unreachable")

    monkeypatch.setattr(backup_service, "get_backup_storage_provider", lambda db: _FakeProvider())

    # Must not raise — a backup failure is never allowed to break the upload flow.
    backup_service.backup_document(db_session, document, content=b"x", filename="nota.pdf")

    assert document.backup_status == BackupStatus.FAILED
    assert "network unreachable" in document.backup_error

    alerts = db_session.query(ComplianceAlert).filter_by(entity_id=document.id).all()
    assert len(alerts) == 1
    assert alerts[0].type.value == "WARNING"
