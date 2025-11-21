"""Initial migration - create all tables.

Revision ID: 001
Revises: 
Create Date: 2025-11-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('telegram_chat_id', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
    )
    op.create_index('ix_users_telegram_chat_id', 'users', ['telegram_chat_id'])
    
    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ff_threshold', sa.Float(), nullable=False),
        sa.Column('dte_pairs', postgresql.JSON(), nullable=True),
        sa.Column('vol_point', sa.String(), nullable=False),
        sa.Column('min_open_interest', sa.Integer(), nullable=False),
        sa.Column('min_volume', sa.Integer(), nullable=False),
        sa.Column('max_bid_ask_pct', sa.Float(), nullable=False),
        sa.Column('sigma_fwd_floor', sa.Float(), nullable=False),
        sa.Column('stability_scans', sa.Integer(), nullable=False),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False),
        sa.Column('quiet_hours', postgresql.JSON(), nullable=True),
        sa.Column('preferred_structure', sa.String(), nullable=False),
        sa.Column('timezone', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create master_tickers table
    op.create_table(
        'master_tickers',
        sa.Column('ticker', sa.String(), primary_key=True),
        sa.Column('active_subscriber_count', sa.Integer(), nullable=False),
        sa.Column('last_scan_at', sa.DateTime(), nullable=True),
        sa.Column('scan_tier', sa.String(), nullable=False),
    )
    op.create_index('ix_master_tickers_ticker', 'master_tickers', ['ticker'])
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticker', sa.String(), primary_key=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'ticker', name='uq_user_ticker'),
    )
    op.create_index('ix_subscriptions_ticker', 'subscriptions', ['ticker'])
    
    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('as_of_ts', sa.DateTime(), nullable=False),
        sa.Column('front_expiry', sa.Date(), nullable=False),
        sa.Column('back_expiry', sa.Date(), nullable=False),
        sa.Column('front_dte', sa.Integer(), nullable=False),
        sa.Column('back_dte', sa.Integer(), nullable=False),
        sa.Column('front_iv', sa.Float(), nullable=False),
        sa.Column('back_iv', sa.Float(), nullable=False),
        sa.Column('sigma_fwd', sa.Float(), nullable=False),
        sa.Column('ff_value', sa.Float(), nullable=False),
        sa.Column('vol_point', sa.String(), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('reason_codes', postgresql.JSON(), nullable=True),
        sa.Column('dedupe_key', sa.String(), nullable=False, unique=True),
        sa.Column('underlying_price', sa.Float(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
    )
    op.create_index('ix_signals_ticker', 'signals', ['ticker'])
    op.create_index('ix_signals_as_of_ts', 'signals', ['as_of_ts'])
    op.create_index('ix_signals_ff_value', 'signals', ['ff_value'])
    op.create_index('ix_signals_dedupe_key', 'signals', ['dedupe_key'])
    
    # Create option_chain_snapshots table
    op.create_table(
        'option_chain_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('as_of_ts', sa.DateTime(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('underlying_price', sa.Float(), nullable=True),
        sa.Column('raw_payload', postgresql.JSON(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
    )
    op.create_index('ix_option_chain_snapshots_ticker', 'option_chain_snapshots', ['ticker'])
    
    # Create signal_user_decisions table
    op.create_table(
        'signal_user_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('decision_ts', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_signal_user_decisions_signal_id', 'signal_user_decisions', ['signal_id'])
    op.create_index('ix_signal_user_decisions_user_id', 'signal_user_decisions', ['user_id'])


def downgrade() -> None:
    op.drop_table('signal_user_decisions')
    op.drop_table('option_chain_snapshots')
    op.drop_table('signals')
    op.drop_table('subscriptions')
    op.drop_table('master_tickers')
    op.drop_table('user_settings')
    op.drop_table('users')
