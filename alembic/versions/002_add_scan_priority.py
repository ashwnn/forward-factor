"""Add scan_priority to user_settings.

Revision ID: 002
Revises: 001
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_settings', sa.Column('scan_priority', sa.String(), nullable=False, server_default='standard'))


def downgrade() -> None:
    op.drop_column('user_settings', 'scan_priority')
