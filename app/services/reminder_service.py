"""Reminder service for scheduling trade reminders."""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from app.core.redis import get_redis
from app.models import Signal

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing trade reminders."""
    
    @staticmethod
    async def schedule_trade_reminders(
        signal: Signal,
        user_id: str,
        user_timezone: str = "America/New_York"
    ) -> None:
        """
        Schedule reminder notifications for a placed trade.
        
        Schedules two reminders:
        1. One day before front expiry at market open (9:30 AM ET)
        2. On expiry day at market open (9:30 AM ET)
        
        Args:
            signal: Signal object with expiry dates
            user_id: User ID to send reminders to
            user_timezone: User's timezone (default: America/New_York for ET)
        """
        try:
            redis = await get_redis()
            
            # Calculate reminder times (using front_expiry as date)
            front_expiry_date = signal.front_expiry
            
            # Use Eastern Time for market hours
            eastern = ZoneInfo("America/New_York")
            
            # 1. One day before at market open (9:30 AM ET)
            one_day_before_local = datetime.combine(
                front_expiry_date - timedelta(days=1),
                datetime.min.time().replace(hour=9, minute=30)
            )
            # Make timezone-aware and convert to UTC
            one_day_before = one_day_before_local.replace(tzinfo=eastern).astimezone(timezone.utc)
            
            # 2. Expiry day at market open (9:30 AM ET)
            expiry_day_local = datetime.combine(
                front_expiry_date,
                datetime.min.time().replace(hour=9, minute=30)
            )
            # Make timezone-aware and convert to UTC
            expiry_day_open = expiry_day_local.replace(tzinfo=eastern).astimezone(timezone.utc)
            
            # Only schedule if time is in the future
            now = datetime.now(timezone.utc)
            
            reminders = []
            
            if one_day_before > now:
                reminders.append({
                    "signal_id": str(signal.id),
                    "user_id": str(user_id),
                    "type": "one_day_before",
                    "priority": "high",
                    "scheduled_at": one_day_before.isoformat()
                })
            
            if expiry_day_open > now:
                reminders.append({
                    "signal_id": str(signal.id),
                    "user_id": str(user_id),
                    "type": "expiry_day",
                    "priority": "high",
                    "scheduled_at": expiry_day_open.isoformat()
                })
            
            # Add to Redis sorted set (score = timestamp)
            for reminder in reminders:
                reminder_key = json.dumps(reminder, sort_keys=True)
                timestamp = datetime.fromisoformat(reminder["scheduled_at"]).timestamp()
                
                await redis.zadd(
                    "reminder_queue",
                    {reminder_key: timestamp}
                )
                
                logger.info(
                    f"Scheduled {reminder['type']} reminder for user {user_id}, "
                    f"signal {signal.id} at {reminder['scheduled_at']}"
                )
            
            logger.info(f"Scheduled {len(reminders)} reminders for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error scheduling reminders: {e}", exc_info=True)
    
    @staticmethod
    async def cancel_reminders(signal_id: str, user_id: str) -> int:
        """
        Cancel all reminders for a specific signal and user.
        
        Args:
            signal_id: Signal ID
            user_id: User ID
            
        Returns:
            Number of reminders cancelled
        """
        try:
            redis = await get_redis()
            
            # Get all reminders from sorted set
            all_reminders = await redis.zrange("reminder_queue", 0, -1)
            
            cancelled = 0
            for reminder_json in all_reminders:
                reminder = json.loads(reminder_json)
                if reminder["signal_id"] == str(signal_id) and reminder["user_id"] == str(user_id):
                    await redis.zrem("reminder_queue", reminder_json)
                    cancelled += 1
            
            logger.info(f"Cancelled {cancelled} reminders for signal {signal_id}, user {user_id}")
            return cancelled
            
        except Exception as e:
            logger.error(f"Error cancelling reminders: {e}", exc_info=True)
            return 0
    
    @staticmethod
    async def get_pending_reminders(user_id: Optional[str] = None) -> list:
        """
        Get pending reminders, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of pending reminder dictionaries
        """
        try:
            redis = await get_redis()
            
            # Get all reminders from sorted set
            all_reminders = await redis.zrange("reminder_queue", 0, -1, withscores=True)
            
            pending = []
            for reminder_json, score in all_reminders:
                reminder = json.loads(reminder_json)
                reminder["scheduled_timestamp"] = score
                
                if user_id is None or reminder["user_id"] == str(user_id):
                    pending.append(reminder)
            
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending reminders: {e}", exc_info=True)
            return []
