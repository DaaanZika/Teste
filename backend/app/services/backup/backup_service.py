"""Full-system backup/restore: database dump + document storage archive
(PROMPT 3 FASE K).

A backup's integrity is checked two ways: a manifest recording every
table's row count at backup time (so `restore_backup` can immediately
flag a truncated/corrupt dump instead of silently "succeeding" with less
data than it started with — see `RestoreResult.verified`); and, the real
proof, `tests/test_backup_restore.py` actually restores a real backup
into a scratch database/storage directory and asserts the specific rows
come back correctly — not just that a file was written.

Postgres uses `pg_dump --format=custom` / `pg_restore` (the client tools
are installed in the Docker image — see backend/Dockerfile). SQLite uses
the standard library's own `sqlite3.Connection.backup()`, the
crash-consistent way to copy a SQLite database without depending on the
`sqlite3` CLI being installed (it often isn't, on a minimal image).

Only `storage/originals` and `storage/processed` are archived —
`storage/temporary` is transient by design (files there are deleted after
use, see app/integrations/storage_adapter.py) and backing it up would
only ever restore garbage.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import tarfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text

MANIFEST_FILENAME = "manifest.json"
DATABASE_DUMP_FILENAME_PG = "database.dump"
DATABASE_DUMP_FILENAME_SQLITE = "database.sqlite3"
STORAGE_ARCHIVE_FILENAME = "storage.tar.gz"
BACKUP_FORMAT_VERSION = 1

BACKED_UP_STORAGE_SUBDIRS = ("originals", "processed")


class UnsupportedDatabaseError(Exception):
    pass


class BackupFailedError(Exception):
    pass


class RestoreFailedError(Exception):
    pass


def _dialect_from_url(database_url: str) -> str:
    scheme = urlparse(database_url).scheme
    if scheme.startswith("postgresql"):
        return "postgresql"
    if scheme.startswith("sqlite"):
        return "sqlite"
    raise UnsupportedDatabaseError(f"Backup/restore não implementado para '{database_url.split(':')[0]}'.")


def _libpq_url(database_url: str) -> str:
    """pg_dump/pg_restore speak libpq URIs (`postgresql://...`), not
    SQLAlchemy's driver-qualified scheme (`postgresql+psycopg://...`) —
    passing the latter makes pg_dump silently fail to parse it and fall
    back to a default local connection as the current OS user instead of
    erroring clearly, which is not hypothetical: it's exactly what
    happened the first time this was tried against a real Postgres
    instance (`role "root" does not exist`), not a defensive guess."""
    _, _, rest = database_url.partition("://")
    return f"postgresql://{rest}"


def _sqlite_path_from_url(database_url: str) -> Path:
    # sqlite:///relative/path.db (3 slashes) or sqlite:////absolute/path.db (4 slashes)
    if database_url.startswith("sqlite:////"):
        return Path("/" + database_url.split("sqlite:////", 1)[1])
    return Path(database_url.split("sqlite:///", 1)[1])


@dataclass
class BackupManifest:
    backup_format_version: int
    created_at: str
    database_dialect: str
    table_row_counts: dict[str, int]


@dataclass
class BackupResult:
    path: Path
    manifest: BackupManifest


@dataclass
class RestoreResult:
    manifest: BackupManifest
    restored_table_row_counts: dict[str, int]
    verified: bool


def _table_row_counts(database_url: str) -> dict[str, int]:
    """Table names come from reflecting the database's own catalog
    (`inspector.get_table_names()`), never from external input — safe to
    interpolate into the COUNT query below."""
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        counts: dict[str, int] = {}
        with engine.connect() as conn:
            for table_name in sorted(inspector.get_table_names()):
                if table_name == "alembic_version":
                    continue
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))  # noqa: S608 - table_name is DB-reflected, not user input
                counts[table_name] = result.scalar_one()
        return counts
    finally:
        engine.dispose()


def _dump_database(database_url: str, dialect: str, destination_dir: Path) -> None:
    if dialect == "postgresql":
        dump_path = destination_dir / DATABASE_DUMP_FILENAME_PG
        result = subprocess.run(
            ["pg_dump", "--format=custom", "--file", str(dump_path), _libpq_url(database_url)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise BackupFailedError(f"pg_dump falhou: {result.stderr}")
    else:
        src_path = _sqlite_path_from_url(database_url)
        if not src_path.exists():
            # sqlite3.connect() silently CREATES an empty file for a path
            # that doesn't exist yet — without this check, backing up a
            # not-yet-migrated or misconfigured database would silently
            # produce a "successful" backup of nothing instead of failing
            # loudly (caught by actually running this against a deleted
            # database file, not assumed).
            raise BackupFailedError(f"Banco de dados SQLite não encontrado: {src_path}")
        dest_path = destination_dir / DATABASE_DUMP_FILENAME_SQLITE
        source_conn = sqlite3.connect(str(src_path))
        try:
            dest_conn = sqlite3.connect(str(dest_path))
            try:
                source_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            source_conn.close()


def _restore_database(database_url: str, dialect: str, source_dir: Path) -> None:
    if dialect == "postgresql":
        dump_path = source_dir / DATABASE_DUMP_FILENAME_PG
        result = subprocess.run(
            ["pg_restore", "--clean", "--if-exists", "--no-owner", "--dbname", _libpq_url(database_url), str(dump_path)],
            capture_output=True,
            text=True,
        )
        # pg_restore commonly exits 1 on harmless warnings (e.g. trying to
        # drop an extension/role it doesn't own) even on an otherwise
        # complete restore — treat that as non-fatal here and let the
        # caller's row-count comparison against the manifest be the real
        # verification, not this exit code alone.
        if result.returncode not in (0, 1):
            raise RestoreFailedError(f"pg_restore falhou: {result.stderr}")
    else:
        dump_path = source_dir / DATABASE_DUMP_FILENAME_SQLITE
        if not dump_path.exists():
            raise RestoreFailedError(f"Backup não contém {DATABASE_DUMP_FILENAME_SQLITE}.")
        dest_path = _sqlite_path_from_url(database_url)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        source_conn = sqlite3.connect(str(dump_path))
        try:
            dest_conn = sqlite3.connect(str(dest_path))
            try:
                source_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            source_conn.close()


def create_backup(*, database_url: str, storage_root: Path, backup_dir: Path) -> BackupResult:
    dialect = _dialect_from_url(database_url)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    work_dir = backup_dir / f"_work-{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        _dump_database(database_url, dialect, work_dir)

        with tarfile.open(work_dir / STORAGE_ARCHIVE_FILENAME, "w:gz") as tar:
            for subdir in BACKED_UP_STORAGE_SUBDIRS:
                source = storage_root / subdir
                if source.exists():
                    tar.add(source, arcname=subdir)

        manifest = BackupManifest(
            backup_format_version=BACKUP_FORMAT_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(),
            database_dialect=dialect,
            table_row_counts=_table_row_counts(database_url),
        )
        (work_dir / MANIFEST_FILENAME).write_text(json.dumps(asdict(manifest), indent=2, ensure_ascii=False))

        backup_dir.mkdir(parents=True, exist_ok=True)
        final_path = backup_dir / f"campanhas-backup-{timestamp}.tar.gz"
        with tarfile.open(final_path, "w:gz") as tar:
            for item in sorted(work_dir.iterdir()):
                tar.add(item, arcname=item.name)

        return BackupResult(path=final_path, manifest=manifest)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def restore_backup(*, backup_path: Path, database_url: str, storage_root: Path) -> RestoreResult:
    work_dir = backup_path.parent / f"_restore-work-{backup_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(work_dir, filter="data")

        manifest_path = work_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            raise RestoreFailedError(f"Backup {backup_path} não contém {MANIFEST_FILENAME}.")
        manifest = BackupManifest(**json.loads(manifest_path.read_text()))

        _restore_database(database_url, manifest.database_dialect, work_dir)

        storage_archive_path = work_dir / STORAGE_ARCHIVE_FILENAME
        if storage_archive_path.exists():
            for subdir in BACKED_UP_STORAGE_SUBDIRS:
                (storage_root / subdir).mkdir(parents=True, exist_ok=True)
            with tarfile.open(storage_archive_path, "r:gz") as tar:
                tar.extractall(storage_root, filter="data")

        restored_counts = _table_row_counts(database_url)
        verified = restored_counts == manifest.table_row_counts

        return RestoreResult(manifest=manifest, restored_table_row_counts=restored_counts, verified=verified)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
