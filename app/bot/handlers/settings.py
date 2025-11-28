"""Settings management handlers."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services import UserService
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /settings command.
    Shows current settings and instructions to change them.
    """
    try:
        chat_id = str(update.effective_chat.id)
        
        async with AsyncSessionLocal() as db:
            user = await UserService.get_user_by_chat_id(db, chat_id)
            
            if not user:
                await update.message.reply_text("Please use /start <invite_code> to initialize your account.")
                return
                
            settings = await UserService.get_user_settings(db, user.id)
            
            if not settings:
                await update.message.reply_text("Error retrieving settings.")
                return
            
            message = f"""
⚙️ **Your Settings**

**Thresholds**
• FF Threshold: {settings.ff_threshold:.0%} (`ff_threshold`)
• Min Forward Vol: {settings.sigma_fwd_floor:.0%} (`sigma_fwd_floor`)

**Filters**
• Min Open Interest: {settings.min_open_interest} (`min_oi`)
• Min Volume: {settings.min_volume} (`min_vol`)
• Max Bid/Ask Spread: {settings.max_bid_ask_pct:.0%} (`max_spread`)

**Scan & Alerts**
• Scan Priority: {settings.scan_priority} (`priority`)
• Stability Scans: {settings.stability_scans} (`stability`)
• Cooldown: {settings.cooldown_minutes}m (`cooldown`)
• Discovery Mode: {'ON' if settings.discovery_mode else 'OFF'} (`discovery`)

**General**
• Timezone: {settings.timezone} (`timezone`)

**To change a setting:**
Use `/set <key> <value>`

Examples:
`/set ff_threshold 0.25` (Set FF to 25%)
`/set min_oi 500` (Set min OI to 500)
`/set priority high` (Set scan priority to high)
`/set timezone America/New_York`
            """.strip()
            
            await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in settings_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred processing your request. Please try again later."
        )


async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /set command.
    Usage: /set <key> <value>
    """
    try:
        chat_id = str(update.effective_chat.id)
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/set <key> <value>`\\nExample: `/set ff_threshold 0.25`",
                parse_mode="Markdown"
            )
            return
        
        key = context.args[0].lower()
        value_str = context.args[1]
        
        #Map friendly keys to DB columns and types
        key_map = {
            "ff_threshold": ("ff_threshold", float),
            "sigma_fwd_floor": ("sigma_fwd_floor", float),
            "min_oi": ("min_open_interest", int),
            "min_vol": ("min_volume", int),
            "max_spread": ("max_bid_ask_pct", float),
            "stability": ("stability_scans", int),
            "cooldown": ("cooldown_minutes", int),
            "timezone": ("timezone", str),
            "priority": ("scan_priority", str),
            "discovery": ("discovery_mode", bool)
        }
        
        if key not in key_map:
            await update.message.reply_text(f"❌ Unknown setting: `{key}`", parse_mode="Markdown")
            return
        
        db_key, type_func = key_map[key]
        
        try:
            # Validate and convert value
            if type_func == float:
                # Handle percentage inputs like "25%"
                clean_val = value_str.replace("%", "")
                value = float(clean_val)
                # If user enters 25 for 25%, convert to 0.25 if it's a percentage field
                if value > 1.0 and db_key in ["ff_threshold", "sigma_fwd_floor", "max_bid_ask_pct"]:
                    value = value / 100.0
            elif type_func == int:
                value = int(value_str)
            elif type_func == bool:
                # Handle boolean inputs
                value = value_str.lower() in ["true", "1", "on", "yes", "enabled"]
            else:
                value = value_str
                
            # Specific validation
            if db_key == "scan_priority" and value not in ["standard", "high", "turbo"]:
                await update.message.reply_text("❌ Priority must be: standard, high, or turbo")
                return
                
        except ValueError:
            await update.message.reply_text(f"❌ Invalid value for {key}")
            return
        
        async with AsyncSessionLocal() as db:
            user = await UserService.get_user_by_chat_id(db, chat_id)
            if not user:
                await update.message.reply_text("Please use /start <invite_code> to initialize your account.")
                return
                
            await UserService.update_user_settings(db, user.id, **{db_key: value})
            
            await update.message.reply_text(f"✅ Updated **{key}** to `{value}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in set_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred processing your request. Please try again later."
        )


async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /me command.
    Shows user's current settings and followed tickers.
    """
    try:
        chat_id = str(update.effective_chat.id)
        
        async with AsyncSessionLocal() as db:
            user = await UserService.get_user_by_chat_id(db, chat_id)
            
            if not user:
                await update.message.reply_text("Please use /start <invite_code> to initialize your account.")
                return
                
            settings = await UserService.get_user_settings(db, user.id)
            
            if not settings:
                await update.message.reply_text("Error retrieving settings.")
                return
            
            # Get subscriptions
            from app.services import SubscriptionService
            subscriptions = await SubscriptionService.get_user_subscriptions(db, user.id)
            tickers = [sub.ticker for sub in subscriptions]
            
            # Format tickers list
            if tickers:
                ticker_list = ", ".join(sorted(tickers))
            else:
                ticker_list = "None"
            
            message = f"""
👤 **Your Profile**

**Watchlist** ({len(tickers)} tickers)
{ticker_list}

**Key Settings**
• FF Threshold: {settings.ff_threshold:.0%}
• Min OI: {settings.min_open_interest} | Min Vol: {settings.min_volume}
• Priority: {settings.scan_priority}
• Discovery Mode: {'🟢 ON' if settings.discovery_mode else '🔴 OFF'}
• Timezone: {settings.timezone}

Use /settings to view all settings or /set to change them.
            """.strip()
            
            await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in me_command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An error occurred processing your request. Please try again later."
        )
