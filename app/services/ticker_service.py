"""Master ticker registry service."""
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import MasterTicker, Subscription, UserSettings
from datetime import datetime, timezone
import re


# Ticker validation pattern: 1-5 uppercase letters
TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')


def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize a ticker symbol.
    
    Args:
        ticker: Ticker symbol to validate
        
    Returns:
        Normalized (uppercase) ticker symbol
        
    Raises:
        ValueError: If ticker format is invalid
    """
    if not ticker:
        raise ValueError("Ticker symbol cannot be empty")
    
    normalized = ticker.upper().strip()
    
    if not TICKER_PATTERN.match(normalized):
        raise ValueError(
            f"Invalid ticker format: '{ticker}'. "
            "Ticker must be 1-5 uppercase letters."
        )
    
    return normalized


class TickerService:
    """Service for master ticker registry management."""
    
    @staticmethod
    async def update_ticker_registry(db: AsyncSession):
        """
        Update master ticker registry based on active subscriptions.
        Recalculates subscriber counts and updates scan tiers.
        """
        # Get all active tickers with subscriber counts
        result = await db.execute(
            select(
                Subscription.ticker,
                func.count(Subscription.user_id).label("count")
            )
            .where(Subscription.active == True)
            .group_by(Subscription.ticker)
        )
        
        ticker_counts = {row[0]: row[1] for row in result.all()}
        
        # Get max priority per ticker
        # Join Subscription -> UserSettings to get scan_priority
        priority_result = await db.execute(
            select(
                Subscription.ticker,
                func.max(UserSettings.scan_priority).label("max_priority")
            )
            .join(UserSettings, Subscription.user_id == UserSettings.user_id)
            .where(Subscription.active == True)
            .group_by(Subscription.ticker)
        )
        
        ticker_priorities = {row[0]: row[1] for row in priority_result.all()}
        
        # Update or create master ticker records
        for ticker, count in ticker_counts.items():
            master_ticker = await TickerService.get_or_create_ticker(db, ticker)
            master_ticker.active_subscriber_count = count
            
            # Determine scan tier
            # Base tier from count
            if count >= 10:
                tier = "high"
            elif count >= 3:
                tier = "medium"
            else:
                tier = "low"
            
            # Override with user priority
            max_prio = ticker_priorities.get(ticker, "standard")
            
            if max_prio == "turbo":
                tier = "high"
            elif max_prio == "high":
                # Upgrade to at least medium, or keep high if already high
                if tier == "low":
                    tier = "medium"
            
            master_ticker.scan_tier = tier
        
        # Set subscriber count to 0 for tickers no longer subscribed
        result = await db.execute(select(MasterTicker))
        all_tickers = result.scalars().all()
        
        for master_ticker in all_tickers:
            if master_ticker.ticker not in ticker_counts:
                master_ticker.active_subscriber_count = 0
                master_ticker.scan_tier = "low"
        
        await db.commit()
    
    @staticmethod
    async def get_or_create_ticker(
        db: AsyncSession,
        ticker: str
    ) -> MasterTicker:
        """Get or create master ticker record.
        
        Args:
            db: Database session
            ticker: Ticker symbol (will be validated and normalized)
            
        Returns:
            MasterTicker record
            
        Raises:
            ValueError: If ticker format is invalid
        """
        ticker = validate_ticker(ticker)
        
        result = await db.execute(
            select(MasterTicker).where(MasterTicker.ticker == ticker)
        )
        master_ticker = result.scalar_one_or_none()
        
        if master_ticker:
            return master_ticker
        
        master_ticker = MasterTicker(ticker=ticker)
        db.add(master_ticker)
        await db.flush()
        
        return master_ticker
    
    @staticmethod
    async def get_tickers_by_tier(
        db: AsyncSession,
        tier: str
    ) -> List[str]:
        """Get all tickers in a specific scan tier."""
        result = await db.execute(
            select(MasterTicker.ticker).where(
                MasterTicker.scan_tier == tier,
                MasterTicker.active_subscriber_count > 0
            )
        )
        return [row[0] for row in result.all()]
    
    @staticmethod
    async def update_last_scan(
        db: AsyncSession,
        ticker: str
    ):
        """Update last scan timestamp for a ticker."""
        ticker = ticker.upper()
        
        result = await db.execute(
            select(MasterTicker).where(MasterTicker.ticker == ticker)
        )
        master_ticker = result.scalar_one_or_none()
        
        if master_ticker:
            master_ticker.last_scan_at = datetime.now(timezone.utc)
            await db.commit()
