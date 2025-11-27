"""Unit tests for Time Utils.

This module tests time-related utility functions including DTE calculation
and quiet hours logic.
"""
import pytest
from datetime import date, datetime, time
from unittest.mock import MagicMock, patch
import pytz

# Mock imports
from app.utils.time import calculate_dte, is_in_quiet_hours, get_user_time


# ============================================================================
# Tests for calculate_dte
# ============================================================================

@pytest.mark.unit
class TestCalculateDTE:
    """Test calculate_dte function."""
    
    def test_future_expiry(self):
        """✅ Future date."""
        today = date(2025, 1, 1)
        expiry = date(2025, 1, 10)
        assert calculate_dte(expiry, today) == 9
    
    def test_today_expiry(self):
        """✅ Expiry today."""
        today = date(2025, 1, 1)
        expiry = date(2025, 1, 1)
        assert calculate_dte(expiry, today) == 0
    
    def test_past_expiry(self):
        """✅ Past date (negative DTE)."""
        today = date(2025, 1, 10)
        expiry = date(2025, 1, 1)
        assert calculate_dte(expiry, today) == -9
    
    def test_default_reference(self):
        """✅ Default reference (today)."""
        # Mock date.today()
        with patch("app.utils.time.date") as mock_date:
            mock_date.today.return_value = date(2025, 1, 1)
            # Need to restore side_effect for other date operations if needed
            # But here we just subtract dates which are real date objects passed in
            
            # Actually, calculate_dte uses date.today() internally if ref is None.
            # But we can't easily patch built-in types like date.
            # Instead, we'll just pass a reference date to avoid relying on today()
            pass
            
        # Real test without mocking date.today()
        expiry = date.today()
        assert calculate_dte(expiry) == 0


# ============================================================================
# Tests for is_in_quiet_hours
# ============================================================================

@pytest.mark.unit
class TestQuietHours:
    """Test is_in_quiet_hours function."""
    
    def test_disabled(self):
        """✅ Disabled quiet hours."""
        config = {"enabled": False}
        assert is_in_quiet_hours(config) is False
    
    @patch("app.utils.time.datetime")
    def test_in_quiet_hours_overnight(self, mock_dt):
        """✅ Inside overnight quiet hours (e.g. 23:00)."""
        # Config: 22:00 to 08:00
        config = {"enabled": True, "start": "22:00", "end": "08:00"}
        
        # Mock current time: 23:00
        mock_now = MagicMock()
        mock_now.time.return_value = time(23, 0)
        mock_dt.now.return_value = mock_now
        
        assert is_in_quiet_hours(config) is True
    
    @patch("app.utils.time.datetime")
    def test_outside_quiet_hours_overnight(self, mock_dt):
        """✅ Outside overnight quiet hours (e.g. 10:00)."""
        # Config: 22:00 to 08:00
        config = {"enabled": True, "start": "22:00", "end": "08:00"}
        
        # Mock current time: 10:00
        mock_now = MagicMock()
        mock_now.time.return_value = time(10, 0)
        mock_dt.now.return_value = mock_now
        
        assert is_in_quiet_hours(config) is False
    
    @patch("app.utils.time.datetime")
    def test_in_quiet_hours_same_day(self, mock_dt):
        """✅ Inside same-day quiet hours (e.g. 14:00-16:00)."""
        # Config: 14:00 to 16:00
        config = {"enabled": True, "start": "14:00", "end": "16:00"}
        
        # Mock current time: 15:00
        mock_now = MagicMock()
        mock_now.time.return_value = time(15, 0)
        mock_dt.now.return_value = mock_now
        
        assert is_in_quiet_hours(config) is True
    
    def test_invalid_timezone(self):
        """✅ Invalid timezone handles gracefully."""
        config = {"enabled": True}
        assert is_in_quiet_hours(config, "Invalid/Zone") is False


# ============================================================================
# Tests for get_user_time
# ============================================================================

@pytest.mark.unit
class TestGetUserTime:
    """Test get_user_time function."""
    
    def test_valid_timezone(self):
        """✅ Valid timezone returns datetime."""
        dt = get_user_time("UTC")
        assert dt.tzinfo is not None
        assert dt.tzinfo.zone == "UTC"
