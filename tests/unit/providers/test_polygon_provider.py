"""Unit tests for PolygonProvider.

This module tests the Polygon.io provider integration including API calls,
response parsing, and error handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
import httpx

# Mock imports
from app.providers.polygon import PolygonProvider
from app.providers import ProviderError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_client():
    """Mock httpx AsyncClient."""
    with patch("httpx.AsyncClient") as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def provider(mock_client):
    """Create PolygonProvider instance."""
    return PolygonProvider(api_key="test-key")


# ============================================================================
# Tests for get_chain_snapshot
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetChainSnapshot:
    """Test get_chain_snapshot method."""
    
    async def test_success(self, provider, mock_client):
        """✅ Success → ChainSnapshot with expiries."""
        # Mock underlying price response
        price_resp = MagicMock()
        price_resp.status_code = 200
        price_resp.json.return_value = {"results": [{"c": 450.0}]}
        
        # Mock snapshot response
        snapshot_resp = MagicMock()
        snapshot_resp.status_code = 200
        snapshot_resp.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "details": {
                        "ticker": "O:SPY250117C00450000",
                        "strike_price": 450.0,
                        "expiration_date": "2025-01-17",
                        "contract_type": "call"
                    },
                    "greeks": {"implied_volatility": 0.2, "delta": 0.5},
                    "last_quote": {"bid": 10.0, "ask": 10.2},
                    "day": {"volume": 100},
                    "open_interest": 500
                }
            ]
        }
        
        mock_client.get.side_effect = [price_resp, snapshot_resp]
        
        snapshot = await provider.get_chain_snapshot("SPY")
        
        assert snapshot.ticker == "SPY"
        assert snapshot.underlying_price == 450.0
        assert len(snapshot.expiries) == 1
        assert snapshot.expiries[0].expiry_date == date(2025, 1, 17)
        assert len(snapshot.expiries[0].contracts) == 1
    
    async def test_api_error_status(self, provider, mock_client):
        """✅ API error (non-OK status) → ProviderError."""
        price_resp = MagicMock()
        price_resp.json.return_value = {"results": [{"c": 450.0}]}
        
        snapshot_resp = MagicMock()
        snapshot_resp.json.return_value = {"status": "ERROR", "error": "Something went wrong"}
        
        mock_client.get.side_effect = [price_resp, snapshot_resp]
        
        with pytest.raises(ProviderError) as exc:
            await provider.get_chain_snapshot("SPY")
        
        assert "Polygon API returned status: ERROR" in str(exc.value)
    
    async def test_http_error(self, provider, mock_client):
        """✅ HTTP error → ProviderError."""
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")
        
        with pytest.raises(ProviderError) as exc:
            await provider.get_chain_snapshot("SPY")
        
        assert "Polygon API connection error" in str(exc.value)
    
    async def test_403_error(self, provider, mock_client):
        """✅ 403 error (plan limit) → ProviderError with specific message."""
        error_resp = MagicMock()
        error_resp.status_code = 403
        mock_client.get.side_effect = httpx.HTTPStatusError("403 Forbidden", request=None, response=error_resp)
        
        with pytest.raises(ProviderError) as exc:
            await provider.get_chain_snapshot("SPY")
        
        assert "Access Denied" in str(exc.value)


# ============================================================================
# Tests for parsing logic
# ============================================================================

@pytest.mark.unit
class TestParsing:
    """Test parsing logic."""
    
    def test_parse_contracts(self, provider):
        """✅ Parse Polygon JSON into Contract objects."""
        results = [
            {
                "details": {
                    "ticker": "O:SPY250117C00450000",
                    "strike_price": 450.0,
                    "expiration_date": "2025-01-17",
                    "contract_type": "call"
                },
                "greeks": {"implied_volatility": 0.2},
                "last_quote": {"bid": 10.0, "ask": 10.2},
                "day": {"volume": 100},
                "open_interest": 500
            }
        ]
        
        contracts = provider._parse_contracts(results)
        
        assert len(contracts) == 1
        c = contracts[0]
        assert c.symbol == "O:SPY250117C00450000"
        assert c.strike == 450.0
        assert c.expiry == date(2025, 1, 17)
        assert c.option_type == "call"
        assert c.implied_volatility == 0.2
        assert c.bid == 10.0
        assert c.ask == 10.2
    
    def test_group_by_expiry(self, provider):
        """✅ Group contracts by expiry_date."""
        # Create mock contracts
        c1 = MagicMock()
        c1.expiry = date(2025, 1, 17)
        c2 = MagicMock()
        c2.expiry = date(2025, 2, 21)
        c3 = MagicMock()
        c3.expiry = date(2025, 1, 17)
        
        contracts = [c1, c2, c3]
        
        expiries = provider._group_by_expiry(contracts)
        
        assert len(expiries) == 2
        # Should be sorted by date
        assert expiries[0].expiry_date == date(2025, 1, 17)
        assert len(expiries[0].contracts) == 2
        assert expiries[1].expiry_date == date(2025, 2, 21)
        assert len(expiries[1].contracts) == 1


# ============================================================================
# Tests for get_top_liquid_tickers
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetTopLiquidTickers:
    """Test get_top_liquid_tickers method."""
    
    async def test_success(self, provider, mock_client):
        """✅ Successfully fetch and sort top tickers by dollar volume."""
        # Mock response
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "status": "OK",
            "results": [
                {"T": "AAPL", "c": 150.0, "v": 10000000},  # $1.5B volume
                {"T": "MSFT", "c": 300.0, "v": 8000000},   # $2.4B volume
                {"T": "SPY", "c": 450.0, "v": 20000000},   # $9B volume
                {"T": "NVDA", "c": 500.0, "v": 5000000},   # $2.5B volume
            ]
        }
        resp.raise_for_status = MagicMock()
        mock_client.get.return_value = resp
        
        tickers = await provider.get_top_liquid_tickers(limit=3)
        
        # Should be sorted by dollar volume descending
        assert tickers == ["SPY", "NVDA", "MSFT"]
    
    async def test_filters_non_standard_tickers(self, provider, mock_client):
        """✅ Filter out tickers with special characters or >5 chars."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "status": "OK",
            "results": [
                {"T": "AAPL", "c": 150.0, "v": 10000000},
                {"T": "BRK.A", "c": 500000.0, "v": 1000},   # Has period
                {"T": "SPY123", "c": 450.0, "v": 20000000}, # Too long
                {"T": "MSFT", "c": 300.0, "v": 8000000},
            ]
        }
        resp.raise_for_status = MagicMock()
        mock_client.get.return_value = resp
        
        tickers = await provider.get_top_liquid_tickers(limit=10)
        
        assert "BRK.A" not in tickers
        assert "SPY123" not in tickers
        assert "AAPL" in tickers
        assert "MSFT" in tickers
    
    async def test_empty_results(self, provider, mock_client):
        """✅ Handle empty results."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "status": "OK",
            "results": []
        }
        resp.raise_for_status = MagicMock()
        mock_client.get.return_value = resp
        
        tickers = await provider.get_top_liquid_tickers()
        
        assert tickers == []
    
    async def test_api_error_status(self, provider, mock_client):
        """✅ API error (non-OK status) → ProviderError."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"status": "ERROR", "error": "Something went wrong"}
        resp.raise_for_status = MagicMock()
        mock_client.get.return_value = resp
        
        with pytest.raises(ProviderError) as exc:
            await provider.get_top_liquid_tickers()
        
        assert "Polygon API returned status: ERROR" in str(exc.value)
    
    async def test_403_error(self, provider, mock_client):
        """✅ 403 error → ProviderError with specific message."""
        error_resp = MagicMock()
        error_resp.status_code = 403
        mock_client.get.side_effect = httpx.HTTPStatusError("403 Forbidden", request=None, response=error_resp)
        
        with pytest.raises(ProviderError) as exc:
            await provider.get_top_liquid_tickers()
        
        assert "Access Denied" in str(exc.value)
