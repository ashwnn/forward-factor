"""User model and settings."""
from sqlalchemy import Column, String, DateTime, Float, Integer, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class User(Base):
    """User model representing a Telegram user."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_chat_id = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default="active", nullable=False)
    
    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("SignalUserDecision", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    """User-specific settings for signal detection."""
    
    __tablename__ = "user_settings"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
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
    
    # Relationship
    user = relationship("User", back_populates="settings")
