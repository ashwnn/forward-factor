"""Reminder worker for sending scheduled trade reminders."""
import logging
import asyncio
import json
from datetime import datetime, timezone
from telegram import Bot
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.models import Signal, User
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReminderWorker:
    """Worker for processing scheduled trade reminders."""
    
    def __init__(self):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    def format_reminder_message(self, signal: Signal, reminder_type: str) -> str:
        """
        Format reminder message based on type.
        
        Args:
            signal: Signal object
            reminder_type: Type of reminder ("one_day_before" or "expiry_day")
            
        Returns:
            Formatted message string
        """
        if reminder_type == "one_day_before":
            return f"""⚠️ **ACTION REQUIRED** ⚠️

📅 **Front Leg Expiring Tomorrow**

{signal.ticker} Calendar Spread:
• Front: {signal.front_expiry.strftime('%Y-%m-%d')} (expires tomorrow)
• Back: {signal.back_expiry.strftime('%Y-%m-%d')} ({signal.back_dte} DTE)

🔔 **Action Needed**: Consider closing or rolling your position before front expiration.

Original Signal Details:
• Forward Factor: {signal.ff_value:.2%}
• Front IV: {signal.front_iv:.2%}
• Back IV: {signal.back_iv:.2%}
• Underlying: ${signal.underlying_price:.2f if signal.underlying_price else 'N/A'}
"""
        
        elif reminder_type == "expiry_day":
            return f"""⚠️ **ACTION REQUIRED** ⚠️

📅 **Front Leg Expires TODAY**

{signal.ticker} Calendar Spread:
• Front: {signal.front_expiry.strftime('%Y-%m-%d')} (**EXPIRES TODAY**)
• Back: {signal.back_expiry.strftime('%Y-%m-%d')} ({signal.back_dte} DTE)

🔔 **Immediate Action Needed**: Close or roll your position today before market close.

Original Signal Details:
• Forward Factor: {signal.ff_value:.2%}
• Front IV: {signal.front_iv:.2%}
• Back IV: {signal.back_iv:.2%}
• Underlying: ${signal.underlying_price:.2f if signal.underlying_price else 'N/A'}
"""
        else:
            return f"Reminder for {signal.ticker} trade"
    
    async def send_reminder(self, reminder: dict):
        """
        Send a reminder notification to a user.
        
        Args:
            reminder: Reminder dictionary with signal_id, user_id, type
        """
        try:
            async with AsyncSessionLocal() as db:
                # Get signal
                result = await db.execute(
                    select(Signal).where(Signal.id == reminder["signal_id"])
                )
                signal = result.scalar_one_or_none()
                
                if not signal:
                    logger.warning(f"Signal {reminder['signal_id']} not found for reminder")
                    return
                
                # Get user
                result = await db.execute(
                    select(User).where(User.id == reminder["user_id"])
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.telegram_chat_id:
                    logger.warning(f"User {reminder['user_id']} not found or has no chat_id")
                    return
                
                # Format message
                message = self.format_reminder_message(signal, reminder["type"])
                
                # Send message
                await self.bot.send_message(
                    chat_id=user.telegram_chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                
                logger.info(
                    f"Sent {reminder['type']} reminder to user {user.telegram_chat_id} "
                    f"for signal {signal.id}"
                )
                
        except Exception as e:
            logger.error(f"Error sending reminder: {e}", exc_info=True)
    
    async def process_due_reminders(self):
        """Check for and process due reminders."""
        try:
            redis = await self._get_redis()
            now = datetime.now(timezone.utc).timestamp()
            
            # Get reminders due now (score <= now)
            due_reminders = await redis.zrangebyscore(
                "reminder_queue",
                min=0,
                max=now
            )
            
            if due_reminders:
                logger.info(f"Processing {len(due_reminders)} due reminders")
            
            for reminder_json in due_reminders:
                try:
                    reminder = json.loads(reminder_json)
                    
                    # Send the reminder
                    await self.send_reminder(reminder)
                    
                    # Remove from queue
                    await redis.zrem("reminder_queue", reminder_json)
                    
                except Exception as e:
                    logger.error(f"Error processing individual reminder: {e}", exc_info=True)
                    # Still remove it to avoid infinite retries
                    await redis.zrem("reminder_queue", reminder_json)
        
        except Exception as e:
            logger.error(f"Error in process_due_reminders: {e}", exc_info=True)
    
    async def run(self):
        """Run reminder worker loop."""
        logger.info("Reminder worker started")
        
        while True:
            try:
                await self.process_due_reminders()
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in reminder worker loop: {e}", exc_info=True)
                await asyncio.sleep(60)


async def main():
    """Main entry point for reminder worker."""
    worker = ReminderWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
