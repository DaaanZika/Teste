"""app/services/backup/backup_service.py — an ACTUAL tested restore, not
just "the file was created" (PROMPT 3 FASE K's explicit requirement).

Every test here performs a real backup, genuinely destroys the live data
(drops the schema / deletes the SQLite file / empties the storage
directory), restores from the backup file, and only then asserts the
specific known data is back — proving the restore path actually works,
not assuming it from the backup path alone.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.campaign import Campaign
from app.models.document import Document
from app.models.organization import Organization
from app.services.backup.backup_service import (
    UnsupportedDatabaseError,
    create_backup,
    restore_backup,
)

PG_ADMIN_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
PG_TEST_DB = "campanhas_backup_restore_test"
PG_TEST_URL = f"postgresql+psycopg://postgres:postgres@localhost:5432/{PG_TEST_DB}"


def test_unsupported_database_url_raises(tmp_path: Path):
    with pytest.raises(UnsupportedDatabaseError):
        create_backup(database_url="mysql://x/y", storage_root=tmp_path, backup_dir=tmp_path / "backups")


def test_sqlite_backup_of_nonexistent_database_raises_instead_of_backing_up_nothing(tmp_path: Path):
    """sqlite3.connect() silently creates an empty file for a path that
    doesn't exist — without an explicit check this would "succeed" with a
    backup of zero tables instead of failing loudly."""
    from app.services.backup.backup_service import BackupFailedError

    database_url = f"sqlite:///{tmp_path / 'does-not-exist.db'}"
    with pytest.raises(BackupFailedError):
        create_backup(database_url=database_url, storage_root=tmp_path / "storage", backup_dir=tmp_path / "backups")


# --- SQLite: full round trip -----------------------------------------------


def _sqlite_engine_and_session(db_path: Path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)


def test_sqlite_backup_then_real_data_loss_then_restore_recovers_everything(tmp_path: Path):
    db_path = tmp_path / "original.db"
    storage_root = tmp_path / "storage"
    (storage_root / "originals").mkdir(parents=True)
    (storage_root / "originals" / "nota.txt").write_text("conteúdo original do documento")
    (storage_root / "processed").mkdir(parents=True)
    backup_dir = tmp_path / "backups"

    engine, Session = _sqlite_engine_and_session(db_path)
    session = Session()
    org_id = str(uuid.uuid4())
    session.add(Organization(id=org_id, name="Org Backup", slug=f"org-backup-{uuid.uuid4().hex[:8]}"))
    session.flush()
    campaign_id = str(uuid.uuid4())
    session.add(Campaign(id=campaign_id, name="Campanha para teste de backup", organization_id=org_id))
    session.commit()
    session.close()
    engine.dispose()

    database_url = f"sqlite:///{db_path}"
    result = create_backup(database_url=database_url, storage_root=storage_root, backup_dir=backup_dir)

    assert result.path.exists()
    assert result.manifest.table_row_counts["campaigns"] == 1

    # Genuinely destroy the data — not a simulation.
    db_path.unlink()
    (storage_root / "originals" / "nota.txt").unlink()
    assert not db_path.exists()

    restore_result = restore_backup(backup_path=result.path, database_url=database_url, storage_root=storage_root)

    assert restore_result.verified is True
    assert restore_result.restored_table_row_counts["campaigns"] == 1

    # The actual proof: query the restored database for the specific row.
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT id, name FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    conn.close()
    assert row == (campaign_id, "Campanha para teste de backup")

    # And the document file itself came back with the right content.
    restored_file = storage_root / "originals" / "nota.txt"
    assert restored_file.exists()
    assert restored_file.read_text() == "conteúdo original do documento"


def test_sqlite_restore_flags_mismatch_when_manifest_is_tampered(tmp_path: Path):
    """Proves `verified` is a real check, not a constant True."""
    db_path = tmp_path / "original.db"
    storage_root = tmp_path / "storage"
    backup_dir = tmp_path / "backups"

    engine, Session = _sqlite_engine_and_session(db_path)
    session = Session()
    org_id = str(uuid.uuid4())
    session.add(Organization(id=org_id, name="Org Backup", slug=f"org-backup-{uuid.uuid4().hex[:8]}"))
    session.flush()
    session.add(Campaign(id=str(uuid.uuid4()), name="Campanha 1", organization_id=org_id))
    session.commit()
    session.close()
    engine.dispose()

    database_url = f"sqlite:///{db_path}"
    result = create_backup(database_url=database_url, storage_root=storage_root, backup_dir=backup_dir)

    import json

    from app.services.backup.backup_service import MANIFEST_FILENAME
    import tarfile

    # Tamper with the manifest inside the tarball to claim more rows than
    # actually exist in the dump — the restore must catch this, not trust it.
    extract_dir = tmp_path / "tamper"
    with tarfile.open(result.path, "r:gz") as tar:
        tar.extractall(extract_dir, filter="data")
    manifest_path = extract_dir / MANIFEST_FILENAME
    manifest_data = json.loads(manifest_path.read_text())
    manifest_data["table_row_counts"]["campaigns"] = 999
    manifest_path.write_text(json.dumps(manifest_data))

    tampered_path = tmp_path / "tampered-backup.tar.gz"
    with tarfile.open(tampered_path, "w:gz") as tar:
        for item in extract_dir.iterdir():
            tar.add(item, arcname=item.name)

    db_path.unlink()
    restore_result = restore_backup(backup_path=tampered_path, database_url=database_url, storage_root=storage_root)

    assert restore_result.verified is False
    assert restore_result.restored_table_row_counts["campaigns"] == 1
    assert restore_result.manifest.table_row_counts["campaigns"] == 999


# --- Postgres: full round trip against a real instance ---------------------


@pytest.fixture()
def pg_database():
    psycopg = pytest.importorskip("psycopg")
    admin = psycopg.connect(PG_ADMIN_URL, autocommit=True)
    admin.execute(f'DROP DATABASE IF EXISTS "{PG_TEST_DB}"')
    admin.execute(f'CREATE DATABASE "{PG_TEST_DB}"')
    admin.close()
    yield PG_TEST_URL
    admin = psycopg.connect(PG_ADMIN_URL, autocommit=True)
    admin.execute(f'DROP DATABASE IF EXISTS "{PG_TEST_DB}"')
    admin.close()


def test_postgres_backup_then_schema_wipe_then_restore_recovers_data(tmp_path: Path, pg_database):
    import psycopg
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base

    database_url = pg_database
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org_id = str(uuid.uuid4())
    session.add(Organization(id=org_id, name="Org Postgres", slug=f"org-pg-{uuid.uuid4().hex[:8]}"))
    session.flush()
    campaign_id = str(uuid.uuid4())
    session.add(Campaign(id=campaign_id, name="Campanha Postgres", organization_id=org_id))
    session.flush()
    session.add(
        Document(
            id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            original_filename="recibo.pdf",
            mime_type="application/pdf",
            file_extension="pdf",
            file_size_bytes=100,
            sha256_hash=uuid.uuid4().hex,
            original_path="originals/recibo.pdf",
        )
    )
    session.commit()
    session.close()
    engine.dispose()

    storage_root = tmp_path / "storage"
    (storage_root / "originals").mkdir(parents=True)
    (storage_root / "processed").mkdir(parents=True)
    backup_dir = tmp_path / "backups"

    result = create_backup(database_url=database_url, storage_root=storage_root, backup_dir=backup_dir)
    assert result.manifest.table_row_counts["campaigns"] == 1
    assert result.manifest.table_row_counts["documents"] == 1

    # Genuinely destroy the schema — a real "the database is gone" scenario.
    admin_conn = psycopg.connect(f"postgresql://postgres:postgres@localhost:5432/{PG_TEST_DB}", autocommit=True)
    admin_conn.execute("DROP SCHEMA public CASCADE")
    admin_conn.execute("CREATE SCHEMA public")
    admin_conn.close()

    restore_result = restore_backup(backup_path=result.path, database_url=database_url, storage_root=storage_root)

    assert restore_result.verified is True
    assert restore_result.restored_table_row_counts["campaigns"] == 1
    assert restore_result.restored_table_row_counts["documents"] == 1

    verify_conn = psycopg.connect(f"postgresql://postgres:postgres@localhost:5432/{PG_TEST_DB}")
    row = verify_conn.execute("SELECT name FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    verify_conn.close()
    assert row == ("Campanha Postgres",)
