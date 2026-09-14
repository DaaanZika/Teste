#!/bin/sh
# Runs migrations before the app starts — the container is the one place
# where "run alembic manually" would otherwise be forgotten. Safe to run
# on every start: Alembic no-ops when the schema is already current.
set -e

echo "Running database migrations..."
alembic upgrade head

exec "$@"
