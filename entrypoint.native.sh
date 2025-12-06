#!/bin/sh
set -e

# Manage Migrations
alembic upgrade head

# Execute the command passed to the container (e.g., gunicorn)
exec "$@"