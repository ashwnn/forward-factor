"""Pytest fixtures for TimescaleDB integration tests."""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base
import logging

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine for integration tests.
    
    Uses the same DATABASE_URL as the application.
    Tests should be run against a test database or in isolation.
    """
    logger.info(f"Creating test engine for: {settings.database_url}")
    
    engine = create_async_engine(
        settings.database_url,
        echo=settings.log_level == "DEBUG",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )
    
    logger.info("Test engine created successfully")
    yield engine
    
    logger.info("Disposing test engine")
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db(test_engine):
    """
    Create clean database session for each test.
    
    Each test gets a fresh session that rolls back after completion.
    """
    logger.debug("Creating test database session")
    
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with async_session() as session:
        logger.debug("Test session created")
        yield session
        logger.debug("Rolling back test session")
        await session.rollback()
        logger.debug("Test session closed")


@pytest.fixture(scope="function")
async def clean_signals_table(test_db):
    """
    Clean signals table before test.
    
    Use this fixture when you need a clean signals table.
    WARNING: This deletes all data in signals table!
    """
    logger.warning("Cleaning signals table for test")
    await test_db.execute(text("TRUNCATE TABLE signals CASCADE"))
    await test_db.commit()
    yield
    logger.debug("Test cleanup completed")
