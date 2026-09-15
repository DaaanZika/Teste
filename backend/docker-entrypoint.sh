#!/bin/sh
# Runs migrations before the app starts — the container is the one place
# where "run alembic manually" would otherwise be forgotten. Safe to run
# on every start: Alembic no-ops when the schema is already current.
set -e

echo "Running database migrations..."
alembic upgrade head

# No-op unless SUPER_ADMIN_BOOTSTRAP_EMAIL/PASSWORD are set, and no-op again
# once a SUPER_ADMIN already exists (see app/services/admin/bootstrap.py) —
# safe to run on every start, same reasoning as the migration above.
python -m app.services.admin.bootstrap

exec "$@"
