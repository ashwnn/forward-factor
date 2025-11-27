"""Unit tests for SubscriptionService.

This module tests subscription management logic including adding, removing,
and retrieving subscriptions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

# Mock imports
from app.services.subscription_service import SubscriptionService
from app.models.subscription import Subscription


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_subscription():
    """Create a mock subscription."""
    sub = MagicMock(spec=Subscription)
    sub.ticker = "SPY"
    sub.user_id = "user-123"
    sub.active = True
    return sub


# ============================================================================
# Tests for add_subscription
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAddSubscription:
    """Test add subscription."""
    
    async def test_add_new(self, mock_db):
        """✅ New subscription created."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        sub = await SubscriptionService.add_subscription(mock_db, "user-1", "spy")
        
        assert sub.ticker == "SPY"
        assert sub.active is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    async def test_reactivate_existing(self, mock_db, mock_subscription):
        """✅ Existing inactive → reactivate."""
        mock_subscription.active = False
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        mock_db.execute.return_value = mock_result
        
        sub = await SubscriptionService.add_subscription(mock_db, "user-1", "SPY")
        
        assert sub.active is True
        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()


# ============================================================================
# Tests for remove_subscription
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRemoveSubscription:
    """Test remove subscription."""
    
    async def test_remove_success(self, mock_db):
        """✅ Returns true if deleted."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        
        result = await SubscriptionService.remove_subscription(mock_db, "user-1", "spy")
        
        assert result is True
        mock_db.commit.assert_called_once()
    
    async def test_remove_not_found(self, mock_db):
        """✅ Not found → returns false."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result
        
        result = await SubscriptionService.remove_subscription(mock_db, "user-1", "spy")
        
        assert result is False


# ============================================================================
# Tests for get_user_subscriptions
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetUserSubscriptions:
    """Test get user subscriptions."""
    
    async def test_get_active_only(self, mock_db, mock_subscription):
        """✅ Returns Subscription objects."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_subscription]
        mock_db.execute.return_value = mock_result
        
        subs = await SubscriptionService.get_user_subscriptions(mock_db, "user-1", active_only=True)
        
        assert len(subs) == 1
        assert subs[0].ticker == "SPY"
