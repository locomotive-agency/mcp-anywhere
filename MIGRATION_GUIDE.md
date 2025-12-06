# Database Migration Guide

This guide explains how to manage database schema changes in MCP Anywhere using Alembic.

## Overview

MCP Anywhere now uses Alembic for database migrations. This provides:
- Version-controlled schema changes
- Safe upgrades for existing installations
- Rollback capability if needed
- Better handling of schema evolution

## For New Installations

New installations will automatically get the latest schema when the application starts. No manual migration is needed.

## For Existing Installations

If you're upgrading from a version without the `role` field in the users table, follow these steps:

### Step 1: Install Alembic (if not already installed)

The dependency should already be in pyproject.toml. If you need to install manually:

```bash
pip install alembic
```

### Step 2: Check Your Database Status

First, let's see what state your database is in:

```bash
# Go to your MCP Anywhere directory
cd /path/to/mcp-anywhere

# Check if you have the alembic_version table
sqlite3 instance/mcp_anywhere.db "SELECT * FROM alembic_version;"
```

### Step 3: Upgrade Your Database

#### If you have NO existing data (fresh install)
Just run the migrations:

```bash
alembic upgrade head
```

#### If you have EXISTING data (upgrading from older version)

**Option A: Your database already has the role field (created via create_all)**

If your database already has all the tables with the `role` field, stamp it as migrated:

```bash
# Mark the database as being at the latest migration
alembic stamp head
```

This tells Alembic "the database is already up to date, don't try to create tables."

**Option B: Your database is missing the role field**

If your database has the old schema without the `role` field:

```bash
# First, stamp it as having the initial schema
alembic stamp 001

# Then upgrade to add the role field
alembic upgrade head
```

This will:
1. Mark your database as having migration 001 (initial schema)
2. Apply migration 002 (adds the role field)
3. Set the admin user's role to 'admin'
4. All other users will default to 'user' role

## Verifying the Migration

After running migrations, verify the role field exists:

```bash
sqlite3 instance/mcp_anywhere.db "PRAGMA table_info(users);"
```

You should see a `role` column in the output.

## Managing Future Schema Changes

### Creating a New Migration

When you modify database models:

```bash
# Auto-generate a migration based on model changes
alembic revision --autogenerate -m "description of changes"

# Review the generated migration in alembic/versions/
# Edit if needed

# Apply the migration
alembic upgrade head
```

### Rolling Back a Migration

If you need to rollback:

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade 001

# Rollback all migrations
alembic downgrade base
```

### Checking Migration Status

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic heads
```

## Migration Files

Migrations are located in `alembic/versions/`:

- `001_initial_schema.py` - Initial database schema (all tables except role field)
- `002_add_user_roles.py` - Adds the role field to users table

## Troubleshooting

### Error: "table already exists"

This means you're trying to create tables that already exist. Use `alembic stamp head` instead of `alembic upgrade head`.

### Error: "column role already exists"

This means the role field already exists in your database. Use `alembic stamp head` to mark migrations as complete.

### Database is corrupted or in unknown state

As a last resort, you can:

1. Backup your database:
   ```bash
   cp instance/mcp_anywhere.db instance/mcp_anywhere.db.backup
   ```

2. Export your data if needed

3. Delete the database and let it recreate:
   ```bash
   rm instance/mcp_anywhere.db
   alembic upgrade head
   ```

## Production Recommendations

1. **Always backup** your database before running migrations
2. **Test migrations** in a development environment first
3. **Review auto-generated migrations** - Alembic's autogenerate is helpful but not perfect
4. **Use version control** for migration files
5. **Document complex migrations** in the migration file comments

## Automatic vs Manual Migrations

### Automatic (create_all) - Current Default

The application currently still uses `Base.metadata.create_all()` for automatic table creation. This is convenient for development but not recommended for production.

### Manual (Alembic) - Recommended for Production

For production deployments, it's better to:

1. Remove the `create_all()` call from `database.py`
2. Always use `alembic upgrade head` to manage schema
3. Include migration steps in your deployment process

To switch to manual mode, modify `src/mcp_anywhere/database.py` and remove/comment out:

```python
# Create tables using SQLAlchemy metadata
async with self._engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

Then rely on Alembic migrations exclusively.
