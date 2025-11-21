"""Master ticker registry service."""
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import MasterTicker, Subscription
from datetime import datetime


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
        
        # Update or create master ticker records
        for ticker, count in ticker_counts.items():
            master_ticker = await TickerService.get_or_create_ticker(db, ticker)
            master_ticker.active_subscriber_count = count
            
            # Determine scan tier based on subscriber count
            # This is a simple heuristic - can be made more sophisticated
            if count >= 10:
                master_ticker.scan_tier = "high"
            elif count >= 3:
                master_ticker.scan_tier = "medium"
            else:
                master_ticker.scan_tier = "low"
        
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
        """Get or create master ticker record."""
        ticker = ticker.upper()
        
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
            master_ticker.last_scan_at = datetime.utcnow()
            await db.commit()
