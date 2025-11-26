"""Notification router for sending signals to users."""
import logging
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.services import SignalService, UserService, SubscriptionService
from app.utils.formatting import format_signal_message
from app.utils.time import is_in_quiet_hours
from sqlalchemy import select
from app.models import Signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationRouter:
    """Router for sending signal notifications to subscribed users."""
    
    def __init__(self):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.redis = None
    
    async def _get_redis(self):
        """Get Redis connection."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def send_signal_to_user(self, signal: Signal, user_id: str, chat_id: str):
        """
        Send signal notification to a single user.
        
        Args:
            signal: Signal object
            user_id: User ID
            chat_id: Telegram chat ID
        """
        try:
            # Get user settings for quiet hours check
            async with AsyncSessionLocal() as db:
                user_settings = await UserService.get_user_settings(db, user_id)
                
                if not user_settings:
                    return
                
                # Check quiet hours
                if is_in_quiet_hours(user_settings.quiet_hours, user_settings.timezone):
                    logger.info(f"User {chat_id} in quiet hours, skipping notification")
                    return
            
            # Format message
            signal_dict = {
                "ticker": signal.ticker,
                "ff_value": signal.ff_value,
                "front_iv": signal.front_iv,
                "back_iv": signal.back_iv,
                "sigma_fwd": signal.sigma_fwd,
                "front_dte": signal.front_dte,
                "back_dte": signal.back_dte,
                "front_expiry": signal.front_expiry,
                "back_expiry": signal.back_expiry,
                "underlying_price": signal.underlying_price,
                "vol_point": signal.vol_point
            }
            
            message = format_signal_message(signal_dict)
            
            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Place Trade", callback_data=f"place:{signal.id}:{user_id}"),
                    InlineKeyboardButton("❌ Ignore", callback_data=f"ignore:{signal.id}:{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send message
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup
            )
            
            logger.info(f"Sent signal {signal.id} to user {chat_id}")
            
        except Exception as e:
            logger.error(f"Error sending signal to {chat_id}: {e}", exc_info=True)
    
    async def process_notification(self, signal_id: str):
        """
        Process a notification from the queue.
        
        Args:
            signal_id: Signal ID to notify about
        """
        try:
            async with AsyncSessionLocal() as db:
                # Get signal
                result = await db.execute(
                    select(Signal).where(Signal.id == signal_id)
                )
                signal = result.scalar_one_or_none()
                
                if not signal:
                    logger.warning(f"Signal {signal_id} not found")
                    return
                
                # Get all subscribers for this ticker
                subscriber_ids = await SubscriptionService.get_ticker_subscribers(db, signal.ticker)
                
                # Send to each subscriber
                for user_id in subscriber_ids:
                    # Get user's chat ID
                    from app.models import User
                    result = await db.execute(
                        select(User).where(User.id == user_id)
                    )
                    user_obj = result.scalar_one_or_none()
                    
                    if user_obj and user_obj.telegram_chat_id:
                        await self.send_signal_to_user(signal, str(user_id), user_obj.telegram_chat_id)
                    elif user_obj:
                        logger.warning(f"User {user_id} has no telegram_chat_id, skipping notification")
                    else:
                        logger.warning(f"User {user_id} not found, skipping notification")
                        
        except Exception as e:
            logger.error(f"Error processing notification {signal_id}: {e}", exc_info=True)
    
    async def run(self):
        """Run notification router loop."""
        logger.info("Notification router started")
        redis = await self._get_redis()
        
        while True:
            try:
                # Block and wait for notification job
                result = await redis.brpop("notification_queue", timeout=5)
                
                if result:
                    queue_name, signal_id = result
                    await self.process_notification(signal_id)
                else:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Router error: {e}", exc_info=True)
                await asyncio.sleep(5)


async def main():
    """Main entry point for notification router."""
    router = NotificationRouter()
    await router.run()


if __name__ == "__main__":
    asyncio.run(main())
