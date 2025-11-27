"""Scan worker for fetching chains and computing signals."""
import logging
import asyncio
from typing import Dict, Any, List, Set
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.providers.polygon import PolygonProvider
from app.services import TickerService, SignalService, UserService, SubscriptionService, stability_tracker
from app.services.signal_engine import compute_signals
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScanWorker:
    """Worker for scanning tickers and computing signals."""
    
    def __init__(self):
        self.provider = PolygonProvider()
        self.redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def scan_ticker(self, ticker: str, is_discovery: bool = False):
        """
        Scan a single ticker for signals.
        
        Args:
            ticker: Ticker symbol to scan
            is_discovery: Whether this is a discovery scan (from discovery_queue)
        """
        logger.info(f"Scanning {ticker} (discovery={is_discovery})...")
        
        try:
            # Fetch chain snapshot
            chain = await self.provider.get_chain_snapshot(ticker)
            
            # Cache snapshot
            redis = await self._get_redis()
            cache_key = f"chain:{ticker}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
            await redis.setex(cache_key, 300, "cached")  # 5 min TTL
            
            # Get all subscribers for this ticker
            async with AsyncSessionLocal() as db:
                subscriber_ids = await SubscriptionService.get_ticker_subscribers(db, ticker)
                
                # For discovery mode, also get users with discovery_mode enabled
                discovery_user_ids: List[str] = []
                if is_discovery:
                    discovery_user_ids = await UserService.get_discovery_users(db)
                
                # Combine subscribers and discovery users (avoid duplicates)
                all_user_ids: Set[str] = set(subscriber_ids) | set(discovery_user_ids)
                
                if not all_user_ids:
                    logger.info(f"No subscribers or discovery users for {ticker}, skipping")
                    return
                
                # For each user, compute signals with their settings
                for user_id in all_user_ids:
                    user_settings_obj = await UserService.get_user_settings(db, user_id)
                    
                    if not user_settings_obj:
                        continue
                    
                    # Determine if this is a discovery signal for this user
                    is_discovery_signal = user_id not in subscriber_ids
                    
                    # Convert to dict for signal engine
                    user_settings = {
                        "ff_threshold": user_settings_obj.ff_threshold,
                        "dte_pairs": user_settings_obj.dte_pairs,
                        "vol_point": user_settings_obj.vol_point,
                        "min_open_interest": user_settings_obj.min_open_interest,
                        "min_volume": user_settings_obj.min_volume,
                        "max_bid_ask_pct": user_settings_obj.max_bid_ask_pct,
                        "sigma_fwd_floor": user_settings_obj.sigma_fwd_floor
                    }
                    
                    # Compute signals
                    signals = compute_signals(chain, user_settings)
                    
                    # Process each signal
                    for signal_data in signals:
                        # Mark if this is a discovery signal
                        signal_data["is_discovery"] = is_discovery_signal
                        
                        # Check stability using expiry dates (not DTE)
                        should_alert, state = await stability_tracker.check_stability(
                            ticker=signal_data["ticker"],
                            front_expiry=signal_data["front_expiry"],
                            back_expiry=signal_data["back_expiry"],
                            ff_value=signal_data["ff_value"],
                            required_scans=user_settings_obj.stability_scans,
                            cooldown_minutes=user_settings_obj.cooldown_minutes
                        )
                        
                        if not should_alert:
                            logger.info(f"Signal for {ticker} not stable yet: {state}")
                            
                        if should_alert:
                            # Persist signal to database (transaction auto-committed by context manager)
                            signal = await SignalService.create_signal(db, signal_data)
                            
                            if signal:
                                # Signal was created (not a duplicate), queue for notification
                                logger.info(f"Created signal {signal.id} for {ticker} (discovery={is_discovery_signal})")
                                await redis.lpush("notification_queue", signal.id)
                            else:
                                # Signal was a duplicate, skip notification
                                logger.debug(f"Skipped duplicate signal for {ticker}")
                        else:
                            logger.debug(f"Signal did not meet stability: {state}")
                
                # Update last scan time
                await TickerService.update_last_scan(db, ticker)
                
            # Transaction is automatically committed when the async with block exits
            logger.info(f"Completed scan for {ticker}")
                
        except Exception as e:
            logger.error(f"Error scanning {ticker}: {e}", exc_info=True)
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.provider.close()
        if self.redis:
            await self.redis.close()
    
    async def run(self):
        """Run worker loop, processing scan jobs from Redis queues."""
        logger.info("Scan worker started")
        redis = await self._get_redis()
        
        try:
            while True:
                try:
                    # Check for regular scan jobs first (higher priority)
                    result = await redis.brpop("scan_queue", timeout=1)
                    
                    if result:
                        queue_name, ticker = result
                        await self.scan_ticker(ticker, is_discovery=False)
                        continue
                    
                    # Check discovery queue
                    result = await redis.brpop("discovery_queue", timeout=1)
                    
                    if result:
                        queue_name, ticker = result
                        await self.scan_ticker(ticker, is_discovery=True)
                        continue
                    
                    # No jobs in either queue, sleep briefly
                    await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Worker error: {e}", exc_info=True)
                    await asyncio.sleep(5)
        finally:
            await self.cleanup()


async def main():
    """Main entry point for scan worker."""
    worker = ScanWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
