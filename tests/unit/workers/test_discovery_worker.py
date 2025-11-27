"""Unit tests for DiscoveryWorker.

This module tests the discovery worker logic including:
- Fetching top liquid tickers from Polygon
- Populating the discovery queue
- Universe refresh scheduling
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.workers.discovery_worker import DiscoveryWorker
from app.providers import ProviderError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_provider():
    """Mock PolygonProvider."""
    with patch("app.workers.discovery_worker.PolygonProvider") as mock:
        provider_instance = AsyncMock()
        mock.return_value = provider_instance
        yield provider_instance


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    with patch("app.workers.discovery_worker.get_redis", new=AsyncMock(return_value=redis)):
        yield redis


# ============================================================================
# Tests for refresh_universe
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRefreshUniverse:
    """Test refresh_universe method."""
    
    async def test_refresh_success(self, mock_provider, mock_redis):
        """✅ Successfully fetch and queue top liquid tickers."""
        # Setup mock response
        mock_provider.get_top_liquid_tickers.return_value = ["AAPL", "MSFT", "GOOGL", "NVDA"]
        
        worker = DiscoveryWorker(ticker_limit=100)
        tickers = await worker.refresh_universe()
        
        # Verify provider call
        mock_provider.get_top_liquid_tickers.assert_called_once_with(limit=100)
        
        # Verify queue cleared
        mock_redis.delete.assert_called_once_with("discovery_queue")
        
        # Verify tickers pushed to queue
        assert mock_redis.lpush.call_count == 4
        mock_redis.lpush.assert_any_call("discovery_queue", "AAPL")
        mock_redis.lpush.assert_any_call("discovery_queue", "MSFT")
        mock_redis.lpush.assert_any_call("discovery_queue", "GOOGL")
        mock_redis.lpush.assert_any_call("discovery_queue", "NVDA")
        
        # Verify return value
        assert tickers == ["AAPL", "MSFT", "GOOGL", "NVDA"]
    
    async def test_refresh_empty_response(self, mock_provider, mock_redis):
        """✅ Handle empty ticker list."""
        mock_provider.get_top_liquid_tickers.return_value = []
        
        worker = DiscoveryWorker()
        tickers = await worker.refresh_universe()
        
        assert tickers == []
        mock_redis.lpush.assert_not_called()
    
    async def test_refresh_provider_error(self, mock_provider, mock_redis):
        """✅ Handle provider errors gracefully."""
        mock_provider.get_top_liquid_tickers.side_effect = ProviderError("API error")
        
        worker = DiscoveryWorker()
        
        with pytest.raises(ProviderError):
            await worker.refresh_universe()
    
    async def test_custom_limit(self, mock_provider, mock_redis):
        """✅ Custom ticker limit is passed to provider."""
        mock_provider.get_top_liquid_tickers.return_value = ["SPY"]
        
        worker = DiscoveryWorker(ticker_limit=50)
        await worker.refresh_universe()
        
        mock_provider.get_top_liquid_tickers.assert_called_once_with(limit=50)


# ============================================================================
# Tests for run_once
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRunOnce:
    """Test run_once method."""
    
    async def test_run_once_success(self, mock_provider, mock_redis):
        """✅ Run once and cleanup."""
        mock_provider.get_top_liquid_tickers.return_value = ["AAPL"]
        
        worker = DiscoveryWorker()
        result = await worker.run_once()
        
        assert result == ["AAPL"]
        mock_provider.close.assert_called_once()
    
    async def test_run_once_cleanup_on_error(self, mock_provider, mock_redis):
        """✅ Cleanup even on error."""
        mock_provider.get_top_liquid_tickers.side_effect = Exception("Unexpected error")
        
        worker = DiscoveryWorker()
        
        with pytest.raises(Exception):
            await worker.run_once()
        
        # Cleanup should still be called
        mock_provider.close.assert_called_once()
