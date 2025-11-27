"""TimescaleDB monitoring and statistics utilities."""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TimescaleMonitor:
    """Monitor TimescaleDB hypertables, chunks, and compression."""
    
    @staticmethod
    async def get_chunk_statistics(db: AsyncSession) -> List[Dict]:
        """
        Get chunk statistics for all hypertables.
        
        Returns detailed information about each chunk including:
        - Hypertable name
        - Chunk name and schema
        - Time range (start/end)
        - Compression status
        - Chunk size
        """
        logger.debug("Fetching chunk statistics")
        
        result = await db.execute(text("""
            SELECT
                hypertable_name,
                chunk_schema,
                chunk_name,
                range_start,
                range_end,
                is_compressed,
                CASE
                    WHEN is_compressed THEN
                        pg_size_pretty(compressed_total_bytes)
                    ELSE
                        pg_size_pretty(total_bytes)
                END as chunk_size,
                CASE
                    WHEN is_compressed THEN compressed_total_bytes
                    ELSE total_bytes
                END as chunk_bytes
            FROM timescaledb_information.chunks
            ORDER BY hypertable_name, range_start DESC
        """))
        
        chunks = [dict(row._mapping) for row in result.fetchall()]
        logger.debug(f"Retrieved {len(chunks)} chunks")
        return chunks
    
    @staticmethod
    async def get_compression_stats(db: AsyncSession) -> List[Dict]:
        """
        Get compression statistics for hypertables.
        
        Returns compression ratios, storage savings, and efficiency metrics.
        """
        logger.debug("Fetching compression statistics")
        
        result = await db.execute(text("""
            SELECT
                chunk_schema,
                chunk_name,
                compression_status,
                before_compression_total_bytes,
                after_compression_total_bytes,
                pg_size_pretty(before_compression_total_bytes) as size_before_pretty,
                pg_size_pretty(after_compression_total_bytes) as size_after_pretty,
                ROUND(
                    (1 - after_compression_total_bytes::float / 
                     NULLIF(before_compression_total_bytes, 0)::float) * 100,
                    2
                ) as compression_percentage
            FROM timescaledb_information.compressed_chunk_stats
            WHERE compression_status = 'Compressed'
            ORDER BY compression_percentage DESC NULLS LAST
        """))
        
        stats = [dict(row._mapping) for row in result.fetchall()]
        logger.debug(f"Retrieved {len(stats)} compression statistics")
        return stats
    
    @staticmethod
    async def get_hypertable_summary(db: AsyncSession) -> List[Dict]:
        """
        Get summary statistics for each hypertable.
        
        Returns:
        - Hypertable name
        - Total number of chunks
        - Compressed vs uncompressed chunks
        - Total size
        - Time range covered
        """
        logger.debug("Fetching hypertable summary")
        
        result = await db.execute(text("""
            SELECT
                h.hypertable_name,
                h.num_chunks,
                COUNT(CASE WHEN c.is_compressed THEN 1 END) as compressed_chunks,
                COUNT(CASE WHEN NOT c.is_compressed THEN 1 END) as uncompressed_chunks,
                pg_size_pretty(SUM(c.total_bytes)) as total_size,
                MIN(c.range_start) as oldest_data,
                MAX(c.range_end) as newest_data
            FROM timescaledb_information.hypertables h
            LEFT JOIN timescaledb_information.chunks c
                ON h.hypertable_name = c.hypertable_name
            GROUP BY h.hypertable_name, h.num_chunks
            ORDER BY h.hypertable_name
        """))
        
        summary = [dict(row._mapping) for row in result.fetchall()]
        logger.debug(f"Retrieved summary for {len(summary)} hypertables")
        return summary
    
    @staticmethod
    async def get_compression_policy_status(db: AsyncSession) -> List[Dict]:
        """
        Get status of compression policies.
        
        Returns information about compression jobs, schedules, and last run status.
        """
        logger.debug("Fetching compression policy status")
        
        result = await db.execute(text("""
            SELECT
                application_name,
                schedule_interval,
                config,
                hypertable_name,
                last_run_status,
                last_successful_finish,
                next_start
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_compression'
            ORDER BY hypertable_name
        """))
        
        policies = [dict(row._mapping) for row in result.fetchall()]
        logger.debug(f"Retrieved {len(policies)} compression policies")
        return policies
    
    @staticmethod
    async def log_database_stats(db: AsyncSession):
        """
        Log comprehensive database statistics for monitoring.
        
        Logs:
        - Hypertable summary
        - Chunk counts
        - Compression ratios
        - Database size
        """
        logger.info("=" * 60)
        logger.info("TimescaleDB Statistics Summary")
        logger.info("=" * 60)
        
        try:
            # Get hypertable summary
            summary = await TimescaleMonitor.get_hypertable_summary(db)
            for ht in summary:
                logger.info(f"Hypertable: {ht['hypertable_name']}")
                logger.info(f"  Total chunks: {ht['num_chunks']}")
                logger.info(f"  Compressed: {ht['compressed_chunks']}, Uncompressed: {ht['uncompressed_chunks']}")
                logger.info(f"  Total size: {ht['total_size']}")
                logger.info(f"  Data range: {ht['oldest_data']} to {ht['newest_data']}")
            
            # Get overall compression stats
            comp_stats = await TimescaleMonitor.get_compression_stats(db)
            if comp_stats:
                avg_compression = sum(s['compression_percentage'] for s in comp_stats) / len(comp_stats)
                logger.info(f"Average compression ratio: {avg_compression:.2f}%")
            
            # Get database size
            result = await db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """))
            db_size = result.scalar_one()
            logger.info(f"Total database size: {db_size}")
            
        except Exception as e:
            logger.error(f"Failed to log database stats: {e}", exc_info=True)
        
        logger.info("=" * 60)
    
    @staticmethod
    async def check_slow_queries(
        db: AsyncSession,
        min_duration_ms: int = 100,
        limit: int = 10
    ) -> List[Dict]:
        """
        Check for slow queries using pg_stat_statements.
        
        Args:
            min_duration_ms: Minimum average query duration in milliseconds
            limit: Maximum number of slow queries to return
        
        Returns:
            List of slow queries with statistics
        
        Note: Requires pg_stat_statements extension to be enabled.
        """
        logger.debug(f"Checking for slow queries (>{min_duration_ms}ms)")
        
        try:
            result = await db.execute(text("""
                SELECT
                    LEFT(query, 100) as query_snippet,
                    calls,
                    ROUND(total_exec_time::numeric, 2) as total_time_ms,
                    ROUND(mean_exec_time::numeric, 2) as mean_time_ms,
                    ROUND(max_exec_time::numeric, 2) as max_time_ms,
                    ROUND(stddev_exec_time::numeric, 2) as stddev_time_ms
                FROM pg_stat_statements
                WHERE mean_exec_time > :min_duration
                ORDER BY mean_exec_time DESC
                LIMIT :limit
            """), {"min_duration": min_duration_ms, "limit": limit})
            
            slow_queries = [dict(row._mapping) for row in result.fetchall()]
            
            if slow_queries:
                logger.warning(f"Found {len(slow_queries)} slow queries")
                for i, query in enumerate(slow_queries, 1):
                    logger.warning(
                        f"Slow query #{i}: {query['mean_time_ms']}ms avg, "
                        f"{query['calls']} calls - {query['query_snippet']}..."
                    )
            else:
                logger.debug("No slow queries found")
            
            return slow_queries
            
        except Exception as e:
            logger.debug(f"pg_stat_statements not available or error: {e}")
            return []
