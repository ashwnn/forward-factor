"""Discovery worker for market-wide scanning of liquid optionable stocks."""
import logging
import asyncio
from typing import List
from app.core.redis import get_redis
from app.providers.polygon import PolygonProvider
from app.providers import ProviderError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscoveryWorker:
    """Worker for populating the discovery queue with top liquid tickers."""
    
    def __init__(self, ticker_limit: int = 100):
        """
        Initialize the discovery worker.
        
        Args:
            ticker_limit: Number of top liquid tickers to fetch (default 100)
        """
        self.provider = PolygonProvider()
        self.ticker_limit = ticker_limit
        self.redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def refresh_universe(self) -> List[str]:
        """
        Refresh the universe of liquid tickers and push to discovery queue.
        
        Fetches top liquid tickers from Polygon and pushes them to the
        discovery_queue for processing by the ScanWorker.
        
        Returns:
            List of tickers that were added to the queue
        """
        logger.info(f"Refreshing discovery universe (limit={self.ticker_limit})...")
        
        try:
            # Fetch top liquid tickers
            tickers = await self.provider.get_top_liquid_tickers(limit=self.ticker_limit)
            
            if not tickers:
                logger.warning("No tickers returned from get_top_liquid_tickers")
                return []
            
            # Push to discovery queue
            redis = await self._get_redis()
            
            # Clear existing discovery queue first
            await redis.delete("discovery_queue")
            
            # Push all tickers to the queue
            for ticker in tickers:
                await redis.lpush("discovery_queue", ticker)
            
            logger.info(f"Pushed {len(tickers)} tickers to discovery_queue")
            return tickers
            
        except ProviderError as e:
            logger.error(f"Provider error during universe refresh: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during universe refresh: {e}", exc_info=True)
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.provider.close()
        if self.redis:
            await self.redis.close()
    
    async def run_once(self) -> List[str]:
        """
        Run a single universe refresh.
        
        This is intended to be called by a scheduler (e.g., APScheduler)
        rather than running in a continuous loop.
        
        Returns:
            List of tickers that were added to the queue
        """
        try:
            return await self.refresh_universe()
        finally:
            await self.cleanup()
    
    async def run(self, interval_hours: int = 1):
        """
        Run worker loop, periodically refreshing the universe.
        
        Args:
            interval_hours: How often to refresh (default 1 hour)
        """
        logger.info(f"Discovery worker started (interval={interval_hours}h)")
        
        try:
            while True:
                try:
                    await self.refresh_universe()
                except Exception as e:
                    logger.error(f"Error during universe refresh: {e}", exc_info=True)
                
                # Wait for next refresh
                await asyncio.sleep(interval_hours * 3600)
        finally:
            await self.cleanup()


async def main():
    """Main entry point for discovery worker."""
    worker = DiscoveryWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
