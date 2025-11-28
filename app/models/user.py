"""User model and settings."""
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
import uuid
import re
from zoneinfo import ZoneInfo
from app.core.database import Base


# Valid IANA timezones (common subset)
VALID_TIMEZONES = {
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Vancouver", "America/Toronto", "America/Phoenix", "America/Detroit",
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Singapore",
    "Australia/Sydney", "Australia/Melbourne", "Pacific/Auckland",
    "UTC"
}


class User(Base):
    """User model representing a Telegram user."""
    
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=True, index=True)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String, default="active", nullable=False)
    link_code = Column(String, unique=True, nullable=True, index=True)
    
    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("SignalUserDecision", back_populates="user", cascade="all, delete-orphan")
    telegram_chats = relationship("TelegramChat", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    """User-specific settings for signal detection."""
    
    __tablename__ = "user_settings"
    
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ff_threshold = Column(Float, default=0.20, nullable=False)
    dte_pairs = Column(JSON, default=lambda: [
        {"front": 30, "back": 60, "front_tol": 5, "back_tol": 10},
        {"front": 30, "back": 90, "front_tol": 5, "back_tol": 10},
        {"front": 60, "back": 90, "front_tol": 10, "back_tol": 10}
    ])
    vol_point = Column(String, default="ATM", nullable=False)
    min_open_interest = Column(Integer, default=100, nullable=False)
    min_volume = Column(Integer, default=10, nullable=False)
    max_bid_ask_pct = Column(Float, default=0.08, nullable=False)
    sigma_fwd_floor = Column(Float, default=0.05, nullable=False)
    stability_scans = Column(Integer, default=2, nullable=False)
    cooldown_minutes = Column(Integer, default=120, nullable=False)
    quiet_hours = Column(JSON, default=lambda: {"enabled": False, "start": "22:00", "end": "08:00"})
    preferred_structure = Column(String, default="ATM_calendar_call", nullable=False)
    timezone = Column(String, default="America/Vancouver", nullable=False)
    scan_priority = Column(String, default="standard", nullable=False)  # standard, high, turbo
    discovery_mode = Column(Boolean, default=False, nullable=False)  # Enable discovery mode for market-wide scanning
    
    # Relationship
    user = relationship("User", back_populates="settings")
    
    @validates('timezone')
    def validate_timezone(self, key, value):
        """Validate that timezone is a valid IANA timezone."""
        if value not in VALID_TIMEZONES:
            # Try to validate using zoneinfo as fallback
            try:
                ZoneInfo(value)
            except Exception:
                raise ValueError(f"Invalid timezone: {value}. Must be a valid IANA timezone.")
        return value
    
    @validates('ff_threshold')
    def validate_ff_threshold(self, key, value):
        """Validate FF threshold is within reasonable bounds."""
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"ff_threshold must be between 0.0 and 1.0, got {value}")
        return value
    
    @validates('min_open_interest', 'min_volume')
    def validate_positive_int(self, key, value):
        """Validate numeric fields are positive."""
        if value < 0:
            raise ValueError(f"{key} must be non-negative, got {value}")
        return value
    
    @validates('stability_scans')
    def validate_stability_scans(self, key, value):
        """Validate stability scans is a reasonable number."""
        if not 1 <= value <= 10:
            raise ValueError(f"stability_scans must be between 1 and 10, got {value}")
        return value
    
    @validates('cooldown_minutes')
    def validate_cooldown(self, key, value):
        """Validate cooldown is a reasonable duration."""
        if not 0 <= value <= 1440:  # Max 24 hours
            raise ValueError(f"cooldown_minutes must be between 0 and 1440, got {value}")
        return value
    
    @validates('scan_priority')
    def validate_scan_priority(self, key, value):
        """Validate scan priority is a valid value."""
        valid_priorities = {"standard", "high", "turbo"}
        if value not in valid_priorities:
            raise ValueError(f"scan_priority must be one of {valid_priorities}, got {value}")
        return value
