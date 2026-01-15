"""add instance settings

Revision ID: 004
Revises: 003
Create Date: 2025-12-11

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '004'
down_revision: Union[str, Sequence[str], None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('instance_settings',
    sa.Column('key', sa.String(length=100), nullable=False, primary_key=True),
    sa.Column('value', sa.Text, nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text),
    sa.Column('value_type', sa.String(length=20), nullable=False, default="string"),
    sa.Column('updated_at', sa.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    sa.Column('updated_by', sa.String(length=100)),
    if_not_exists=True
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('instance_settings')
