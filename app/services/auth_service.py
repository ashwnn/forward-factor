"""Authentication service for user registration and login."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User, UserSettings
from app.core.auth import hash_password, verify_password


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    async def register_user(email: str, password: str, db: AsyncSession) -> User:
        """
        Register a new user with email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            db: Database session
            
        Returns:
            Created User object
            
        Raises:
            HTTPException: If email already exists
        """
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user = User(
            email=email,
            password_hash=hash_password(password),
            status="active"
        )
        
        db.add(user)
        await db.flush()
        
        # Create default settings for user
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def authenticate_user(email: str, password: str, db: AsyncSession) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            db: Database session
            
        Returns:
            User object if authentication successful, None otherwise
        """
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not user.password_hash:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    async def link_telegram_username(user_id: str, telegram_username: str, db: AsyncSession) -> User:
        """
        Link a Telegram username to a user account.
        
        Args:
            user_id: User's UUID
            telegram_username: Telegram username to link
            db: Database session
            
        Returns:
            Updated User object
            
        Raises:
            HTTPException: If user not found
        """
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove @ prefix if present
        if telegram_username.startswith("@"):
            telegram_username = telegram_username[1:]
        
        user.telegram_username = telegram_username
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
        """
        Get a user by email address.
        
        Args:
            email: User's email address
            db: Database session
            
        Returns:
            User object if found, None otherwise
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_telegram_chat_id(telegram_chat_id: str, db: AsyncSession) -> Optional[User]:
        """
        Get a user by Telegram chat ID.
        
        Args:
            telegram_chat_id: Telegram chat ID
            db: Database session
            
        Returns:
            User object if found, None otherwise
        """
        result = await db.execute(select(User).where(User.telegram_chat_id == telegram_chat_id))
        return result.scalar_one_or_none()
