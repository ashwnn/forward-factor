"""Settings management handlers (stub for future implementation)."""
from telegram import Update
from telegram.ext import ContextTypes


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /settings command.
    
    Future implementation: Allow users to configure:
    - FF threshold
    - DTE pairs
    - Vol point (ATM, delta-based)
    - Liquidity filters
    - Quiet hours
    """
    await update.message.reply_text(
        "Settings management coming soon!\n\n"
        "Currently using default settings:\n"
        "- FF Threshold: 20%\n"
        "- DTE Pairs: 30/60, 30/90, 60/90\n"
        "- Vol Point: ATM\n"
        "- Timezone: America/Vancouver"
    )
