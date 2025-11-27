"""Stability tracker using Redis for signal debouncing."""
from typing import Optional
from datetime import datetime, timedelta, date, timezone
from app.core.redis import get_redis
import asyncio


class StabilityTracker:
    """Track signal stability across consecutive scans."""
    
    def __init__(self):
        self.redis = None
        self._lock = asyncio.Lock()
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis is None:
            async with self._lock:
                if self.redis is None:
                    self.redis = await get_redis()
        return self.redis
    
    def _make_key(self, ticker: str, front_expiry: date, back_expiry: date) -> str:
        """Create Redis key for a ticker/expiry pair using expiry dates.
        
        This prevents stability being reset when DTE changes day-to-day.
        """
        return f"stability:{ticker}:{front_expiry}:{back_expiry}"
    
    def _lock_key(self, ticker: str, front_expiry: date, back_expiry: date) -> str:
        """Create Redis lock key for atomic operations."""
        return f"stability_lock:{ticker}:{front_expiry}:{back_expiry}"
    
    async def check_stability(
        self,
        ticker: str,
        front_expiry: date,
        back_expiry: date,
        ff_value: float,
        required_scans: int = 2,
        cooldown_minutes: int = 120,
        delta_ff_min: float = 0.02
    ) -> tuple[bool, dict]:
        """
        Check if signal meets stability requirements.
        
        Uses Redis SETNX-based locking for atomic read-modify-write operations.
        
        Args:
            ticker: Ticker symbol
            front_expiry: Front expiry date
            back_expiry: Back expiry date
            ff_value: Current FF value
            required_scans: Number of consecutive scans required
            cooldown_minutes: Cooldown period between alerts
            delta_ff_min: Minimum FF increase to re-alert
            
        Returns:
            (should_alert, state_dict) tuple
        """
        redis = await self._get_redis()
        key = self._make_key(ticker, front_expiry, back_expiry)
        lock_key = self._lock_key(ticker, front_expiry, back_expiry)
        
        # Acquire lock with retry
        max_retries = 10
        for attempt in range(max_retries):
            acquired = await redis.setnx(lock_key, "1")
            if acquired:
                await redis.expire(lock_key, 5)  # 5 second lock timeout
                break
            await asyncio.sleep(0.1)
        else:
            # Lock acquisition failed after retries
            return False, {"consecutive_count": 0, "reason": "lock_failed"}
        
        try:
            # Get current state atomically
            state = await redis.hgetall(key)
            now = datetime.now(timezone.utc)
            
            if not state:
                # First time seeing this signal
                await redis.hset(key, mapping={
                    "last_ff": str(ff_value),
                    "consecutive_count": "1",
                    "last_alert_ts": "",
                    "first_seen": now.isoformat()
                })
                await redis.expire(key, 86400)  # 24 hour TTL
                return False, {"consecutive_count": 1, "reason": "first_scan"}
            
            last_ff = float(state.get("last_ff", 0))
            consecutive_count = int(state.get("consecutive_count", 0))
            last_alert_ts_str = state.get("last_alert_ts", "")
            
            # Update consecutive count
            consecutive_count += 1
            
            # Check cooldown
            if last_alert_ts_str:
                last_alert_ts = datetime.fromisoformat(last_alert_ts_str)
                # Ensure last_alert_ts is timezone-aware for comparison
                if last_alert_ts.tzinfo is None:
                    last_alert_ts = last_alert_ts.replace(tzinfo=timezone.utc)
                time_since_alert = (now - last_alert_ts).total_seconds() / 60
                
                if time_since_alert < cooldown_minutes:
                    await redis.hset(key, mapping={
                        "last_ff": str(ff_value),
                        "consecutive_count": str(consecutive_count)
                    })
                    return False, {
                        "consecutive_count": consecutive_count,
                        "reason": f"cooldown_{time_since_alert:.1f}min"
                    }
                
                # Check FF delta
                ff_delta = ff_value - last_ff
                if ff_delta < delta_ff_min:
                    await redis.hset(key, mapping={
                        "last_ff": str(ff_value),
                        "consecutive_count": str(consecutive_count)
                    })
                    return False, {
                        "consecutive_count": consecutive_count,
                        "reason": f"ff_delta_too_small_{ff_delta:.4f}"
                    }
            
            # Check if we have enough consecutive scans
            if consecutive_count < required_scans:
                await redis.hset(key, mapping={
                    "last_ff": str(ff_value),
                    "consecutive_count": str(consecutive_count)
                })
                return False, {
                    "consecutive_count": consecutive_count,
                    "reason": f"need_{required_scans}_scans"
                }
            
            # All checks passed - should alert
            await redis.hset(key, mapping={
                "last_ff": str(ff_value),
                "consecutive_count": str(consecutive_count),
                "last_alert_ts": now.isoformat()
            })
            
            return True, {"consecutive_count": consecutive_count, "reason": "stable"}
        finally:
            # Always release the lock
            await redis.delete(lock_key)
    
    async def reset(self, ticker: str, front_expiry: date, back_expiry: date):
        """Reset stability tracking for a ticker/expiry pair."""
        redis = await self._get_redis()
        key = self._make_key(ticker, front_expiry, back_expiry)
        await redis.delete(key)


# Global instance
stability_tracker = StabilityTracker()
