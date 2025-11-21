"""User service for CRUD operations."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, UserSettings
from app.core.config import settings as app_settings


class UserService:
    """Service for user management."""
    
    @staticmethod
    async def get_or_create_user(db: AsyncSession, telegram_chat_id: str) -> User:
        """
        Get existing user or create new one.
        
        Args:
            db: Database session
            telegram_chat_id: Telegram chat ID
            
        Returns:
            User object
        """
        # Try to get existing user
        result = await db.execute(
            select(User).where(User.telegram_chat_id == telegram_chat_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return user
        
        # Create new user with default settings
        user = User(telegram_chat_id=telegram_chat_id, status="active")
        db.add(user)
        await db.flush()
        
        # Create default settings
        user_settings = UserSettings(
            user_id=user.id,
            ff_threshold=app_settings.default_ff_threshold,
            min_open_interest=app_settings.default_min_open_interest,
            min_volume=app_settings.default_min_volume,
            max_bid_ask_pct=app_settings.default_max_bid_ask_pct,
            sigma_fwd_floor=app_settings.default_sigma_fwd_floor,
            stability_scans=app_settings.default_stability_scans,
            cooldown_minutes=app_settings.default_cooldown_minutes,
            timezone=app_settings.default_timezone
        )
        db.add(user_settings)
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def get_user_by_chat_id(db: AsyncSession, telegram_chat_id: str) -> Optional[User]:
        """Get user by Telegram chat ID."""
        result = await db.execute(
            select(User).where(User.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_settings(db: AsyncSession, user_id: str) -> Optional[UserSettings]:
        """Get user settings."""
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_user_settings(
        db: AsyncSession,
        user_id: str,
        **kwargs
    ) -> UserSettings:
        """Update user settings."""
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one()
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        await db.commit()
        await db.refresh(settings)
        
        return settings
