"""Time utilities for DTE calculations and timezone handling."""
from datetime import date, datetime, time
from typing import Optional
import pytz


def calculate_dte(expiry_date: date, reference_date: Optional[date] = None) -> int:
    """
    Calculate days to expiry.
    
    Args:
        expiry_date: Option expiry date
        reference_date: Reference date (defaults to today)
        
    Returns:
        Number of calendar days to expiry
    """
    if reference_date is None:
        reference_date = date.today()
    
    return (expiry_date - reference_date).days


def is_in_quiet_hours(quiet_hours: dict, timezone_str: str = "America/Vancouver") -> bool:
    """
    Check if current time is within user's quiet hours.
    
    Args:
        quiet_hours: Dict with 'enabled', 'start', 'end' keys
        timezone_str: User's timezone
        
    Returns:
        True if in quiet hours, False otherwise
    """
    if not quiet_hours.get("enabled", False):
        return False
    
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz).time()
        
        start_str = quiet_hours.get("start", "22:00")
        end_str = quiet_hours.get("end", "08:00")
        
        start_time = time.fromisoformat(start_str)
        end_time = time.fromisoformat(end_str)
        
        # Handle overnight quiet hours (e.g., 22:00 to 08:00)
        if start_time > end_time:
            return now >= start_time or now <= end_time
        else:
            return start_time <= now <= end_time
            
    except Exception:
        return False


def get_user_time(timezone_str: str = "America/Vancouver") -> datetime:
    """
    Get current time in user's timezone.
    
    Args:
        timezone_str: User's timezone (default: America/Vancouver)
        
    Returns:
        Current datetime in user's timezone
    """
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz)
