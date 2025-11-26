"""Callback query handlers for inline buttons."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService, SignalService
from app.core.database import AsyncSessionLocal
from datetime import datetime

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
            if len(parts) != 3 or parts[0] != "signal":
                await query.edit_message_text("Invalid callback data")
                return
                
            signal_id = parts[1]
            action = parts[2]
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
            
            # Record decision
            await SignalService.record_decision(
                db,
                signal_id=signal_id,
                user_id=user.id,
                decision=action,
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "via": "telegram_callback"
                }
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

