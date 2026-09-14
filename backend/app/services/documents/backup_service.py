"""Optional secondary copy of an uploaded document (PROMPT 3 §12).

Never blocks or fails the upload it's attached to: if BACKUP_STORAGE_PROVIDER
isn't set, `Document.backup_status` simply stays NOT_CONFIGURED (its
default). If it is set but the upload to it fails for any reason (not
connected, network error, ...), the failure is recorded on the document
and as a WARNING alert — the document itself, already safely on its
PRIMARY storage, is entirely unaffected (PROMPT 3 §45: never lose a
document to an integration failure).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.storage_adapter import get_backup_storage_provider
from app.models.document import Document
from app.models.enums import AlertType, BackupStatus
from app.services.compliance.alerts import raise_alert

logger = logging.getLogger("app.documents.backup")


def backup_document(db: Session, document: Document, *, content: bytes, filename: str) -> None:
    settings = get_settings()
    backup_provider = get_backup_storage_provider(db)
    if backup_provider is None:
        return  # backup_status stays NOT_CONFIGURED — nothing to do, not an error

    document.backup_status = BackupStatus.PENDING
    db.commit()

    try:
        reference = backup_provider.save_original(filename, content, campaign_id=document.campaign_id)
    except Exception as exc:  # noqa: BLE001 - a backup failure must never break the upload flow
        logger.warning("Backup failed for document %s: %s", document.id, exc)
        document.backup_status = BackupStatus.FAILED
        document.backup_error = str(exc)
        raise_alert(
            db,
            type=AlertType.WARNING,
            title="Falha no backup do documento",
            message=f"Não foi possível criar cópia de backup do documento {document.id}: {exc}",
            entity="document",
            entity_id=document.id,
            campaign_id=document.campaign_id,
        )
        db.commit()
        return

    document.backup_status = BackupStatus.COMPLETED
    document.backup_storage_provider = settings.backup_storage_provider
    document.backup_external_id = reference
    document.backup_completed_at = datetime.now(timezone.utc)
    document.backup_error = None
    db.commit()
