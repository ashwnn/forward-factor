"""regenerate link codes to 16 chars

Revision ID: 20251127_1600
Revises: 20251128_0000
Create Date: 2025-11-27 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import secrets


# revision identifiers, used by Alembic.
revision = '20251127_1600'
down_revision = '20251128_0000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Regenerate link codes to be 16 characters for all users who have 8-char codes."""
    connection = op.get_bind()
    
    # Get all users with link codes that are less than 16 characters
    result = connection.execute(
        sa.text("SELECT id, link_code FROM users WHERE link_code IS NOT NULL AND LENGTH(link_code) < 16")
    )
    
    users_to_update = result.fetchall()
    
    # Update each user with a new 16-character link code
    for user_id, old_code in users_to_update:
        new_code = secrets.token_hex(8)  # 8 bytes = 16 hex characters
        connection.execute(
            sa.text("UPDATE users SET link_code = :new_code WHERE id = :user_id"),
            {"new_code": new_code, "user_id": user_id}
        )
    
    print(f"Updated {len(users_to_update)} users with new 16-character link codes")


def downgrade() -> None:
    """No downgrade needed - we can't revert to shorter codes without breaking functionality."""
    pass
