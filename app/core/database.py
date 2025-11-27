"""Database setup with async SQLAlchemy for PostgreSQL/TimescaleDB."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
import logging
import re
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Mask password in database URL for logging
def mask_db_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)

logger.info(f"Connecting to database: {mask_db_url(settings.database_url)}")
logger.debug(f"Database URL scheme: {settings.database_url.split(':')[0]}")

# Create async engine with PostgreSQL connection pooling
engine_args = {
    "echo": settings.log_level == "DEBUG",  # Log all SQL if DEBUG
    "pool_pre_ping": True,  # Verify connections before using
    "pool_size": 10,  # Maintain 10 connections in pool
    "max_overflow": 20,  # Allow up to 20 additional connections
    "pool_timeout": 30,  # Wait up to 30s for connection
    "pool_recycle": 3600,  # Recycle connections every hour
}

logger.info(
    f"Configuring connection pool: pool_size=10, max_overflow=20, "
    f"pool_timeout=30s, pool_recycle=3600s"
)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    **engine_args
)

logger.info("Database engine created with connection pooling enabled")
logger.debug(f"Engine pool configuration: {engine.pool}")

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

logger.info("Async session factory created")


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    NOTE: This dependency does NOT auto-commit. Services must explicitly
    call await session.commit() when needed. This provides clearer
    transaction boundaries and avoids double-commit issues.
    """
    logger.debug("Creating new database session from pool")
    session_start_time = None
    
    if logger.isEnabledFor(logging.DEBUG):
        import time
        session_start_time = time.time()
        logger.debug(f"Pool status - size: {engine.pool.size()}, checked_in: {engine.pool.checkedin()}, checked_out: {engine.pool.checkedout()}, overflow: {engine.pool.overflow()}")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            logger.debug("Database session completed successfully")
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {str(e)}", exc_info=True)
            logger.debug(f"Error type: {type(e).__name__}, Error details: {e}")
            raise
        finally:
            if logger.isEnabledFor(logging.DEBUG) and session_start_time:
                import time
                duration = time.time() - session_start_time
                logger.debug(f"Database session closed (duration: {duration:.3f}s)")
                logger.debug(f"Pool status after close - size: {engine.pool.size()}, checked_in: {engine.pool.checkedin()}")
            else:
                logger.debug("Database session closed")


def get_async_session():
    """Context manager for getting database sessions outside of FastAPI requests."""
    logger.debug("Creating standalone async session context manager")
    return AsyncSessionLocal()


async def init_db():
    """Initialize database tables."""
    logger.info("Initializing database tables...")
    logger.debug("Acquiring database connection for schema initialization")
    
    try:
        async with engine.begin() as conn:
            logger.debug("Connection acquired, creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.debug("Tables created successfully")
        logger.info("✓ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {str(e)}", exc_info=True)
        logger.debug(f"Error type: {type(e).__name__}")
        logger.debug(f"Database URL (masked): {mask_db_url(settings.database_url)}")
        raise
