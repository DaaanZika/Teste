"""app/services/backup/cli.py — thin wrapper around backup_service, tested
against a real SQLite round trip (not mocked) plus the error-path exit
codes a cron job or operator would rely on."""
from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import Settings
from app.models.campaign import Campaign
from app.models.organization import Organization
from app.services.backup import cli as backup_cli


def _settings_for(tmp_path: Path) -> Settings:
    db_path = tmp_path / "app.db"
    storage_root = tmp_path / "storage"
    (storage_root / "originals").mkdir(parents=True)
    (storage_root / "processed").mkdir(parents=True)
    (storage_root / "temporary").mkdir(parents=True)
    return Settings(
        database_url=f"sqlite:///{db_path}",
        storage_root=storage_root,
        storage_originals_dir=storage_root / "originals",
        storage_processed_dir=storage_root / "processed",
        storage_temporary_dir=storage_root / "temporary",
    )


def test_backup_then_restore_via_cli_round_trip(tmp_path, monkeypatch, capsys):
    settings = _settings_for(tmp_path)
    monkeypatch.setattr(backup_cli, "get_settings", lambda: settings)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    org_id = str(uuid.uuid4())
    session.add(Organization(id=org_id, name="Org CLI", slug=f"org-cli-{uuid.uuid4().hex[:8]}"))
    session.flush()
    session.add(Campaign(id=str(uuid.uuid4()), name="Campanha CLI", organization_id=org_id))
    session.commit()
    session.close()
    engine.dispose()

    exit_code = backup_cli.cmd_backup()
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Backup criado" in out

    backups = list((tmp_path / "backups").glob("campanhas-backup-*.tar.gz"))
    assert len(backups) == 1

    exit_code = backup_cli.cmd_list()
    assert exit_code == 0
    assert str(backups[0]) in capsys.readouterr().out

    # Destroy the database for real before restoring.
    (tmp_path / "app.db").unlink()

    exit_code = backup_cli.cmd_restore(str(backups[0]))
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Restauração concluída e verificada" in out
    assert (tmp_path / "app.db").exists()


def test_restore_missing_file_returns_error_exit_code(tmp_path, monkeypatch, capsys):
    settings = _settings_for(tmp_path)
    monkeypatch.setattr(backup_cli, "get_settings", lambda: settings)

    exit_code = backup_cli.cmd_restore(str(tmp_path / "does-not-exist.tar.gz"))
    assert exit_code == 1
    assert "não encontrado" in capsys.readouterr().err


def test_list_with_no_backups_yet(tmp_path, monkeypatch, capsys):
    settings = _settings_for(tmp_path)
    monkeypatch.setattr(backup_cli, "get_settings", lambda: settings)

    exit_code = backup_cli.cmd_list()
    assert exit_code == 0
    assert "Nenhum backup encontrado" in capsys.readouterr().out
