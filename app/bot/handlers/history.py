"""History command handler."""
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService, SignalService
from app.core.database import AsyncSessionLocal
from app.utils.formatting import format_history


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /history command.
    Shows user's recent signals and decisions.
    """
    chat_id = str(update.effective_chat.id)
    
    async with AsyncSessionLocal() as db:
        # Get user
        user = await UserService.get_user_by_chat_id(db, chat_id)
        if not user:
            await update.message.reply_text("Please use /start first to initialize your account.")
            return
        
        # Get decision history
        decisions = await SignalService.get_user_decisions(db, user.id, limit=20)
        
        message = format_history(decisions)
        await update.message.reply_text(message)
