"""Add users role type and email

Revision ID: 002
Revises: 001
Create Date: 2025-12-01

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
        batch_op.add_column(sa.Column('role', sa.String(length=20), nullable=False, server_default='user'))
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=False))
        batch_op.add_column(sa.Column('type', sa.String(length=20), nullable=False))

    # Update existing admin user to have admin role
    op.execute(
        """
        UPDATE users
        SET role = 'admin'
        WHERE username = 'admin'
        """
    )

    # Update existing users to be local users
    op.execute(
        """
        UPDATE users
        SET type = 'local'
        """
    )


def downgrade() -> None:
    """Remove role column from users table."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('role')
        batch_op.drop_column('type')
        batch_op.drop_column('email')
