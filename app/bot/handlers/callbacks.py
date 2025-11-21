"""Callback query handlers for inline buttons."""
from telegram import Update
from telegram.ext import ContextTypes
from app.services import SignalService
from app.core.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle inline button callbacks (Place/Ignore).
    
    Callback data format: "action:signal_id:user_id"
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # Parse callback data
        parts = query.data.split(":")
        if len(parts) != 3:
            await query.edit_message_text("Invalid callback data.")
            return
        
        action, signal_id, user_id = parts
        
        # Verify user
        chat_id = str(update.effective_chat.id)
        
        async with AsyncSessionLocal() as db:
            # Record decision
            decision = "placed" if action == "place" else "ignored"
            await SignalService.record_decision(
                db,
                signal_id=signal_id,
                user_id=user_id,
                decision=decision,
                metadata={"chat_id": chat_id}
            )
            
            # Update message
            if action == "place":
                emoji = "✅"
                text = "Trade Placed"
            else:
                emoji = "❌"
                text = "Ignored"
            
            # Edit message to show decision
            original_text = query.message.text
            updated_text = f"{original_text}\n\n{emoji} {text}"
            
            await query.edit_message_text(updated_text)
            
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await query.edit_message_text("Error processing your action.")
