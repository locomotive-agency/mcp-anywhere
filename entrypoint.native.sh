#!/bin/sh
set -e

DB="${DATA_DIR}/mcp_anywhere.db"
DB_BACKUP_FILE="${DATA_DIR}/mcp_anywhere.db.$(date +%s)"

# Backup Database, if exists.
if [ -e ${DB} ]; then
    echo ">>> Running database backup to ${DB_BACKUP_FILE}"
    sqlite3 ${DB} ".backup ${DB_BACKUP_FILE}"
    echo ">>> Database backup complete."
fi

# Manage Migrations
alembic upgrade head

# Execute the command passed to the container (e.g., gunicorn)
exec "$@"