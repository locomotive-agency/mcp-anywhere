"""Add user roles

Revision ID: 002
Revises: 001
Create Date: 2025-12-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role column to users table."""
    # Using batch mode for SQLite compatibility
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Add role column with default value 'user'
        batch_op.add_column(
            sa.Column('role', sa.String(length=20), nullable=False, server_default='user')
        )

    # Update existing admin user to have admin role
    op.execute(
        """
        UPDATE users
        SET role = 'admin'
        WHERE username = 'admin'
        """
    )


def downgrade() -> None:
    """Remove role column from users table."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('role')
