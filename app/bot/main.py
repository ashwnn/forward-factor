"""Telegram bot main entry point."""
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, Update
from app.core.config import settings
from app.bot.handlers.start import start_command, help_command
from app.bot.handlers.watchlist import add_command, remove_command, list_command
from app.bot.handlers.history import history_command
from app.bot.handlers.callbacks import button_callback
from app.bot.handlers.settings import settings_command, set_command

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level)
)
logger = logging.getLogger(__name__)


def main():
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot...")
    
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("set", set_command))
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start bot
    logger.info("Bot started successfully")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
