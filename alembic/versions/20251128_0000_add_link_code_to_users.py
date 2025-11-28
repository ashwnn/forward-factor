"""add link_code to users

Revision ID: 20251128_0000
Revises: 001_initial_schema
Create Date: 2025-11-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251128_0000'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('link_code', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_link_code'), 'users', ['link_code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_link_code'), table_name='users')
    op.drop_column('users', 'link_code')
