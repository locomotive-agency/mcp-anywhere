"""Add tool capability

Revision ID: 003
Revises: 002
Create Date: 2025-12-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

table = "mcp_server_tools"

def upgrade() -> None:
    """Add capability column to table."""
    # Using batch mode for SQLite compatibility
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.add_column(sa.Column('tool_capability', sa.String(length=20), nullable=False, server_default='read'))


def downgrade() -> None:
    """Remove tool_capability column from table."""
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.drop_column('tool_capability')