"""CLI for on-demand or scheduled backup/restore (PROMPT 3 FASE K).

    python -m app.services.backup.cli backup
    python -m app.services.backup.cli restore backups/campanhas-backup-20260101-000000.tar.gz
    python -m app.services.backup.cli list

Reads DATABASE_URL/STORAGE_ROOT from the normal app settings — no
separate configuration. See backend/BACKUP.md for the full procedure,
including how a restore is actually verified, not just assumed to have
worked.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.backup.backup_service import (
    BackupFailedError,
    RestoreFailedError,
    UnsupportedDatabaseError,
    create_backup,
    restore_backup,
)


def _backup_dir() -> Path:
    settings = get_settings()
    return settings.storage_root.parent / "backups"


def cmd_backup() -> int:
    settings = get_settings()
    try:
        result = create_backup(
            database_url=settings.database_url, storage_root=settings.storage_root, backup_dir=_backup_dir()
        )
    except (BackupFailedError, UnsupportedDatabaseError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print(f"Backup criado: {result.path}")
    print(f"Tabelas: {sum(result.manifest.table_row_counts.values())} linhas em {len(result.manifest.table_row_counts)} tabelas")
    return 0


def cmd_restore(backup_path: str) -> int:
    settings = get_settings()
    path = Path(backup_path)
    if not path.exists():
        print(f"ERRO: arquivo de backup não encontrado: {path}", file=sys.stderr)
        return 1

    try:
        result = restore_backup(backup_path=path, database_url=settings.database_url, storage_root=settings.storage_root)
    except (RestoreFailedError, UnsupportedDatabaseError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    if not result.verified:
        print("AVISO: contagem de linhas após a restauração não bate com o manifesto do backup.", file=sys.stderr)
        print(f"  Esperado: {result.manifest.table_row_counts}", file=sys.stderr)
        print(f"  Obtido:   {result.restored_table_row_counts}", file=sys.stderr)
        return 2

    print(f"Restauração concluída e verificada (backup de {result.manifest.created_at}).")
    print(f"Tabelas: {sum(result.restored_table_row_counts.values())} linhas em {len(result.restored_table_row_counts)} tabelas")
    return 0


def cmd_list() -> int:
    backup_dir = _backup_dir()
    if not backup_dir.exists():
        print("Nenhum backup encontrado (diretório de backups ainda não existe).")
        return 0
    backups = sorted(backup_dir.glob("campanhas-backup-*.tar.gz"))
    if not backups:
        print(f"Nenhum backup encontrado em {backup_dir}.")
        return 0
    for backup in backups:
        print(backup)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup/restore do sistema (banco + documentos)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("backup")
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("backup_path")
    subparsers.add_parser("list")

    args = parser.parse_args()
    configure_logging()

    if args.command == "backup":
        return cmd_backup()
    if args.command == "restore":
        return cmd_restore(args.backup_path)
    if args.command == "list":
        return cmd_list()
    return 1


if __name__ == "__main__":
    sys.exit(main())
