"""Rename metadata column to decision_metadata.

Revision ID: 004
Revises: 003
Create Date: 2025-11-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('signal_user_decisions', 'metadata', new_column_name='decision_metadata')


def downgrade() -> None:
    op.alter_column('signal_user_decisions', 'decision_metadata', new_column_name='metadata')
