"""Scan scheduler with tiered cadence."""
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.services import TickerService

from app.core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScanScheduler:
    """Scheduler for tiered ticker scanning."""
    
    def __init__(self):
        logger.info("Initializing ScanScheduler...")
        logger.debug("Creating AsyncIOScheduler instance")
        self.scheduler = AsyncIOScheduler()
        self.redis = None
        logger.info("ScanScheduler initialized")
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis is None:
            logger.debug("Connecting to Redis...")
            self.redis = await get_redis()
            logger.info("Redis connection established")
        return self.redis
    
    async def enqueue_tier_scans(self, tier: str):
        """
        Enqueue scan jobs for all tickers in a tier.
        
        Args:
            tier: Scan tier ("high", "medium", "low")
        """
        try:
            async with AsyncSessionLocal() as db:
                tickers = await TickerService.get_tickers_by_tier(db, tier)
                
                if not tickers:
                    logger.info(f"No tickers in {tier} tier")
                    return
                
                logger.debug(f"Found {len(tickers)} tickers in {tier} tier")
                
                redis = await self._get_redis()
                
                # Enqueue each ticker
                for ticker in tickers:
                    await redis.lpush("scan_queue", ticker)
                
                logger.info(f"Enqueued {len(tickers)} tickers from {tier} tier")
                
        except Exception as e:
            logger.error(f"Error enqueuing {tier} tier scans: {e}", exc_info=True)
    
    async def scan_high_tier(self):
        """Scan high tier tickers."""
        await self.enqueue_tier_scans("high")
    
    async def scan_medium_tier(self):
        """Scan medium tier tickers."""
        await self.enqueue_tier_scans("medium")
    
    async def scan_low_tier(self):
        """Scan low tier tickers."""
        await self.enqueue_tier_scans("low")
    
    async def update_ticker_registry(self):
        """Periodic update of ticker registry."""
        try:
            async with AsyncSessionLocal() as db:
                await TickerService.update_ticker_registry(db)
                logger.info("Updated ticker registry")
        except Exception as e:
            logger.error(f"Error updating ticker registry: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler with tiered jobs."""
        logger.info("="*60)
        logger.info("Starting scan scheduler...")
        logger.info(f"Log level: {settings.log_level}")
        logger.info(f"High tier cadence: every {settings.scan_cadence_high} minutes")
        logger.info(f"Medium tier cadence: every {settings.scan_cadence_medium} minutes")
        logger.info(f"Low tier cadence: every {settings.scan_cadence_low} minutes")
        logger.info("="*60)
        
        # High tier: every N minutes (from config)
        self.scheduler.add_job(
            self.scan_high_tier,
            trigger=IntervalTrigger(minutes=settings.scan_cadence_high),
            id="scan_high_tier",
            replace_existing=True
        )
        
        # Medium tier: every N minutes
        self.scheduler.add_job(
            self.scan_medium_tier,
            trigger=IntervalTrigger(minutes=settings.scan_cadence_medium),
            id="scan_medium_tier",
            replace_existing=True
        )
        
        # Low tier: every N minutes
        self.scheduler.add_job(
            self.scan_low_tier,
            trigger=IntervalTrigger(minutes=settings.scan_cadence_low),
            id="scan_low_tier",
            replace_existing=True
        )
        
        # Update ticker registry every 5 minutes
        self.scheduler.add_job(
            self.update_ticker_registry,
            trigger=IntervalTrigger(minutes=5),
            id="update_registry",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("All scheduled jobs registered successfully")
        logger.info("="*60)
        logger.info("Scheduler started successfully")
        logger.info("="*60)
    
    async def run(self):
        """Run scheduler indefinitely."""
        self.start()
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down scheduler...")
            self.scheduler.shutdown()


async def main():
    """Main entry point for scheduler."""
    scheduler = ScanScheduler()
    await scheduler.run()


if __name__ == "__main__":
    asyncio.run(main())
