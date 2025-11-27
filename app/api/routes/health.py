"""Health check endpoints for API and database monitoring."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db, engine
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "forward-factor-api"}


@router.get("/health/db")
async def check_database_health(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive database health check including TimescaleDB status.
    
    Returns:
    - Database connectivity
    - TimescaleDB extension version
    - Hypertable configuration
    - Compression policy status
    - Connection pool statistics
    - Chunk statistics
    
    Example response:
    {
        "status": "healthy",
        "database": "timescaledb",
        "extension_version": "2.13.0",
        "hypertables": [...],
        "compression_policies": [...],
        "connection_pool": {...},
        "chunks": {...}
    }
    """
    logger.debug("Starting database health check")
    
    try:
        # Step 1: Basic connectivity test
        logger.debug("Testing database connectivity")
        await db.execute(text("SELECT 1"))
        logger.debug("✓ Database connection successful")
        
        # Step 2: Check TimescaleDB extension
        logger.debug("Checking TimescaleDB extension")
        result = await db.execute(text("""
            SELECT extname, extversion
            FROM pg_extension
            WHERE extname = 'timescaledb'
        """))
        extension = result.fetchone()
        extension_version = extension.extversion if extension else None
        logger.debug(f"✓ TimescaleDB version: {extension_version}")
        
        # Step 3: Check hypertables
        logger.debug("Checking hypertable configurations")
        result = await db.execute(text("""
            SELECT hypertable_name, num_chunks, num_dimensions
            FROM timescaledb_information.hypertables
            ORDER BY hypertable_name
        """))
        hypertables = [dict(row._mapping) for row in result.fetchall()]
        logger.debug(f"✓ Found {len(hypertables)} hypertables")
        
        # Step 4: Check compression policies
        logger.debug("Checking compression policies")
        result = await db.execute(text("""
            SELECT hypertable_name, attname as column_name,
                   segmentby_column_index, orderby_column_index
            FROM timescaledb_information.compression_settings
            ORDER BY hypertable_name, attname
        """))
        compression_settings = [dict(row._mapping) for row in result.fetchall()]
        
        # Get compression policy jobs
        result = await db.execute(text("""
            SELECT application_name, schedule_interval, config,
                   hypertable_name
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_compression'
        """))
        compression_policies = [dict(row._mapping) for row in result.fetchall()]
        logger.debug(f"✓ Found {len(compression_policies)} compression policies")
        
        # Step 5: Get chunk statistics
        logger.debug("Fetching chunk statistics")
        result = await db.execute(text("""
            SELECT
                hypertable_name,
                COUNT(*) as total_chunks,
                SUM(CASE WHEN is_compressed THEN 1 ELSE 0 END) as compressed_chunks,
                COUNT(DISTINCT range_start::date) as unique_days
            FROM timescaledb_information.chunks
            GROUP BY hypertable_name
        """))
        chunk_stats = [dict(row._mapping) for row in result.fetchall()]
        logger.debug(f"✓ Chunk statistics retrieved")
        
        # Step 6: Get connection pool stats
        logger.debug("Fetching connection pool statistics")
        pool_stats = {
            "size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "checked_in": engine.pool.checkedin()
        }
        logger.debug(f"✓ Pool stats: {pool_stats}")
        
        # Step 7: Get database size
        logger.debug("Checking database size")
        result = await db.execute(text("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as size
        """))
        db_size = result.scalar_one()
        logger.debug(f"✓ Database size: {db_size}")
        
        logger.info("Database health check completed successfully")
        
        return {
            "status": "healthy",
            "database": "timescaledb",
            "extension_version": extension_version,
            "database_size": db_size,
            "hypertables": hypertables,
            "compression": {
                "policies": compression_policies,
                "settings": compression_settings
            },
            "chunks": chunk_stats,
            "connection_pool": pool_stats
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.get("/health/db/chunks")
async def get_chunk_details(db: AsyncSession = Depends(get_db)):
    """
    Get detailed chunk information for all hypertables.
    
    Returns detailed statistics about chunks including:
    - Chunk names and time ranges
    - Compression status
    - Chunk sizes
    """
    logger.debug("Fetching detailed chunk information")
    
    try:
        result = await db.execute(text("""
            SELECT
                hypertable_name,
                chunk_name,
                range_start,
                range_end,
                is_compressed,
                CASE
                    WHEN is_compressed THEN
                        pg_size_pretty(compressed_total_bytes)
                    ELSE
                        pg_size_pretty(total_bytes)
                END as chunk_size
            FROM timescaledb_information.chunks
            ORDER BY hypertable_name, range_start DESC
            LIMIT 50
        """))
        chunks = [dict(row._mapping) for row in result.fetchall()]
        
        logger.info(f"Retrieved {len(chunks)} chunk details")
        
        return {
            "status": "success",
            "chunk_count": len(chunks),
            "chunks": chunks
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch chunk details: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/health/db/compression")
async def get_compression_stats(db: AsyncSession = Depends(get_db)):
    """
    Get compression statistics including compression ratios.
    
    Returns:
    - Compression ratios for compressed chunks
    - Storage savings
    - Number of compressed vs uncompressed chunks
    """
    logger.debug("Fetching compression statistics")
    
    try:
        result = await db.execute(text("""
            SELECT
                chunk_schema,
                chunk_name,
                compression_status,
                pg_size_pretty(before_compression_total_bytes) as size_before,
                pg_size_pretty(after_compression_total_bytes) as size_after,
                ROUND(
                    (1 - after_compression_total_bytes::float / 
                     NULLIF(before_compression_total_bytes, 0)::float) * 100,
                    2
                ) as compression_percentage
            FROM timescaledb_information.compressed_chunk_stats
            ORDER BY compression_percentage DESC NULLS LAST
            LIMIT 20
        """))
        compression_stats = [dict(row._mapping) for row in result.fetchall()]
        
        # Calculate overall statistics
        if compression_stats:
            total_before = sum(
                int(stat['size_before'].split()[0].replace(',', ''))
                for stat in compression_stats if stat['size_before']
            )
            total_after = sum(
                int(stat['size_after'].split()[0].replace(',', ''))
                for stat in compression_stats if stat['size_after']
            )
            
            overall_ratio = None
            if total_before > 0:
                overall_ratio = round((1 - total_after / total_before) * 100, 2)
        else:
            overall_ratio = None
        
        logger.info(f"Retrieved {len(compression_stats)} compression statistics")
        
        return {
            "status": "success",
            "compressed_chunks": len(compression_stats),
            "overall_compression_percentage": overall_ratio,
            "chunks": compression_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch compression stats: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
