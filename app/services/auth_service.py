"""Authentication service for user registration and login."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import logging

import secrets
from app.models.user import User, UserSettings
from app.core.auth import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def generate_link_code() -> str:
        """Generate a unique link code."""
        return secrets.token_hex(4)
    
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
        logger.info(f"Attempting to register user: {email}")
        
        try:
            # Check if email already exists
            logger.debug(f"Checking if email exists: {email}")
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.warning(f"Registration failed: Email already exists: {email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create new user
            logger.debug(f"Creating new user: {email}")
            user = User(
                email=email,
                password_hash=hash_password(password),
                status="active",
                link_code=AuthService.generate_link_code()
            )
            
            db.add(user)
            await db.flush()
            logger.debug(f"User created with ID: {user.id}")
            
            # Create default settings for user
            logger.debug(f"Creating default settings for user: {user.id}")
            settings = UserSettings(user_id=user.id)
            db.add(settings)
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Successfully registered user: {email} (ID: {user.id})")
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering user {email}: {str(e)}", exc_info=True)
            await db.rollback()
            raise
    
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
        Finds existing bot user with matching username and merges accounts.
        
        Args:
            user_id: User's UUID (web user)
            telegram_username: Telegram username to link
            db: Database session
            
        Returns:
            Updated User object
            
        Raises:
            HTTPException: If user not found
        """
        # Get the web user
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
        
        # Look for existing bot user with this telegram_username
        result = await db.execute(
            select(User).where(
                User.telegram_username == telegram_username,
                User.id != user_id  # Not the same user
            )
        )
        bot_user = result.scalar_one_or_none()
        
        if bot_user and bot_user.telegram_chat_id:
            # Found a bot user - merge accounts
            logger.info(f"Merging bot user {bot_user.id} into web user {user.id}")
            
            # Copy telegram_chat_id from bot user to web user
            user.telegram_chat_id = bot_user.telegram_chat_id
            user.telegram_username = telegram_username
            
            # Migrate subscriptions from bot user to web user
            from app.models.subscription import Subscription
            result = await db.execute(
                select(Subscription).where(Subscription.user_id == bot_user.id)
            )
            bot_subscriptions = result.scalars().all()
            
            for bot_sub in bot_subscriptions:
                # Check if web user already has this ticker
                result = await db.execute(
                    select(Subscription).where(
                        Subscription.user_id == user.id,
                        Subscription.ticker == bot_sub.ticker
                    )
                )
                existing_sub = result.scalar_one_or_none()
                
                if existing_sub:
                    # Keep the earlier added_at date and ensure it's active
                    if bot_sub.added_at < existing_sub.added_at:
                        existing_sub.added_at = bot_sub.added_at
                    existing_sub.active = True
                else:
                    # Transfer subscription to web user
                    bot_sub.user_id = user.id
            
            # Mark bot user as inactive/merged
            bot_user.status = "merged"
            
            logger.info(f"Successfully merged {len(bot_subscriptions)} subscriptions")
        else:
            # No bot user found, just set the username
            user.telegram_username = telegram_username
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def verify_link_code(link_code: str, telegram_chat_id: str, telegram_username: str, db: AsyncSession) -> Optional[User]:
        """
        Verify link code and link Telegram account.
        
        Args:
            link_code: The link code provided by the user
            telegram_chat_id: The Telegram chat ID to link
            telegram_username: The Telegram username (optional)
            db: Database session
            
        Returns:
            User object if successful, None otherwise
        """
        # Find user by link code
        result = await db.execute(select(User).where(User.link_code == link_code))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
            
        # Link the account
        user.telegram_chat_id = telegram_chat_id
        if telegram_username:
            user.telegram_username = telegram_username
            
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def ensure_link_code(user: User, db: AsyncSession) -> str:
        """
        Ensure user has a link code. Generates one if missing.
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            The link code
        """
        if user.link_code:
            return user.link_code
            
        user.link_code = AuthService.generate_link_code()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user.link_code

    @staticmethod
    async def unlink_telegram_username(user_id: str, db: AsyncSession) -> User:
        """
        Unlink Telegram account from a user.
        
        Args:
            user_id: User's UUID
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
        
        # Clear Telegram information
        user.telegram_username = None
        user.telegram_chat_id = None
        
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
