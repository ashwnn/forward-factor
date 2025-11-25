"""Watchlist management command handlers."""
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService, SubscriptionService, TickerService
from app.core.database import AsyncSessionLocal
from app.utils.formatting import format_watchlist


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /add TICKER command.
    Adds a ticker to user's watchlist.
    """
    chat_id = str(update.effective_chat.id)
    
    # Check for ticker argument
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Please provide a ticker symbol.\nUsage: /add TICKER\nExample: /add AAPL"
        )
        return
    
    ticker = context.args[0].upper()
    
    async with AsyncSessionLocal() as db:
        # Get user
        user = await UserService.get_user_by_chat_id(db, chat_id)
        if not user:
            await update.message.reply_text("Please use /start <invite_code> to initialize your account.")
            return
        
        # Add subscription
        await SubscriptionService.add_subscription(db, user.id, ticker)
        
        # Update master ticker registry
        await TickerService.update_ticker_registry(db)
        
        await update.message.reply_text(
            f"✅ Added {ticker} to your watchlist.\n\n"
            f"You'll receive signals when Forward Factor opportunities are detected."
        )


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /remove TICKER command.
    Removes a ticker from user's watchlist.
    """
    chat_id = str(update.effective_chat.id)
    
    # Check for ticker argument
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Please provide a ticker symbol.\nUsage: /remove TICKER\nExample: /remove AAPL"
        )
        return
    
    ticker = context.args[0].upper()
    
    async with AsyncSessionLocal() as db:
        # Get user
        user = await UserService.get_user_by_chat_id(db, chat_id)
        if not user:
            await update.message.reply_text("Please use /start <invite_code> to initialize your account.")
            return
        
        # Remove subscription
        removed = await SubscriptionService.remove_subscription(db, user.id, ticker)
        
        if removed:
            # Update master ticker registry
            await TickerService.update_ticker_registry(db)
            
            await update.message.reply_text(f"✅ Removed {ticker} from your watchlist.")
        else:
            await update.message.reply_text(f"❌ {ticker} was not in your watchlist.")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /list command.
    Shows user's current watchlist.
    """
    chat_id = str(update.effective_chat.id)
    
    async with AsyncSessionLocal() as db:
        # Get user
        user = await UserService.get_user_by_chat_id(db, chat_id)
        if not user:
            await update.message.reply_text("Please use /start first to initialize your account.")
            return
        
        # Get subscriptions
        tickers = await SubscriptionService.get_user_subscriptions(db, user.id)
        
        message = format_watchlist(tickers)
        await update.message.reply_text(message)
