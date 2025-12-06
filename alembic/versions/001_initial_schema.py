"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    # MCP Servers table
    op.create_table('mcp_servers',
    sa.Column('id', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('github_url', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('runtime_type', sa.String(length=20), nullable=False),
    sa.Column('install_command', sa.Text(), nullable=False),
    sa.Column('start_command', sa.Text(), nullable=False),
    sa.Column('env_variables', sa.JSON(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('build_status', sa.String(length=20), nullable=False),
    sa.Column('build_error', sa.Text(), nullable=True),
    sa.Column('image_tag', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )

    # MCP Server Tools table
    op.create_table('mcp_server_tools',
    sa.Column('id', sa.String(length=8), nullable=False),
    sa.Column('server_id', sa.String(length=8), nullable=False),
    sa.Column('tool_name', sa.String(length=100), nullable=False),
    sa.Column('tool_description', sa.Text(), nullable=True),
    sa.Column('tool_schema', sa.JSON(), nullable=True),
    sa.Column('is_enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['server_id'], ['mcp_servers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # MCP Server Secret Files table
    op.create_table('mcp_server_secret_files',
    sa.Column('id', sa.String(length=8), nullable=False),
    sa.Column('server_id', sa.String(length=8), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('stored_filename', sa.String(length=255), nullable=False),
    sa.Column('file_type', sa.String(length=50), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('env_var_name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['server_id'], ['mcp_servers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Users table (without role field initially)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )

    # OAuth Clients table
    op.create_table('oauth_clients',
    sa.Column('client_id', sa.String(length=48), nullable=False),
    sa.Column('client_secret', sa.String(length=120), nullable=False),
    sa.Column('client_name', sa.String(length=100), nullable=False),
    sa.Column('redirect_uris', sa.Text(), nullable=False),
    sa.Column('default_scopes', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('client_id')
    )

    # OAuth Tokens table
    op.create_table('oauth_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.String(length=48), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_type', sa.String(length=40), nullable=False),
    sa.Column('access_token', sa.String(length=255), nullable=False),
    sa.Column('refresh_token', sa.String(length=255), nullable=True),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('is_revoked', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['oauth_clients.client_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('access_token')
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('oauth_tokens')
    op.drop_table('oauth_clients')
    op.drop_table('users')
    op.drop_table('mcp_server_secret_files')
    op.drop_table('mcp_server_tools')
    op.drop_table('mcp_servers')
