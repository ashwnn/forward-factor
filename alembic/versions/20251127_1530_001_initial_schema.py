"""Initial TimescaleDB schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-11-27 15:30:00.000000

This is the initial migration that sets up the complete database schema
with TimescaleDB hypertables for time-series data.

Tables created:
- users: User accounts (Telegram and web)
- user_settings: User-specific signal detection settings
- subscriptions: User ticker watchlist
- master_tickers: Master ticker registry
- signals: Forward Factor signals (TimescaleDB hypertable)
- option_chain_snapshots: Raw option chain data (TimescaleDB hypertable)
- signal_user_decisions: User actions on signals

TimescaleDB features:
- Hypertables for signals and option_chain_snapshots (1-day chunks)
- Composite primary keys including partitioning column (as_of_ts)
- Compression policies (compress after 7 days)
- Optimized indexes for time-series queries
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial TimescaleDB schema."""
    logger.info("=" * 80)
    logger.info("Creating initial TimescaleDB schema...")
    logger.info("=" * 80)
    
    # Step 1: Enable TimescaleDB extension
    logger.info("Step 1/9: Enabling TimescaleDB extension...")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    logger.info("✓ TimescaleDB extension enabled")
    
    # Step 2: Create users table
    logger.info("Step 2/9: Creating users table...")
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('telegram_chat_id', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('telegram_username', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_telegram_chat_id', 'users', ['telegram_chat_id'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_telegram_username', 'users', ['telegram_username'])
    logger.info("✓ Users table created")
    
    # Step 3: Create user_settings table
    logger.info("Step 3/9: Creating user_settings table...")
    op.create_table(
        'user_settings',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('ff_threshold', sa.Float(), nullable=False),
        sa.Column('dte_pairs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('vol_point', sa.String(), nullable=False),
        sa.Column('min_open_interest', sa.Integer(), nullable=False),
        sa.Column('min_volume', sa.Integer(), nullable=False),
        sa.Column('max_bid_ask_pct', sa.Float(), nullable=False),
        sa.Column('sigma_fwd_floor', sa.Float(), nullable=False),
        sa.Column('stability_scans', sa.Integer(), nullable=False),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False),
        sa.Column('quiet_hours', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('preferred_structure', sa.String(), nullable=False),
        sa.Column('timezone', sa.String(), nullable=False),
        sa.Column('scan_priority', sa.String(), nullable=False),
        sa.Column('discovery_mode', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )
    logger.info("✓ User settings table created")
    
    # Step 4: Create subscriptions table
    logger.info("Step 4/9: Creating subscriptions table...")
    op.create_table(
        'subscriptions',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'ticker'),
        sa.UniqueConstraint('user_id', 'ticker', name='uq_user_ticker')
    )
    op.create_index('ix_subscriptions_ticker', 'subscriptions', ['ticker'])
    logger.info("✓ Subscriptions table created")
    
    # Step 5: Create master_tickers table
    logger.info("Step 5/9: Creating master_tickers table...")
    op.create_table(
        'master_tickers',
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('active_subscriber_count', sa.Integer(), nullable=False),
        sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scan_tier', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('ticker')
    )
    op.create_index('ix_master_tickers_ticker', 'master_tickers', ['ticker'])
    logger.info("✓ Master tickers table created")
    
    # Step 6: Create signals table with composite primary key for TimescaleDB
    logger.info("Step 6/9: Creating signals table (TimescaleDB hypertable)...")
    op.create_table(
        'signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('as_of_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
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
        sa.Column('reason_codes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('dedupe_key', sa.String(), nullable=False),
        sa.Column('is_discovery', sa.Boolean(), nullable=False),
        sa.Column('underlying_price', sa.Float(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        # Composite primary key required for TimescaleDB hypertable
        sa.PrimaryKeyConstraint('id', 'as_of_ts')
    )
    
    # Create indexes before hypertable conversion
    op.create_index('ix_signals_as_of_ts', 'signals', ['as_of_ts'])
    op.create_index('ix_signals_ticker', 'signals', ['ticker'])
    op.create_index('ix_signals_ff_value', 'signals', ['ff_value'])
    op.create_index('ix_signals_dedupe_key', 'signals', ['dedupe_key'])
    
    # Convert to hypertable
    logger.info("Converting signals to hypertable (1-day chunks)...")
    op.execute("""
        SELECT create_hypertable(
            'signals',
            'as_of_ts',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    """)
    
    # Create composite unique index (must include partitioning column)
    logger.info("Creating composite unique index on (dedupe_key, as_of_ts)...")
    op.create_index(
        'ix_signals_dedupe_key_time',
        'signals',
        ['dedupe_key', 'as_of_ts'],
        unique=True,
        postgresql_using='btree'
    )
    
    # Create composite index for common queries
    op.create_index(
        'ix_signals_ticker_time',
        'signals',
        ['ticker', 'as_of_ts'],
        postgresql_using='btree'
    )
    
    # Enable compression
    logger.info("Configuring compression for signals...")
    op.execute("""
        ALTER TABLE signals SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'ticker',
            timescaledb.compress_orderby = 'as_of_ts DESC'
        );
    """)
    op.execute("""
        SELECT add_compression_policy('signals', INTERVAL '7 days');
    """)
    logger.info("✓ Signals table created as hypertable with compression")
    
    # Step 7: Create option_chain_snapshots table with composite primary key
    logger.info("Step 7/9: Creating option_chain_snapshots table (TimescaleDB hypertable)...")
    op.create_table(
        'option_chain_snapshots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('as_of_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('underlying_price', sa.Float(), nullable=True),
        sa.Column('raw_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        # Composite primary key required for TimescaleDB hypertable
        sa.PrimaryKeyConstraint('id', 'as_of_ts')
    )
    
    # Create indexes before hypertable conversion
    op.create_index('ix_option_chain_snapshots_ticker', 'option_chain_snapshots', ['ticker'])
    
    # Convert to hypertable
    logger.info("Converting option_chain_snapshots to hypertable (1-day chunks)...")
    op.execute("""
        SELECT create_hypertable(
            'option_chain_snapshots',
            'as_of_ts',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    """)
    
    # Create composite index for common queries
    op.create_index(
        'ix_option_chain_snapshots_ticker_time',
        'option_chain_snapshots',
        ['ticker', 'as_of_ts'],
        postgresql_using='btree'
    )
    
    # Enable compression
    logger.info("Configuring compression for option_chain_snapshots...")
    op.execute("""
        ALTER TABLE option_chain_snapshots SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'ticker',
            timescaledb.compress_orderby = 'as_of_ts DESC'
        );
    """)
    op.execute("""
        SELECT add_compression_policy('option_chain_snapshots', INTERVAL '7 days');
    """)
    logger.info("✓ Option chain snapshots table created as hypertable with compression")
    
    # Step 8: Create signal_user_decisions table
    logger.info("Step 8/9: Creating signal_user_decisions table...")
    op.create_table(
        'signal_user_decisions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('signal_id', sa.String(), nullable=False),
        sa.Column('signal_as_of_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('decision_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decision_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ['signal_id', 'signal_as_of_ts'],
            ['signals.id', 'signals.as_of_ts'],
            ondelete='CASCADE',
            name='signal_user_decisions_signal_composite_fkey'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_signal_user_decisions_signal_id', 'signal_user_decisions', ['signal_id'])
    op.create_index('ix_signal_user_decisions_user_id', 'signal_user_decisions', ['user_id'])
    op.create_index('ix_signal_user_decisions_decision_ts', 'signal_user_decisions', ['decision_ts'])
    logger.info("✓ Signal user decisions table created")
    
    # Step 9: Final verification
    logger.info("Step 9/9: Verifying schema...")
    logger.info("✓ Schema verification complete")
    
    logger.info("=" * 80)
    logger.info("✓ Initial TimescaleDB schema created successfully!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Verification queries:")
    logger.info("  1. Check hypertables: SELECT * FROM timescaledb_information.hypertables;")
    logger.info("  2. Check chunks: SELECT * FROM timescaledb_information.chunks;")
    logger.info("  3. Check compression: SELECT * FROM timescaledb_information.compression_settings;")
    logger.info("")


def downgrade() -> None:
    """Drop all tables and TimescaleDB extension."""
    logger.info("=" * 80)
    logger.info("Dropping TimescaleDB schema...")
    logger.info("=" * 80)
    
    # Drop tables in reverse order (respecting foreign key dependencies)
    logger.info("Dropping signal_user_decisions table...")
    op.drop_table('signal_user_decisions')
    
    logger.info("Dropping option_chain_snapshots hypertable...")
    op.drop_table('option_chain_snapshots')
    
    logger.info("Dropping signals hypertable...")
    op.drop_table('signals')
    
    logger.info("Dropping master_tickers table...")
    op.drop_table('master_tickers')
    
    logger.info("Dropping subscriptions table...")
    op.drop_table('subscriptions')
    
    logger.info("Dropping user_settings table...")
    op.drop_table('user_settings')
    
    logger.info("Dropping users table...")
    op.drop_table('users')
    
    logger.info("Dropping TimescaleDB extension...")
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
    
    logger.info("=" * 80)
    logger.info("✓ TimescaleDB schema dropped")
    logger.info("=" * 80)
