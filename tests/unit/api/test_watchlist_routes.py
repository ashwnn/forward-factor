"""Unit tests for Watchlist Routes.

This module tests the watchlist API endpoints including adding, removing,
and retrieving tickers.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status, HTTPException
from datetime import datetime

# Mock imports
from app.api.routes.watchlist import router
from app.models.user import User
from app.models.subscription import Subscription


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = "user-123"
    return user


@pytest.fixture
def mock_subscription_service():
    """Mock SubscriptionService."""
    with patch("app.api.routes.watchlist.SubscriptionService") as mock:
        yield mock


@pytest.fixture
def mock_subscription():
    """Create a mock subscription."""
    sub = MagicMock(spec=Subscription)
    sub.ticker = "SPY"
    sub.added_at = datetime(2025, 1, 1, 10, 0, 0)
    sub.active = True
    return sub


# ============================================================================
# Tests for GET /api/watchlist
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetWatchlist:
    """Test get watchlist endpoint."""
    
    async def test_get_watchlist_success(self, mock_db, mock_user, mock_subscription_service, mock_subscription):
        """✅ Returns user's subscriptions."""
        mock_subscription_service.get_user_subscriptions = AsyncMock(return_value=[mock_subscription])
        
        from app.api.routes.watchlist import get_watchlist
        
        response = await get_watchlist(current_user=mock_user, db=mock_db)
        
        assert len(response) == 1
        assert response[0]["ticker"] == "SPY"
        assert response[0]["active"] is True
    
    async def test_empty_watchlist(self, mock_db, mock_user, mock_subscription_service):
        """✅ Empty watchlist → []."""
        mock_subscription_service.get_user_subscriptions = AsyncMock(return_value=[])
        
        from app.api.routes.watchlist import get_watchlist
        
        response = await get_watchlist(current_user=mock_user, db=mock_db)
        
        assert response == []


# ============================================================================
# Tests for POST /api/watchlist
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAddTicker:
    """Test add ticker endpoint."""
    
    async def test_add_ticker_success(self, mock_db, mock_user, mock_subscription_service, mock_subscription):
        """✅ Add ticker (normalized to uppercase)."""
        mock_subscription_service.add_subscription = AsyncMock(return_value=mock_subscription)
        
        from app.api.routes.watchlist import add_ticker, AddTickerRequest
        
        request = AddTickerRequest(ticker="spy")
        
        response = await add_ticker(request, mock_user, mock_db)
        
        assert response["ticker"] == "SPY"
        assert "Successfully added" in response["message"]
        
        mock_subscription_service.add_subscription.assert_called_once_with(
            mock_db, str(mock_user.id), "SPY"
        )
    
    async def test_empty_ticker(self, mock_db, mock_user):
        """✅ Empty ticker → 400."""
        from app.api.routes.watchlist import add_ticker, AddTickerRequest
        
        request = AddTickerRequest(ticker="")
        
        with pytest.raises(HTTPException) as exc:
            await add_ticker(request, mock_user, mock_db)
        
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Tests for DELETE /api/watchlist/{ticker}
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRemoveTicker:
    """Test remove ticker endpoint."""
    
    async def test_remove_ticker_success(self, mock_db, mock_user, mock_subscription_service):
        """✅ Remove ticker (case-insensitive)."""
        mock_subscription_service.remove_subscription = AsyncMock()
        
        from app.api.routes.watchlist import remove_ticker
        
        response = await remove_ticker("spy", mock_user, mock_db)
        
        assert "Successfully removed" in response["message"]
        
        mock_subscription_service.remove_subscription.assert_called_once_with(
            mock_db, str(mock_user.id), "SPY"
        )
