#!/bin/sh
set -e

# Ensure Flask app is discoverable by flask CLI
export FLASK_APP=src.app

echo "Starting docker-entrypoint: running DB migrations if needed"

# If migrations directory doesn't exist, initialize migrations
if [ ! -d "migrations" ]; then
  echo "No migrations directory found — running 'flask db init' and initial migrate"
  flask db init
  flask db migrate -m "initial"
else
  echo "Migrations directory exists — attempting to create new migration"
  # try to create a new migration; ignore failure (e.g., when no changes)
  flask db migrate -m "autoupdate" || true
fi

echo "Upgrading database to latest migration"
flask db upgrade

exec "$@"
