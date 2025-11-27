"""Telegram bot main entry point."""
import logging
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors globally for the Telegram bot.
    
    Logs the error and notifies the developer if configured.
    """
    logger.error("Exception while handling an update:")
    
    # Format the traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    
    # Log the full error with traceback
    logger.error(f"Exception: {context.error}")
    logger.error(f"Traceback:\n{tb_string}")
    
    # Log update info if available
    if update:
        if isinstance(update, Update):
            logger.error(f"Update ID: {update.update_id}")
            if update.effective_user:
                logger.error(f"User: {update.effective_user.id} (@{update.effective_user.username})")
            if update.effective_chat:
                logger.error(f"Chat: {update.effective_chat.id}")
            if update.effective_message:
                logger.error(f"Message: {update.effective_message.text}")
    
    # Send a message to the user if possible
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Sorry, an error occurred while processing your request. "
                "Please try again later."
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")


def main():
    """Start the Telegram bot."""
    logger.info("="*60)
    logger.info("Starting Telegram bot...")
    logger.info(f"Log level: {settings.log_level}")
    logger.debug(f"Bot token configured: {bool(settings.telegram_bot_token)}")
    logger.info("="*60)
    
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Register error handler
    application.add_error_handler(error_handler)
    
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
    logger.info("All handlers registered successfully")
    logger.info("="*60)
    logger.info("Bot started successfully - polling for updates")
    logger.info("="*60)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
