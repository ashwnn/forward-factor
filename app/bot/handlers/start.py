"""Start command handler."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService, AuthService
from app.core.database import AsyncSessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.
    Links user account if code provided.
    """
    try:
        chat_id = str(update.effective_chat.id)
        telegram_username = update.effective_user.username  # Get username from Telegram
        
        async with AsyncSessionLocal() as db:
            # Check if user already exists
            user = await UserService.get_user_by_chat_id(db, chat_id)
            
            if user:
                await send_welcome_message(update)
                return
            
            # Not linked. Check for link code in args
            if context.args and len(context.args) > 0:
                link_code = context.args[0]
                user = await AuthService.verify_link_code(link_code, chat_id, telegram_username, db)
                
                if user:
                    await update.message.reply_text("✅ Account successfully linked!")
                    await send_welcome_message(update)
                    return
                else:
                    await update.message.reply_text("❌ Invalid link code. Please check your settings on the web dashboard.")
                    return
            
            # No code or invalid flow
            await update.message.reply_text(
                "⚠️ You must register on the web application before using the Telegram bot.\n\n"
                f"Please log in at {settings.frontend_url}/login and obtain your personal link code from Settings.\n\n"
                "Once you have the code, send it here or click the link in the dashboard."
            )
    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred processing your request. Please try again later."
        )


async def send_welcome_message(update: Update):
    """Send the welcome message."""
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
