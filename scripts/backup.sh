#!/usr/bin/env bash
# Creates a full backup (database + storage/originals + storage/processed)
# via the backend's own backup service. See backend/BACKUP.md for the full
# procedure, including how a restore is actually verified.
#
# Usage:
#   ./scripts/backup.sh                 # runs locally (backend/.venv or system python)
#   docker compose exec backend python -m app.services.backup.cli backup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

cd "$BACKEND_DIR"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

exec "$PYTHON" -m app.services.backup.cli backup
