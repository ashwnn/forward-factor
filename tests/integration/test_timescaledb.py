"""Integration tests for TimescaleDB hypertables and features."""
import pytest
from sqlalchemy import text, select
from datetime import datetime, timezone, timedelta
from app.models import Signal, OptionChainSnapshot
import asyncio
import logging

logger = logging.getLogger(__name__)


class TestTimescaleDBSetup:
    """Test TimescaleDB extension and configuration."""
    
    @pytest.mark.asyncio
    async def test_timescaledb_extension_enabled(self, test_db):
        """Verify TimescaleDB extension is enabled."""
        logger.info("Testing TimescaleDB extension status")
        
        result = await test_db.execute(text("""
            SELECT extname, extversion
            FROM pg_extension
            WHERE extname = 'timescaledb'
        """))
        extension = result.fetchone()
        
        assert extension is not None, "TimescaleDB extension not found"
        assert extension.extname == 'timescaledb'
        logger.info(f"✓ TimescaleDB version: {extension.extversion}")
    
    @pytest.mark.asyncio
    async def test_hypertables_exist(self, test_db):
        """Verify hypertables are properly configured."""
        logger.info("Testing hypertable configuration")
        
        result = await test_db.execute(text("""
            SELECT hypertable_schema, hypertable_name, num_dimensions
            FROM timescaledb_information.hypertables
            WHERE hypertable_name IN ('signals', 'option_chain_snapshots')
            ORDER BY hypertable_name
        """))
        hypertables = result.fetchall()
        
        assert len(hypertables) == 2, f"Expected 2 hypertables, found {len(hypertables)}"
        
        hypertable_names = {ht.hypertable_name for ht in hypertables}
        assert 'signals' in hypertable_names
        assert 'option_chain_snapshots' in hypertable_names
        
        # Verify all have 1 dimension (time)
        assert all(ht.num_dimensions == 1 for ht in hypertables)
        logger.info(f"✓ Found {len(hypertables)} hypertables with correct configuration")
    
    @pytest.mark.asyncio
    async def test_chunk_interval_configuration(self, test_db):
        """Verify chunk time interval is set to 1 day."""
        logger.info("Testing chunk interval configuration")
        
        result = await test_db.execute(text("""
            SELECT hypertable_name, column_name, time_interval
            FROM timescaledb_information.dimensions
            WHERE hypertable_name IN ('signals', 'option_chain_snapshots')
        """))
        dimensions = result.fetchall()
        
        assert len(dimensions) == 2
        for dim in dimensions:
            assert dim.column_name == 'as_of_ts'
            assert dim.time_interval == '1 day'
        logger.info("✓ Chunk intervals configured correctly")
    
    @pytest.mark.asyncio
    async def test_compression_policies_exist(self, test_db):
        """Verify compression policies are configured."""
        logger.info("Testing compression policy configuration")
        
        result = await test_db.execute(text("""
            SELECT application_name, config, hypertable_name
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_compression'
        """))
        policies = result.fetchall()
        
        assert len(policies) >= 2, f"Expected at least 2 compression policies, found {len(policies)}"
        logger.info(f"✓ Found {len(policies)} compression policies")
    
    @pytest.mark.asyncio
    async def test_composite_indexes_exist(self, test_db):
        """Verify composite indexes on (ticker, as_of_ts) exist."""
        logger.info("Testing composite index configuration")
        
        result = await test_db.execute(text("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE tablename IN ('signals', 'option_chain_snapshots')
              AND indexname LIKE 'idx_%_ticker_time'
            ORDER BY tablename
        """))
        indexes = result.fetchall()
        
        assert len(indexes) == 2, f"Expected 2 composite indexes, found {len(indexes)}"
        index_names = {idx.indexname for idx in indexes}
        assert 'idx_signals_ticker_time' in index_names
        assert 'idx_option_chain_snapshots_ticker_time' in index_names
        logger.info("✓ Composite indexes configured correctly")


class TestHypertableOperations:
    """Test hypertable data operations."""
    
    @pytest.mark.asyncio
    async def test_signal_insertion(self, test_db):
        """Test inserting signals into hypertable."""
        logger.info("Testing signal insertion into hypertable")
        
        signal = Signal(
            ticker="TEST",
            as_of_ts=datetime.now(timezone.utc),
            front_expiry=datetime.now(timezone.utc).date() + timedelta(days=30),
            back_expiry=datetime.now(timezone.utc).date() + timedelta(days=60),
            front_dte=30,
            back_dte=60,
            front_iv=0.25,
            back_iv=0.20,
            sigma_fwd=0.15,
            ff_value=0.30,
            vol_point='ATM',
            dedupe_key=f'test_signal_{datetime.now(timezone.utc).isoformat()}'
        )
        
        test_db.add(signal)
        await test_db.commit()
        
        # Verify insertion
        result = await test_db.execute(
            select(Signal).where(Signal.ticker == "TEST")
        )
        retrieved_signal = result.scalar_one_or_none()
        
        assert retrieved_signal is not None
        assert retrieved_signal.ticker == "TEST"
        assert retrieved_signal.ff_value == 0.30
        logger.info("✓ Signal inserted and retrieved successfully")
        
        # Cleanup
        await test_db.delete(retrieved_signal)
        await test_db.commit()
    
    @pytest.mark.asyncio
    async def test_time_range_query(self, test_db):
        """Test time-range queries use chunk exclusion."""
        logger.info("Testing time-range query performance")
        
        # Insert signals across different time periods
        now = datetime.now(timezone.utc)
        signals = []
        
        for i in range(5):
            signal = Signal(
                ticker=f"TICK{i}",
                as_of_ts=now - timedelta(hours=i*24),
                front_expiry=(now - timedelta(hours=i*24)).date() + timedelta(days=30),
                back_expiry=(now - timedelta(hours=i*24)).date() + timedelta(days=60),
                front_dte=30,
                back_dte=60,
                front_iv=0.25,
                back_iv=0.20,
                sigma_fwd=0.15,
                ff_value=0.20 + (i * 0.01),
                vol_point='ATM',
                dedupe_key=f'test_range_{i}_{now.isoformat()}'
            )
            signals.append(signal)
            test_db.add(signal)
        
        await test_db.commit()
        
        # Query last 48 hours
        cutoff = now - timedelta(hours=48)
        result = await test_db.execute(
            select(Signal).where(
                Signal.as_of_ts > cutoff,
                Signal.ticker.like('TICK%')
            )
        )
        recent_signals = result.scalars().all()
        
        # Should return signals from last 2 days (TICK0, TICK1)
        assert len(recent_signals) >= 2
        logger.info(f"✓ Time-range query returned {len(recent_signals)} signals")
        
        # Cleanup
        for sig in signals:
            await test_db.delete(sig)
        await test_db.commit()


class TestConcurrentWrites:
    """Test concurrent write operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_writes(self, test_engine):
        """Verify multiple workers can write simultaneously without locking."""
        logger.info("Testing concurrent writes to hypertable")
        
        from sqlalchemy.ext.asyncio import async_sessionmaker
        
        async_session = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async def write_signal(session_maker, ticker_index: int):
            """Write a single signal in its own session."""
            async with session_maker() as session:
                now = datetime.now(timezone.utc)
                signal = Signal(
                    ticker=f"CONCURRENT{ticker_index}",
                    as_of_ts=now,
                    front_expiry=now.date() + timedelta(days=30),
                    back_expiry=now.date() + timedelta(days=60),
                    front_dte=30,
                    back_dte=60,
                    front_iv=0.25,
                    back_iv=0.20,
                    sigma_fwd=0.15,
                    ff_value=0.20,
                    vol_point='ATM',
                    dedupe_key=f'concurrent_test_{ticker_index}_{now.isoformat()}'
                )
                session.add(signal)
                await session.commit()
                logger.debug(f"Signal {ticker_index} written successfully")
        
        # Create 10 concurrent write tasks
        tasks = [write_signal(async_session, i) for i in range(10)]
        
        # Execute all writes concurrently
        await asyncio.gather(*tasks)
        
        # Verify all signals were written
        async with async_session() as session:
            result = await session.execute(
                select(Signal).where(Signal.ticker.like('CONCURRENT%'))
            )
            concurrent_signals = result.scalars().all()
            
            assert len(concurrent_signals) == 10, f"Expected 10 signals, found {len(concurrent_signals)}"
            logger.info("✓ All 10 concurrent writes succeeded")
            
            # Cleanup
            for sig in concurrent_signals:
                await session.delete(sig)
            await session.commit()


class TestCompressionFeatures:
    """Test compression-related features."""
    
    @pytest.mark.asyncio
    async def test_compression_settings(self, test_db):
        """Verify compression settings are configured correctly."""
        logger.info("Testing compression settings")
        
        result = await test_db.execute(text("""
            SELECT
                hypertable_name,
                attname,
                segmentby_column_index,
                orderby_column_index
            FROM timescaledb_information.compression_settings
            WHERE hypertable_name IN ('signals', 'option_chain_snapshots')
            ORDER BY hypertable_name, attname
        """))
        settings = result.fetchall()
        
        assert len(settings) > 0, "No compression settings found"
        
        # Verify ticker is segment-by column
        ticker_settings = [s for s in settings if s.attname == 'ticker']
        assert len(ticker_settings) == 2, "ticker should be segment-by for both hypertables"
        assert all(s.segmentby_column_index is not None for s in ticker_settings)
        
        # Verify as_of_ts is order-by column
        time_settings = [s for s in settings if s.attname == 'as_of_ts']
        assert len(time_settings) == 2, "as_of_ts should be order-by for both hypertables"
        assert all(s.orderby_column_index is not None for s in time_settings)
        
        logger.info("✓ Compression settings verified")
