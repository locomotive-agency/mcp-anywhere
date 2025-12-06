#!/bin/sh
set -e

# Manage Migrations
if sqlite3 .data/mcp_anywhere.db "SELECT * FROM alembic_version;" ; then
    echo ">>> Migration database exists, running migrations..."
    alembic upgrade head
else
    if sqlite3 .data/mcp_anywhere.db "SELECT * FROM users;" ; then
      echo ">>> User database exists, skipping initial migration..."
      alembic stamp 001 # skip initial migration
      alembic upgrade head
    else
      echo ">>> User database not found. Continuing"
  fi
fi

# Execute the command passed to the container (e.g., gunicorn)
exec "$@"