#!/usr/bin/env bash
# Restores a backup created by scripts/backup.sh. Exits non-zero if the
# restored row counts don't match the backup's own manifest (see
# backend/BACKUP.md — this is what makes "restore" here mean "actually
# verified", not just "a command was run").
#
# Usage:
#   ./scripts/restore.sh backend/backups/campanhas-backup-20260101-000000.tar.gz
#   docker compose exec backend python -m app.services.backup.cli restore <path>
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 <caminho-do-backup.tar.gz>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

# Resolve to an absolute path before cd'ing into backend/ — a relative
# path like "backend/backups/x.tar.gz" (natural when run from the repo
# root, as in the usage example above) would otherwise be looked up
# relative to backend/ instead of the caller's own working directory.
if [ -d "$(dirname "$1")" ]; then
  BACKUP_PATH="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
else
  BACKUP_PATH="$1"
fi

cd "$BACKEND_DIR"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

exec "$PYTHON" -m app.services.backup.cli restore "$BACKUP_PATH"
