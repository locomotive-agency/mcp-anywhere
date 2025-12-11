"""add user tool permission

Revision ID: 004
Revises: 003
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, Sequence[str], None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_tool_permissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('tool_id', sa.String(length=8), nullable=False),
    sa.Column('permission', sa.String(length=10), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['tool_id'], ['mcp_server_tools.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'tool_id', name='uq_user_tool'),
    if_not_exists=True
    )

    with op.batch_alter_table('user_tool_permissions', schema=None) as batch_op:
        batch_op.create_index('idx_user_tool_permissions_tool', ['tool_id'], unique=False)
        batch_op.create_index('idx_user_tool_permissions_user', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('user_tool_permissions', schema=None) as batch_op:
        batch_op.drop_index('idx_user_tool_permissions_user')
        batch_op.drop_index('idx_user_tool_permissions_tool')

    op.drop_table('user_tool_permissions')
