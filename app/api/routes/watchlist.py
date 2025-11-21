"""Watchlist management API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    """Request to add a ticker to watchlist."""
    ticker: str


class TickerResponse(BaseModel):
    """Ticker information response."""
    ticker: str
    added_at: str
    active: bool


@router.get("", response_model=List[TickerResponse])
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's watchlist.
    
    Requires authentication.
    """
    subscriptions = await SubscriptionService.get_user_subscriptions(str(current_user.id), db)
    
    return [
        {
            "ticker": sub.ticker,
            "added_at": sub.added_at.isoformat(),
            "active": sub.active
        }
        for sub in subscriptions
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_ticker(
    request: AddTickerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a ticker to the current user's watchlist.
    
    Requires authentication.
    """
    # Normalize ticker to uppercase
    ticker = request.ticker.upper().strip()
    
    if not ticker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticker cannot be empty"
        )
    
    # Add subscription
    subscription = await SubscriptionService.add_subscription(
        str(current_user.id),
        ticker,
        db
    )
    
    return {
        "ticker": subscription.ticker,
        "added_at": subscription.added_at.isoformat(),
        "active": subscription.active,
        "message": f"Successfully added {ticker} to watchlist"
    }


@router.delete("/{ticker}", status_code=status.HTTP_200_OK)
async def remove_ticker(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a ticker from the current user's watchlist.
    
    Requires authentication.
    """
    ticker = ticker.upper().strip()
    
    await SubscriptionService.remove_subscription(
        str(current_user.id),
        ticker,
        db
    )
    
    return {
        "message": f"Successfully removed {ticker} from watchlist"
    }
