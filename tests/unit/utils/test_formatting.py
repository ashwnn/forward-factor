"""Unit tests for Formatting Utils.

This module tests message formatting functions for Telegram notifications.
"""
import pytest
from datetime import date

# Mock imports
from app.utils.formatting import (
    format_signal_message,
    format_reminder_message,
    format_watchlist,
    format_history
)


# ============================================================================
# Tests for format_signal_message
# ============================================================================

@pytest.mark.unit
class TestFormatSignal:
    """Test format_signal_message function."""
    
    def test_format_full_signal(self):
        """✅ Format complete signal dictionary."""
        signal = {
            "ticker": "SPY",
            "ff_value": 0.0512,
            "front_iv": 0.15,
            "back_iv": 0.12,
            "sigma_fwd": 0.10,
            "front_dte": 30,
            "back_dte": 60,
            "front_expiry": date(2025, 1, 1),
            "back_expiry": date(2025, 2, 1),
            "underlying_price": 450.50,
            "vol_point": "ATM"
        }
        
        msg = format_signal_message(signal)
        
        assert "Forward Factor Signal: SPY" in msg
        assert "Forward Factor: 5.12%" in msg
        assert "Front IV (30d): 15.00%" in msg
        assert "Back IV (60d): 12.00%" in msg
        assert "Underlying: $450.50" in msg
        assert "Vol Point: ATM" in msg


# ============================================================================
# Tests for format_reminder_message
# ============================================================================

@pytest.mark.unit
class TestFormatReminder:
    """Test format_reminder_message function."""
    
    def test_one_day_before(self):
        """✅ One day before reminder."""
        signal = {
            "ticker": "SPY",
            "front_expiry": date(2025, 1, 1),
            "back_expiry": date(2025, 2, 1),
            "back_dte": 30,
            "ff_value": 0.05,
            "front_iv": 0.15,
            "back_iv": 0.12,
            "underlying_price": 450.0
        }
        
        msg = format_reminder_message(signal, "one_day_before")
        
        assert "Front Leg Expiring Tomorrow" in msg
        assert "SPY Calendar Spread" in msg
        assert "Action Needed" in msg
    
    def test_expiry_day(self):
        """✅ Expiry day reminder."""
        signal = {
            "ticker": "SPY",
            "front_expiry": date(2025, 1, 1),
            "back_expiry": date(2025, 2, 1),
            "back_dte": 30
        }
        
        msg = format_reminder_message(signal, "expiry_day")
        
        assert "Front Leg Expires TODAY" in msg
        assert "Immediate Action Needed" in msg
    
    def test_unknown_type(self):
        """✅ Unknown reminder type."""
        msg = format_reminder_message({"ticker": "SPY"}, "unknown")
        assert "Reminder for SPY trade" in msg


# ============================================================================
# Tests for format_watchlist
# ============================================================================

@pytest.mark.unit
class TestFormatWatchlist:
    """Test format_watchlist function."""
    
    def test_empty_watchlist(self):
        """✅ Empty watchlist message."""
        assert "Your watchlist is empty" in format_watchlist([])
    
    def test_populated_watchlist(self):
        """✅ List of tickers formatted correctly."""
        tickers = ["SPY", "QQQ", "IWM"]
        msg = format_watchlist(tickers)
        
        assert "Your Watchlist (3 tickers)" in msg
        assert "• SPY" in msg
        assert "• QQQ" in msg
        assert "• IWM" in msg


# ============================================================================
# Tests for format_history
# ============================================================================

@pytest.mark.unit
class TestFormatHistory:
    """Test format_history function."""
    
    def test_empty_history(self):
        """✅ Empty history message."""
        assert "No signal history yet" in format_history([])
    
    def test_populated_history(self):
        """✅ History items formatted correctly."""
        decisions = [
            {
                "ticker": "SPY",
                "ff_value": 0.05,
                "decision": "placed",
                "decision_ts": "2025-01-01 10:00"
            },
            {
                "ticker": "QQQ",
                "ff_value": 0.03,
                "decision": "ignored",
                "decision_ts": "2025-01-01 11:00"
            }
        ]
        
        msg = format_history(decisions)
        
        assert "Recent Signals" in msg
        assert "✅ SPY" in msg
        assert "❌ QQQ" in msg
        assert "FF: 5.00%" in msg
