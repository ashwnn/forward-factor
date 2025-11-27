"""Callback query handlers for inline buttons."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService, SignalService
from app.core.database import AsyncSessionLocal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle callback queries from signal action buttons.
    
    Callback data format: "signal:<signal_id>:<action>"
    where action is "placed", "ignored", or "expired"
    """
    try:
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        try:
            parts = query.data.split(":")
            if len(parts) < 2:
                await query.edit_message_text("Invalid callback data")
                return
            
            action = parts[0]  # "place" or "ignore"
            signal_id = parts[1]
            # user_id is in parts[2] if present (from notification)
            
            # Map action names
            action_map = {
                "place": "placed",
                "ignore": "ignored"
            }
            action = action_map.get(action, action)
            
        except Exception:
            await query.edit_message_text("❌ Error parsing signal data")
            return
        
        # Get user
        chat_id = str(update.effective_chat.id)
        async with AsyncSessionLocal() as db:
            user = await UserService.get_user_by_chat_id(db, chat_id)
            if not user:
                await query.edit_message_text("❌ User not found")
                return
            
            # Get signal first to obtain as_of_ts for composite foreign key
            from app.models import Signal
            from sqlalchemy import select
            
            result = await db.execute(
                select(Signal).where(Signal.id == signal_id)
            )
            signal = result.scalar_one_or_none()
            
            if not signal:
                await query.edit_message_text("❌ Signal not found")
                return
            
            # Record decision with composite foreign key
            await SignalService.record_decision(
                db,
                signal_id=signal_id,
                signal_as_of_ts=signal.as_of_ts,
                user_id=user.id,
                decision=action,
                metadata={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "via": "telegram_callback"
                }
            )
            
            # If user placed the trade, schedule reminders
            if action == "placed":
                from app.services.reminder_service import ReminderService
                
                await ReminderService.schedule_trade_reminders(
                    signal=signal,
                    user_id=user.id
                )
        
        # Update message
        action_emoji = {
            "placed": "✅",
            "ignored": "🚫",
            "expired": "⏳"
        }
        
        await query.edit_message_text(
            f"{action_emoji.get(action, '✅')} Decision recorded: {action}"
        )
    except Exception as e:
        logger.error(f"Error in button_callback: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                "❌ An error occurred processing your request. Please try again later."
            )
        except:
            pass  # Message might be too old to edit

