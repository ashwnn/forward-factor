"""Migrate to TimescaleDB with hypertables and compression

Revision ID: f7g8h9i0j1k2
Revises: a1b2c3d4e5f6
Create Date: 2025-11-27 19:27:00.000000

This migration enables TimescaleDB and converts time-series tables to hypertables
with compression policies for optimal storage and query performance.

Changes:
- Enable TimescaleDB extension
- Convert 'signals' table to hypertable (partitioned by as_of_ts, 1 day chunks)
- Convert 'option_chain_snapshots' table to hypertable (partitioned by as_of_ts, 1 day chunks)
- Add compression policies (compress data older than 7 days)
- Create composite indexes for (ticker, as_of_ts) queries
"""
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision = 'f7g8h9i0j1k2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Migrate to TimescaleDB:
    1. Enable TimescaleDB extension
    2. Convert time-series tables to hypertables
    3. Add compression policies
    4. Create composite indexes
    """
    logger.info("=" * 80)
    logger.info("Starting TimescaleDB migration...")
    logger.info("=" * 80)
    
    # Step 1: Enable TimescaleDB extension
    logger.info("Step 1/5: Enabling TimescaleDB extension...")
    logger.debug("Executing: CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    logger.info("✓ TimescaleDB extension enabled")
    
    
    # Step 2: Prepare 'signals' table for hypertable conversion
    logger.info("Step 2/7: Preparing 'signals' table for hypertable conversion...")
    
    # First, drop the foreign key constraint from signal_user_decisions that depends on signals.id
    logger.debug("Dropping foreign key constraint signal_user_decisions_signal_id_fkey")
    op.execute("""
        ALTER TABLE signal_user_decisions DROP CONSTRAINT IF EXISTS signal_user_decisions_signal_id_fkey;
    """)
    
    # Now we can drop the old primary key constraint
    logger.debug("Dropping existing primary key constraint on 'signals'")
    op.execute("""
        ALTER TABLE signals DROP CONSTRAINT IF EXISTS signals_pkey;
    """)
    
    # Create the new composite primary key
    logger.debug("Creating composite primary key (id, as_of_ts) on 'signals'")
    op.execute("""
        ALTER TABLE signals ADD CONSTRAINT signals_pkey PRIMARY KEY (id, as_of_ts);
    """)
    
    # Note: We don't recreate the foreign key here because signal_user_decisions
    # doesn't have the signal_as_of_ts column yet. The next migration
    # (g8h9i0j1k2l3) will add that column and create the composite foreign key.
    
    logger.info("✓ 'signals' table prepared with composite primary key (id, as_of_ts)")
    
    # Step 3: Convert 'signals' table to hypertable
    logger.info("Step 3/7: Converting 'signals' table to hypertable...")
    logger.debug("Partition column: as_of_ts, Chunk interval: 1 day")
    op.execute("""
        SELECT create_hypertable(
            'signals',
            'as_of_ts',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    """)
    logger.info("✓ 'signals' table converted to hypertable")
    
    # Step 4: Prepare 'option_chain_snapshots' table for hypertable conversion
    logger.info("Step 4/7: Preparing 'option_chain_snapshots' table for hypertable conversion...")
    logger.debug("Dropping existing primary key constraint on 'option_chain_snapshots'")
    op.execute("""
        ALTER TABLE option_chain_snapshots DROP CONSTRAINT IF EXISTS option_chain_snapshots_pkey;
    """)
    logger.debug("Creating composite primary key (id, as_of_ts) on 'option_chain_snapshots'")
    op.execute("""
        ALTER TABLE option_chain_snapshots ADD CONSTRAINT option_chain_snapshots_pkey PRIMARY KEY (id, as_of_ts);
    """)
    logger.info("✓ 'option_chain_snapshots' table prepared with composite primary key (id, as_of_ts)")
    
    # Step 5: Convert 'option_chain_snapshots' table to hypertable
    logger.info("Step 5/7: Converting 'option_chain_snapshots' table to hypertable...")
    logger.debug("Partition column: as_of_ts, Chunk interval: 1 day")
    op.execute("""
        SELECT create_hypertable(
            'option_chain_snapshots',
            'as_of_ts',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    """)
    logger.info("✓ 'option_chain_snapshots' table converted to hypertable")
    
    # Step 6: Enable compression on 'signals' table
    logger.info("Step 6/7: Configuring compression policies...")
    logger.debug("Configuring compression for 'signals': segment by ticker, order by as_of_ts DESC")
    op.execute("""
        ALTER TABLE signals SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'ticker',
            timescaledb.compress_orderby = 'as_of_ts DESC'
        );
    """)
    logger.debug("Adding compression policy for 'signals': compress after 7 days")
    op.execute("""
        SELECT add_compression_policy('signals', INTERVAL '7 days');
    """)
    logger.info("✓ Compression policy added for 'signals' (compress after 7 days)")
    
    # Enable compression on 'option_chain_snapshots' table
    logger.debug("Configuring compression for 'option_chain_snapshots': segment by ticker, order by as_of_ts DESC")
    op.execute("""
        ALTER TABLE option_chain_snapshots SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'ticker',
            timescaledb.compress_orderby = 'as_of_ts DESC'
        );
    """)
    logger.debug("Adding compression policy for 'option_chain_snapshots': compress after 7 days")
    op.execute("""
        SELECT add_compression_policy('option_chain_snapshots', INTERVAL '7 days');
    """)
    logger.info("✓ Compression policy added for 'option_chain_snapshots' (compress after 7 days)")
    
    # Step 7: Create composite indexes for common query patterns
    logger.info("Step 7/7: Creating composite indexes...")
    logger.debug("Creating index: idx_signals_ticker_time on (ticker, as_of_ts)")
    op.create_index(
        'idx_signals_ticker_time',
        'signals',
        ['ticker', 'as_of_ts'],
        postgresql_using='btree',
        if_not_exists=True
    )
    logger.info("✓ Composite index created: idx_signals_ticker_time")
    
    logger.debug("Creating index: idx_option_chain_snapshots_ticker_time on (ticker, as_of_ts)")
    op.create_index(
        'idx_option_chain_snapshots_ticker_time',
        'option_chain_snapshots',
        ['ticker', 'as_of_ts'],
        postgresql_using='btree',
        if_not_exists=True
    )
    logger.info("✓ Composite index created: idx_option_chain_snapshots_ticker_time")
    
    logger.info("=" * 80)
    logger.info("✓ TimescaleDB migration completed successfully!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Verification queries:")
    logger.info("  1. Check hypertables: SELECT * FROM timescaledb_information.hypertables;")
    logger.info("  2. Check chunks: SELECT * FROM timescaledb_information.chunks;")
    logger.info("  3. Check compression: SELECT * FROM timescaledb_information.compression_settings;")
    logger.info("")


def downgrade() -> None:
    """
    Revert TimescaleDB migration:
    1. Drop composite indexes
    2. Remove compression policies
    3. Drop hypertables (revert to regular tables)
    4. Drop TimescaleDB extension
    """
    logger.info("=" * 80)
    logger.info("Starting TimescaleDB migration rollback...")
    logger.info("=" * 80)
    
    # Step 1: Drop composite indexes
    logger.info("Step 1/4: Dropping composite indexes...")
    logger.debug("Dropping index: idx_option_chain_snapshots_ticker_time")
    op.drop_index(
        'idx_option_chain_snapshots_ticker_time',
        table_name='option_chain_snapshots',
        if_exists=True
    )
    logger.debug("Dropping index: idx_signals_ticker_time")
    op.drop_index(
        'idx_signals_ticker_time',
        table_name='signals',
        if_exists=True
    )
    logger.info("✓ Composite indexes dropped")
    
    # Step 2: Remove compression policies
    logger.info("Step 2/4: Removing compression policies...")
    logger.debug("Removing compression policy from 'option_chain_snapshots'")
    op.execute("""
        SELECT remove_compression_policy('option_chain_snapshots', if_exists => true);
    """)
    logger.debug("Removing compression policy from 'signals'")
    op.execute("""
        SELECT remove_compression_policy('signals', if_exists => true);
    """)
    logger.info("✓ Compression policies removed")
    
    # Step 3: Drop hypertables (reverts to regular tables)
    logger.info("Step 3/4: Reverting hypertables to regular tables...")
    logger.debug("Dropping hypertable: option_chain_snapshots")
    op.execute("""
        SELECT drop_chunks('option_chain_snapshots', older_than => INTERVAL '0 seconds');
    """)
    logger.debug("Dropping hypertable: signals")
    op.execute("""
        SELECT drop_chunks('signals', older_than => INTERVAL '0 seconds');
    """)
    logger.info("✓ Hypertables reverted to regular tables")
    
    # Step 4: Revert composite primary keys to single-column primary keys
    logger.info("Step 4/6: Reverting composite primary keys...")
    
    # Revert signals table
    logger.debug("Reverting 'signals' primary key to single column (id)")
    # Drop any foreign key constraints (handles both old single-column and new composite)
    op.execute("""
        ALTER TABLE signal_user_decisions DROP CONSTRAINT IF EXISTS signal_user_decisions_signal_composite_fkey;
    """)
    op.execute("""
        ALTER TABLE signal_user_decisions DROP CONSTRAINT IF EXISTS signal_user_decisions_signal_id_fkey;
    """)
    # Drop composite primary key
    op.execute("""
        ALTER TABLE signals DROP CONSTRAINT IF EXISTS signals_pkey;
    """)
    # Add single-column primary key
    op.execute("""
        ALTER TABLE signals ADD CONSTRAINT signals_pkey PRIMARY KEY (id);
    """)
    # Recreate single-column foreign key (only if signal_as_of_ts doesn't exist)
    # Note: If migration g8h9i0j1k2l3 has run, we can't recreate the FK until it's reverted
    op.execute("""
        DO $$
        BEGIN
            -- Only add FK if the column signal_as_of_ts doesn't exist (migration g8h9i0j1k2l3 not run)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='signal_user_decisions' AND column_name='signal_as_of_ts'
            ) THEN
                ALTER TABLE signal_user_decisions 
                ADD CONSTRAINT signal_user_decisions_signal_id_fkey 
                FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)
    
    # Revert option_chain_snapshots table
    logger.debug("Reverting 'option_chain_snapshots' primary key to single column (id)")
    op.execute("""
        ALTER TABLE option_chain_snapshots DROP CONSTRAINT IF EXISTS option_chain_snapshots_pkey;
    """)
    op.execute("""
        ALTER TABLE option_chain_snapshots ADD CONSTRAINT option_chain_snapshots_pkey PRIMARY KEY (id);
    """)
    logger.info("✓ Composite primary keys reverted to single-column")
    
    # Step 5: Drop TimescaleDB extension
    logger.info("Step 5/6: Dropping TimescaleDB extension...")
    logger.debug("Executing: DROP EXTENSION IF EXISTS timescaledb CASCADE")
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
    logger.info("✓ TimescaleDB extension dropped")
    
    logger.info("=" * 80)
    logger.info("✓ TimescaleDB migration rollback completed")
    logger.info("=" * 80)
