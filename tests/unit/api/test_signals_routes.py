"""Unit tests for Signals Routes.

This module tests the signals API endpoints including signal retrieval,
history, and decision recording.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status, HTTPException
from datetime import datetime, date

# Mock imports
from app.api.routes.signals import router
from app.models.user import User
from app.models.signal import Signal
from app.models.decision import SignalUserDecision
from app.models.subscription import Subscription


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = "user-123"
    return user


@pytest.fixture
def mock_signal():
    """Create a mock signal."""
    signal = MagicMock(spec=Signal)
    signal.id = "sig-123"
    signal.ticker = "SPY"
    signal.ff_value = 0.35
    signal.front_iv = 0.25
    signal.back_iv = 0.20
    signal.sigma_fwd = 0.15
    signal.front_expiry = date(2025, 1, 17)
    signal.back_expiry = date(2025, 2, 14)
    signal.front_dte = 16
    signal.back_dte = 44
    signal.as_of_ts = datetime(2025, 1, 1, 10, 0, 0)
    signal.quality_score = 1.0
    signal.vol_point = "ATM"
    return signal


@pytest.fixture
def mock_decision():
    """Create a mock decision."""
    decision = MagicMock(spec=SignalUserDecision)
    decision.id = "dec-123"
    decision.signal_id = "sig-123"
    decision.decision = "placed"
    decision.decision_ts = datetime(2025, 1, 1, 12, 0, 0)
    decision.pnl = 100.0
    decision.exit_price = 455.0
    return decision


# ============================================================================
# Tests for GET /api/signals
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetSignals:
    """Test get signals endpoint."""
    
    async def test_get_signals_success(self, mock_db, mock_user, mock_signal):
        """✅ Returns signals for user's watchlist."""
        # Mock subscribed tickers
        mock_sub_result = MagicMock()
        mock_sub_result.all.return_value = [("SPY",)]
        
        # Mock signals query
        mock_sig_result = MagicMock()
        mock_sig_result.scalars.return_value.all.return_value = [mock_signal]
        
        # Configure execute side effects
        mock_db.execute.side_effect = [mock_sub_result, mock_sig_result]
        
        from app.api.routes.signals import get_signals
        
        response = await get_signals(current_user=mock_user, db=mock_db)
        
        assert len(response) == 1
        assert response[0]["ticker"] == "SPY"
        assert response[0]["ff_value"] == 0.35
    
    async def test_empty_watchlist(self, mock_db, mock_user):
        """✅ Empty watchlist → empty array."""
        mock_sub_result = MagicMock()
        mock_sub_result.all.return_value = []
        mock_db.execute.return_value = mock_sub_result
        
        from app.api.routes.signals import get_signals
        
        response = await get_signals(current_user=mock_user, db=mock_db)
        
        assert response == []
        # Should verify only one execute call happened
        assert mock_db.execute.call_count == 1
    
    async def test_filter_by_ticker(self, mock_db, mock_user, mock_signal):
        """✅ Filter by ticker parameter."""
        mock_sub_result = MagicMock()
        mock_sub_result.all.return_value = [("SPY",)]
        mock_sig_result = MagicMock()
        mock_sig_result.scalars.return_value.all.return_value = [mock_signal]
        mock_db.execute.side_effect = [mock_sub_result, mock_sig_result]
        
        from app.api.routes.signals import get_signals
        
        await get_signals(ticker="SPY", current_user=mock_user, db=mock_db)
        
        # Verify execute called twice
        assert mock_db.execute.call_count == 2


# ============================================================================
# Tests for GET /api/signals/history
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetHistory:
    """Test get history endpoint."""
    
    async def test_get_history_success(self, mock_db, mock_user, mock_signal, mock_decision):
        """✅ Returns user's decision history with signals."""
        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_decision, mock_signal)]
        mock_db.execute.return_value = mock_result
        
        from app.api.routes.signals import get_history
        
        response = await get_history(current_user=mock_user, db=mock_db)
        
        assert len(response) == 1
        assert response[0]["signal"]["ticker"] == "SPY"
        assert response[0]["decision"]["decision"] == "placed"
        assert response[0]["decision"]["pnl"] == 100.0


# ============================================================================
# Tests for POST /api/signals/{signal_id}/decision
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRecordDecision:
    """Test record decision endpoint."""
    
    async def test_create_new_decision(self, mock_db, mock_user, mock_signal):
        """✅ Create new decision → 201."""
        # 1. Signal lookup -> found
        mock_sig_result = MagicMock()
        mock_sig_result.scalar_one_or_none.return_value = mock_signal
        
        # 2. Existing decision lookup -> None
        mock_dec_result = MagicMock()
        mock_dec_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [mock_sig_result, mock_dec_result]
        
        from app.api.routes.signals import record_decision, DecisionRequest
        
        request = DecisionRequest(decision="placed", notes="Test note")
        
        response = await record_decision("sig-123", request, mock_user, mock_db)
        
        assert response["decision"] == "placed"
        
        # Verify add/commit
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    async def test_update_existing_decision(self, mock_db, mock_user, mock_signal, mock_decision):
        """✅ Update existing decision."""
        # 1. Signal lookup -> found
        mock_sig_result = MagicMock()
        mock_sig_result.scalar_one_or_none.return_value = mock_signal
        
        # 2. Existing decision lookup -> found
        mock_dec_result = MagicMock()
        mock_dec_result.scalar_one_or_none.return_value = mock_decision
        
        mock_db.execute.side_effect = [mock_sig_result, mock_dec_result]
        
        from app.api.routes.signals import record_decision, DecisionRequest
        
        request = DecisionRequest(decision="ignored", notes="Changed mind")
        
        response = await record_decision("sig-123", request, mock_user, mock_db)
        
        assert response["decision"] == "ignored"
        assert mock_decision.decision == "ignored"
        assert mock_decision.notes == "Changed mind"
        
        # Verify commit (no add needed for update)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()
    
    async def test_invalid_decision_type(self, mock_db, mock_user):
        """✅ Invalid decision type → 400."""
        from app.api.routes.signals import record_decision, DecisionRequest
        
        request = DecisionRequest(decision="invalid")
        
        with pytest.raises(HTTPException) as exc:
            await record_decision("sig-123", request, mock_user, mock_db)
        
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_signal_not_found(self, mock_db, mock_user):
        """✅ Signal not found → 404."""
        mock_sig_result = MagicMock()
        mock_sig_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_sig_result
        
        from app.api.routes.signals import record_decision, DecisionRequest
        
        request = DecisionRequest(decision="placed")
        
        with pytest.raises(HTTPException) as exc:
            await record_decision("sig-999", request, mock_user, mock_db)
        
        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
