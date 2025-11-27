"""Telegram message formatting utilities."""
from datetime import datetime, timezone
from typing import Dict, Any


def format_signal_message(signal: Dict[str, Any]) -> str:
    """
    Format a signal into a Telegram message.
    
    Args:
        signal: Signal dictionary with all computed fields
        
    Returns:
        Formatted message string
    """
    ticker = signal.get("ticker", "")
    ff_value = signal.get("ff_value", 0.0)
    front_iv = signal.get("front_iv", 0.0)
    back_iv = signal.get("back_iv", 0.0)
    sigma_fwd = signal.get("sigma_fwd", 0.0)
    front_dte = signal.get("front_dte", 0)
    back_dte = signal.get("back_dte", 0)
    front_expiry = signal.get("front_expiry", "")
    back_expiry = signal.get("back_expiry", "")
    underlying_price = signal.get("underlying_price", 0.0)
    vol_point = signal.get("vol_point", "ATM")
    
    # Format percentages
    ff_pct = ff_value * 100
    front_iv_pct = front_iv * 100
    back_iv_pct = back_iv * 100
    sigma_fwd_pct = sigma_fwd * 100
    
    message = f"""
🚨 Forward Factor Signal: {ticker}

📊 Forward Factor: {ff_pct:.2f}%
Front IV ({front_dte}d): {front_iv_pct:.2f}%
Back IV ({back_dte}d): {back_iv_pct:.2f}%
Implied Forward IV: {sigma_fwd_pct:.2f}%

📅 Expiries:
Front: {front_expiry} ({front_dte} DTE)
Back: {back_expiry} ({back_dte} DTE)

💰 Underlying: ${underlying_price:.2f}
📍 Vol Point: {vol_point}

📋 Strategy: Calendar Spread
Sell front expiry, Buy back expiry
Same strike (ATM or near)

⚠️ Note: Wealthsimple spread support varies by account.
Close before front expiry.

🕐 Signal Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
    """.strip()
    
    return message



def format_reminder_message(signal_dict: dict, reminder_type: str) -> str:
    """
    Format a trade reminder message.
    
    Args:
        signal_dict: Dictionary with signal data
        reminder_type: Type of reminder ("one_day_before" or "expiry_day")
        
    Returns:
        Formatted reminder message
    """
    ticker = signal_dict.get('ticker', 'UNKNOWN')
    front_expiry = signal_dict.get('front_expiry', 'Unknown')
    back_expiry = signal_dict.get('back_expiry', 'Unknown')
    back_dte = signal_dict.get('back_dte', 0)
    ff_value = signal_dict.get('ff_value', 0)
    front_iv = signal_dict.get('front_iv', 0)
    back_iv = signal_dict.get('back_iv', 0)
    underlying_price = signal_dict.get('underlying_price', None)
    
    price_str = f"${underlying_price:.2f}" if underlying_price else "N/A"
    
    if reminder_type == "one_day_before":
        return f"""⚠️ **ACTION REQUIRED** ⚠️

📅 **Front Leg Expiring Tomorrow**

{ticker} Calendar Spread:
• Front: {front_expiry} (expires tomorrow)
• Back: {back_expiry} ({back_dte} DTE)

🔔 **Action Needed**: Consider closing or rolling your position before front expiration.

Original Signal Details:
• Forward Factor: {ff_value:.2%}
• Front IV: {front_iv:.2%}
• Back IV: {back_iv:.2%}
• Underlying: {price_str}
"""
    
    elif reminder_type == "expiry_day":
        return f"""⚠️ **ACTION REQUIRED** ⚠️

📅 **Front Leg Expires TODAY**

{ticker} Calendar Spread:
• Front: {front_expiry} (**EXPIRES TODAY**)
• Back: {back_expiry} ({back_dte} DTE)

🔔 **Immediate Action Needed**: Close or roll your position today before market close.

Original Signal Details:
• Forward Factor: {ff_value:.2%}
• Front IV: {front_iv:.2%}
• Back IV: {back_iv:.2%}
• Underlying: {price_str}
"""
    
    return f"Reminder for {ticker} trade"

def format_watchlist(tickers: list) -> str:
    """
    Format watchlist for display.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Formatted watchlist string
    """
    if not tickers:
        return "Your watchlist is empty. Use /add TICKER to add tickers."
    
    ticker_list = "\n".join([f"• {ticker}" for ticker in sorted(tickers)])
    return f"📋 Your Watchlist ({len(tickers)} tickers):\n\n{ticker_list}"


def format_history(decisions: list) -> str:
    """
    Format decision history for display.
    
    Args:
        decisions: List of decision dictionaries
        
    Returns:
        Formatted history string
    """
    if not decisions:
        return "No signal history yet."
    
    lines = ["📜 Recent Signals:\n"]
    
    for dec in decisions[:10]:  # Show last 10
        ticker = dec.get("ticker", "")
        ff_value = dec.get("ff_value", 0.0) * 100
        decision = dec.get("decision", "")
        decision_ts = dec.get("decision_ts", "")
        
        emoji = "✅" if decision == "placed" else "❌"
        lines.append(f"{emoji} {ticker} | FF: {ff_value:.2f}% | {decision} | {decision_ts}")
    
    return "\n".join(lines)
