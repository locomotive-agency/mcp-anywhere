#!/bin/sh
set -e

DB=".data/mcp_anywhere.db"
DB_BACKUP_FILE=".data/mcp_anywhere.db.$(date +%s)"

# Backup Database
if [ -e ${DB} ]; then
    echo ">>> Running db backup to ${DB_BACKUP_FILE}"
    sqlite3 ${DB} ".backup ${DB_BACKUP_FILE}"
    echo ">>> backup complete."
fi

# Manage Migrations
alembic upgrade head

# Execute the command passed to the container (e.g., gunicorn)
exec "$@"