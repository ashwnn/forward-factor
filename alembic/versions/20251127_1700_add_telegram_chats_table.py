"""add telegram_chats table

Revision ID: 20251127_1700
Revises: 20251127_1600
Create Date: 2025-11-27 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251127_1700'
down_revision = '20251127_1600'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create telegram_chats table for multiple chats per user."""
    op.create_table(
        'telegram_chats',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('chat_id', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_telegram_chats_user_id', 'telegram_chats', ['user_id'])
    op.create_index('ix_telegram_chats_chat_id', 'telegram_chats', ['chat_id'], unique=True)
    
    # Migrate existing telegram_chat_id data to new table
    # Note: We can't migrate first_name/last_name since they weren't stored before
    # Users will need to re-link their accounts to get proper names
    connection = op.get_bind()
    result = connection.execute(
        sa.text("""
            SELECT id, telegram_chat_id, telegram_username, created_at 
            FROM users 
            WHERE telegram_chat_id IS NOT NULL
        """)
    )
    
    users_with_chats = result.fetchall()
    
    # Insert existing chat IDs into new table with placeholder first_name
    for user_id, chat_id, username, created_at in users_with_chats:
        connection.execute(
            sa.text("""
                INSERT INTO telegram_chats (id, user_id, chat_id, first_name, username, linked_at)
                VALUES (gen_random_uuid()::text, :user_id, :chat_id, :first_name, :username, :linked_at)
            """),
            {
                "user_id": user_id, 
                "chat_id": chat_id, 
                "first_name": username or "User",  # Use username or "User" as placeholder
                "username": username, 
                "linked_at": created_at
            }
        )
    
    print(f"Migrated {len(users_with_chats)} existing Telegram chats to telegram_chats table")
    
    # Drop the old telegram_chat_id and telegram_username columns from users table
    op.drop_index('ix_users_telegram_chat_id', table_name='users')
    op.drop_index('ix_users_telegram_username', table_name='users')
    op.drop_column('users', 'telegram_chat_id')
    op.drop_column('users', 'telegram_username')


def downgrade() -> None:
    """Drop telegram_chats table and restore old columns."""
    # Restore old columns to users table
    op.add_column('users', sa.Column('telegram_chat_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('telegram_username', sa.String(), nullable=True))
    op.create_index('ix_users_telegram_chat_id', 'users', ['telegram_chat_id'], unique=True)
    op.create_index('ix_users_telegram_username', 'users', ['telegram_username'])
    
    # Drop telegram_chats table
    op.drop_index('ix_telegram_chats_chat_id', table_name='telegram_chats')
    op.drop_index('ix_telegram_chats_user_id', table_name='telegram_chats')
    op.drop_table('telegram_chats')
