"""User service for CRUD operations."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, UserSettings
from app.core.config import settings as app_settings


class UserService:
    """Service for user management."""
    
    @staticmethod
    async def get_or_create_user(
        db: AsyncSession, 
        telegram_chat_id: str, 
        first_name: str,
        last_name: Optional[str] = None,
        telegram_username: Optional[str] = None
    ) -> User:
        """
        Get existing user by Telegram chat ID or create new user with linked chat.
        
        Args:
            db: Database session
            telegram_chat_id: Telegram chat ID
            first_name: Telegram user's first name (required)
            last_name: Telegram user's last name (optional)
            telegram_username: Optional Telegram username (without @)
            
        Returns:
            User object
        """
        from app.models.telegram_chat import TelegramChat
        
        # Try to get existing user through TelegramChat
        result = await db.execute(
            select(User)
            .join(TelegramChat, User.id == TelegramChat.user_id)
            .where(TelegramChat.chat_id == telegram_chat_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # User exists - update the TelegramChat record if needed
            result = await db.execute(
                select(TelegramChat).where(TelegramChat.chat_id == telegram_chat_id)
            )
            telegram_chat = result.scalar_one_or_none()
            
            if telegram_chat:
                # Update chat info if changed
                updated = False
                if telegram_username and telegram_chat.username != telegram_username:
                    telegram_chat.username = telegram_username
                    updated = True
                if telegram_chat.first_name != first_name:
                    telegram_chat.first_name = first_name
                    updated = True
                if telegram_chat.last_name != last_name:
                    telegram_chat.last_name = last_name
                    updated = True
                    
                if updated:
                    await db.commit()
                    await db.refresh(user)
            return user
        
        # Create new user with default settings
        user = User(status="active")
        db.add(user)
        await db.flush()
        
        # Create TelegramChat link
        telegram_chat = TelegramChat(
            user_id=user.id,
            chat_id=telegram_chat_id,
            first_name=first_name,
            last_name=last_name,
            username=telegram_username
        )
        db.add(telegram_chat)
        
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
        from app.models.telegram_chat import TelegramChat
        
        result = await db.execute(
            select(User)
            .join(TelegramChat, User.id == TelegramChat.user_id)
            .where(TelegramChat.chat_id == telegram_chat_id)
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
    
    @staticmethod
    async def get_discovery_users(db: AsyncSession) -> List[str]:
        """
        Get list of user IDs who have discovery mode enabled.
        
        Args:
            db: Database session
            
        Returns:
            List of user IDs with discovery_mode=True
        """
        result = await db.execute(
            select(UserSettings.user_id).where(UserSettings.discovery_mode == True)
        )
        return [row[0] for row in result.fetchall()]
