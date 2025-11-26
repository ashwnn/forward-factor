"""Start command handler."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService
from app.core.database import AsyncSessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.
    Creates user account if doesn't exist.
    """
    try:
        chat_id = str(update.effective_chat.id)
        
        async with AsyncSessionLocal() as db:
            # Check if user already exists
            user = await UserService.get_user_by_chat_id(db, chat_id)
            
            if not user:
                # Check for invite code
                if not context.args or context.args[0] != settings.invite_code:
                    await update.message.reply_text(
                        "🔒 Access Restricted\n\n"
                        "Please provide a valid invite code to start using this bot.\n"
                        "Usage: /start <invite_code>"
                    )
                    return
                
                # Create user if code is valid
                user = await UserService.get_or_create_user(db, chat_id)
            
            welcome_message = f"""
Welcome to Forward Factor Signal Bot!

I'll help you find calendar spread opportunities based on Forward Factor analysis.

Commands:
/add TICKER - Add a ticker to your watchlist
/remove TICKER - Remove a ticker from your watchlist
/list - Show your current watchlist
/history - View your recent signals and decisions
/help - Show this help message

Get started by adding some tickers to your watchlist!
Example: /add SPY
            """.strip()
            
            await update.message.reply_text(welcome_message)
    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred processing your request. Please try again later."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    try:
        help_text = """
Forward Factor Signal Bot Commands:

/start - Initialize your account
/add TICKER - Add ticker to watchlist (e.g., /add AAPL)
/remove TICKER - Remove ticker from watchlist
/list - Show your watchlist
/history - View recent signals and your decisions
/help - Show this message

About Forward Factor:
This bot scans option chains for calendar spread opportunities where front-month IV is elevated relative to the implied forward volatility. When a signal is found, you'll receive a notification with trade details.

Note: This bot does NOT execute trades automatically. All signals are for manual execution at your broker.
        """.strip()
        
        await update.message.reply_text(help_text)
    except Exception as e:
        logger.error(f"Error in help_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred processing your request. Please try again later."
        )
