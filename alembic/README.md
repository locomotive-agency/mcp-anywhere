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
# If your database already has the role field
alembic stamp head

# If your database is missing the role field
alembic stamp 001
alembic upgrade head
```

See [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) for detailed instructions.

## Migration Files

- `001_initial_schema.py` - Base schema (all tables without role field)
- `002_add_user_roles.py` - Adds user role field (admin/user)

## Configuration

- `alembic.ini` - Alembic configuration file
- `env.py` - Migration environment setup (async SQLAlchemy support)
- `script.py.mako` - Template for new migration files
