"""Add web authentication fields to users table

Revision ID: 003_add_web_auth
Revises: 002_add_scan_priority
Create Date: 2025-11-21 11:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_web_auth'
down_revision = '002_add_scan_priority'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add web authentication fields to users table."""
    # Make telegram_chat_id nullable (for web-only users)
    op.alter_column('users', 'telegram_chat_id',
                    existing_type=sa.String(),
                    nullable=True)
    
    # Add email field (unique, nullable, indexed)
    op.add_column('users', sa.Column('email', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Add password_hash field (nullable)
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=True))
    
    # Add telegram_username field (nullable, indexed)
    op.add_column('users', sa.Column('telegram_username', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_telegram_username'), 'users', ['telegram_username'], unique=False)
    
    # Add check constraint: at least one of email or telegram_chat_id must be present
    op.create_check_constraint(
        'check_user_identity',
        'users',
        'email IS NOT NULL OR telegram_chat_id IS NOT NULL'
    )


def downgrade() -> None:
    """Remove web authentication fields from users table."""
    # Drop check constraint
    op.drop_constraint('check_user_identity', 'users', type_='check')
    
    # Drop telegram_username column and index
    op.drop_index(op.f('ix_users_telegram_username'), table_name='users')
    op.drop_column('users', 'telegram_username')
    
    # Drop password_hash column
    op.drop_column('users', 'password_hash')
    
    # Drop email column and index
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_column('users', 'email')
    
    # Make telegram_chat_id non-nullable again
    op.alter_column('users', 'telegram_chat_id',
                    existing_type=sa.String(),
                    nullable=False)
