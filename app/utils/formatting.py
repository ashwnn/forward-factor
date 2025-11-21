"""Telegram message formatting utilities."""
from datetime import datetime
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

🕐 Signal Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
    """.strip()
    
    return message


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
