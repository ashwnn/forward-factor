"""Subscription service for managing user watchlists."""
from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Subscription, User


class SubscriptionService:
    """Service for subscription management."""
    
    @staticmethod
    async def add_subscription(
        db: AsyncSession,
        user_id: str,
        ticker: str
    ) -> Subscription:
        """
        Add a ticker to user's watchlist.
        
        Args:
            db: Database session
            user_id: User ID
            ticker: Ticker symbol (will be uppercased)
            
        Returns:
            Subscription object
        """
        ticker = ticker.upper()
        
        # Check if already exists
        result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.ticker == ticker
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            if not existing.active:
                existing.active = True
                await db.commit()
                await db.refresh(existing)
            return existing
        
        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            ticker=ticker,
            active=True
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        
        return subscription
    
    @staticmethod
    async def remove_subscription(
        db: AsyncSession,
        user_id: str,
        ticker: str
    ) -> bool:
        """
        Remove a ticker from user's watchlist.
        
        Args:
            db: Database session
            user_id: User ID
            ticker: Ticker symbol
            
        Returns:
            True if removed, False if not found
        """
        ticker = ticker.upper()
        
        result = await db.execute(
            delete(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.ticker == ticker
            )
        )
        await db.commit()
        
        return result.rowcount > 0
    
    @staticmethod
    async def get_user_subscriptions(
        db: AsyncSession,
        user_id: str,
        active_only: bool = True
    ) -> List[Subscription]:
        """
        Get list of subscriptions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            active_only: Only return active subscriptions
            
        Returns:
            List of Subscription objects
        """
        query = select(Subscription).where(Subscription.user_id == user_id)
        
        if active_only:
            query = query.where(Subscription.active == True)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_ticker_subscribers(
        db: AsyncSession,
        ticker: str
    ) -> List[str]:
        """
        Get all user IDs subscribed to a ticker.
        
        Args:
            db: Database session
            ticker: Ticker symbol
            
        Returns:
            List of user IDs
        """
        ticker = ticker.upper()
        
        result = await db.execute(
            select(Subscription.user_id).where(
                Subscription.ticker == ticker,
                Subscription.active == True
            )
        )
        return [str(row[0]) for row in result.all()]
