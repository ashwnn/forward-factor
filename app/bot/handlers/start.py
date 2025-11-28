"""Start command handler."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService, AuthService
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.
    Links user account if code provided.
    """
    try:
        chat_id = str(update.effective_chat.id)
        # Extract user information from Telegram
        telegram_user = update.effective_user
        first_name = telegram_user.first_name  # Always available
        last_name = telegram_user.last_name    # Optional
        telegram_username = telegram_user.username  # Optional
        
        async with AsyncSessionLocal() as db:
            # Check if user already exists
            user = await UserService.get_user_by_chat_id(db, chat_id)
            
            if user:
                await send_welcome_message(update)
                return
            
            # Not linked. Check for link code in args
            if context.args and len(context.args) > 0:
                link_code = context.args[0]
                user = await AuthService.verify_link_code(
                    link_code, 
                    chat_id, 
                    first_name,
                    last_name,
                    telegram_username, 
                    db
                )
                
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
                "Please visit the web dashboard and obtain your personal link code from Settings.\n\n"
                "Once you have the code, use /start <your-link-code> or click the link in the dashboard."
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
/me - View your profile and settings
/add TICKER - Add a ticker to your watchlist
/remove TICKER - Remove a ticker from your watchlist
/list - Show your current watchlist
/settings - View all your settings
/set KEY VALUE - Change a setting
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
/me - View your profile, settings, and watchlist
/add TICKER - Add ticker to watchlist (e.g., /add AAPL)
/remove TICKER - Remove ticker from watchlist
/list - Show your watchlist
/history - View recent signals and your decisions
/settings - View all your settings
/set KEY VALUE - Change a setting (e.g., /set discovery on)
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
