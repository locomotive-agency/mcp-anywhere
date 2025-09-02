#!/bin/sh
set -e

# Execute the command passed to the container (e.g., gunicorn)
exec "$@"