# Alembic Migrations

This directory contains database migrations for MCP Anywhere.

## Quick Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (auto-generate from model changes)
alembic revision --autogenerate -m "description"

# Rollback one migration
alembic downgrade -1

# Show current database version
alembic current

# Show migration history
alembic history
```

## For Existing Databases

If you're upgrading from a version without migrations:

```bash
alembic stamp head

alembic stamp 001
alembic upgrade head
```

## Configuration

- `alembic.ini` - Alembic configuration file
- `env.py` - Migration environment setup (async SQLAlchemy support)
- `script.py.mako` - Template for new migration files
