"""Fix composite foreign key for signal_user_decisions

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2025-11-27 14:30:00.000000

This migration fixes the foreign key constraint on signal_user_decisions to properly
reference the composite primary key (id, as_of_ts) on the signals table.

PostgreSQL requires foreign keys to reference ALL columns of a composite primary key.
This migration:
1. Adds signal_as_of_ts column to signal_user_decisions
2. Backfills the data from the signals table
3. Recreates the foreign key as a composite constraint
4. Adds appropriate indexes for query performance

"""
from alembic import op
import sqlalchemy as sa
import logging

logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision = 'g8h9i0j1k2l3'
down_revision = 'f7g8h9i0j1k2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add composite foreign key to signal_user_decisions."""
    logger.info("=" * 80)
    logger.info("Starting composite foreign key migration...")
    logger.info("=" * 80)
    
    # Step 1: Add signal_as_of_ts column (nullable initially for backfill)
    logger.info("Step 1/7: Adding signal_as_of_ts column to signal_user_decisions...")
    op.add_column('signal_user_decisions',
        sa.Column('signal_as_of_ts', sa.DateTime(), nullable=True))
    logger.info("✓ Column added")
    
    # Step 2: Backfill data from signals table
    logger.info("Step 2/7: Backfilling signal_as_of_ts from signals table...")
    logger.debug("Executing UPDATE to populate signal_as_of_ts")
    op.execute("""
        UPDATE signal_user_decisions sud
        SET signal_as_of_ts = s.as_of_ts
        FROM signals s
        WHERE sud.signal_id = s.id
    """)
    logger.info("✓ Data backfilled")
    
    # Step 3: Make column non-nullable
    logger.info("Step 3/7: Making signal_as_of_ts non-nullable...")
    op.alter_column('signal_user_decisions', 'signal_as_of_ts',
                    existing_type=sa.DateTime(),
                    nullable=False)
    logger.info("✓ Column constraint updated")
    
    # Step 4: Drop old single-column foreign key
    logger.info("Step 4/7: Dropping old foreign key constraint...")
    logger.debug("Dropping signal_user_decisions_signal_id_fkey")
    op.drop_constraint('signal_user_decisions_signal_id_fkey', 
                       'signal_user_decisions', type_='foreignkey')
    logger.info("✓ Old foreign key dropped")
    
    # Step 5: Create composite foreign key
    logger.info("Step 5/7: Creating composite foreign key constraint...")
    logger.debug("Creating foreign key on (signal_id, signal_as_of_ts) -> signals(id, as_of_ts)")
    op.create_foreign_key(
        'signal_user_decisions_signal_composite_fkey',
        'signal_user_decisions', 'signals',
        ['signal_id', 'signal_as_of_ts'],
        ['id', 'as_of_ts'],
        ondelete='CASCADE'
    )
    logger.info("✓ Composite foreign key created")
    
    # Step 6: Add composite index for join performance
    logger.info("Step 6/7: Adding composite index for query performance...")
    logger.debug("Creating index ix_signal_user_decisions_signal_composite")
    op.create_index(
        'ix_signal_user_decisions_signal_composite',
        'signal_user_decisions',
        ['signal_id', 'signal_as_of_ts']
    )
    logger.info("✓ Composite index created")
    
    # Step 7: Add index on decision_ts for timeline queries
    logger.info("Step 7/7: Adding index on decision_ts...")
    logger.debug("Creating index ix_signal_user_decisions_decision_ts")
    op.create_index(
        'ix_signal_user_decisions_decision_ts',
        'signal_user_decisions',
        ['decision_ts'],
        postgresql_using='btree'
    )
    logger.info("✓ Decision timestamp index created")
    
    logger.info("=" * 80)
    logger.info("✓ Composite foreign key migration completed successfully!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Changes:")
    logger.info("  - Added signal_as_of_ts column to signal_user_decisions")
    logger.info("  - Created composite foreign key (signal_id, signal_as_of_ts) -> signals(id, as_of_ts)")
    logger.info("  - Added indexes for query performance")
    logger.info("")


def downgrade() -> None:
    """Revert composite foreign key changes."""
    logger.info("=" * 80)
    logger.info("Starting composite foreign key rollback...")
    logger.info("=" * 80)
    
    # Step 1: Drop indexes
    logger.info("Step 1/4: Dropping indexes...")
    logger.debug("Dropping ix_signal_user_decisions_decision_ts")
    op.drop_index('ix_signal_user_decisions_decision_ts',
                  table_name='signal_user_decisions')
    logger.debug("Dropping ix_signal_user_decisions_signal_composite")
    op.drop_index('ix_signal_user_decisions_signal_composite',
                  table_name='signal_user_decisions')
    logger.info("✓ Indexes dropped")
    
    # Step 2: Drop composite foreign key
    logger.info("Step 2/4: Dropping composite foreign key constraint...")
    logger.debug("Dropping signal_user_decisions_signal_composite_fkey")
    op.drop_constraint('signal_user_decisions_signal_composite_fkey',
                       'signal_user_decisions', type_='foreignkey')
    logger.info("✓ Composite foreign key dropped")
    
    # Step 3: Recreate old single-column foreign key
    logger.info("Step 3/4: Recreating old single-column foreign key...")
    logger.debug("Creating signal_user_decisions_signal_id_fkey")
    op.create_foreign_key(
        'signal_user_decisions_signal_id_fkey',
        'signal_user_decisions', 'signals',
        ['signal_id'], ['id'],
        ondelete='CASCADE'
    )
    logger.info("✓ Old foreign key recreated")
    
    # Step 4: Drop signal_as_of_ts column
    logger.info("Step 4/4: Dropping signal_as_of_ts column...")
    logger.debug("Dropping column signal_as_of_ts")
    op.drop_column('signal_user_decisions', 'signal_as_of_ts')
    logger.info("✓ Column dropped")
    
    logger.info("=" * 80)
    logger.info("✓ Composite foreign key rollback completed")
    logger.info("=" * 80)
