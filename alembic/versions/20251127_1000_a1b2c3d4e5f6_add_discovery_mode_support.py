"""Add discovery mode support

Revision ID: a1b2c3d4e5f6
Revises: e9dc54207ed6
Create Date: 2025-11-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e9dc54207ed6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add discovery_mode column to user_settings
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('discovery_mode', sa.Boolean(), nullable=False, server_default='0'))
    
    # Add is_discovery column to signals
    with op.batch_alter_table('signals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_discovery', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove is_discovery column from signals
    with op.batch_alter_table('signals', schema=None) as batch_op:
        batch_op.drop_column('is_discovery')
    
    # Remove discovery_mode column from user_settings
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.drop_column('discovery_mode')
