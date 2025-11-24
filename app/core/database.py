"""Database setup with async SQLAlchemy."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

# Mask password in database URL for logging
def mask_db_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)

logger.info(f"Connecting to database: {mask_db_url(settings.database_url)}")

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

logger.info(f"Database engine created with pool_size=10, max_overflow=20")

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting database sessions."""
    logger.debug("Creating new database session")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Database session committed successfully")
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {str(e)}")
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")


def get_async_session():
    """Context manager for getting database sessions outside of FastAPI requests."""
    return AsyncSessionLocal()


async def init_db():
    """Initialize database tables."""
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {str(e)}", exc_info=True)
        raise
