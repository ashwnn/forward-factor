"""Redis connection pool for caching and state management."""
import asyncio
import redis.asyncio as redis
from app.core.config import settings


# Global Redis connection pool
_redis_pool: redis.Redis | None = None
_redis_lock = asyncio.Lock()


async def get_redis() -> redis.Redis:
    """Get Redis connection from pool (thread-safe initialization)."""
    global _redis_pool
    
    # Fast path: pool already initialized
    if _redis_pool is not None:
        return _redis_pool
    
    # Slow path: need to initialize with lock
    async with _redis_lock:
        # Double-check after acquiring lock
        if _redis_pool is None:
            _redis_pool = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )
    return _redis_pool


async def close_redis():
    """Close Redis connection pool."""
    global _redis_pool
    async with _redis_lock:
        if _redis_pool:
            await _redis_pool.close()
            _redis_pool = None
