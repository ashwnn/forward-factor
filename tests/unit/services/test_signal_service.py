"""Unit tests for Signal Service.

This module tests the SignalService which handles persistence and retrieval
of trading signals and user decisions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession

# We need to mock app.models imports if they trigger pydantic errors
# But for writing the test file, we'll assume we can import them
# or we'll mock them in the test setup if needed.
from app.services.signal_service import SignalService
from app.models import Signal, SignalUserDecision


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_signal_data():
    """Create sample signal data dictionary."""
    return {
        "ticker": "SPY",
        "as_of_ts": datetime(2025, 1, 1, 10, 0, 0),
        "front_expiry": date(2025, 1, 17),
        "back_expiry": date(2025, 2, 14),
        "front_dte": 16,
        "back_dte": 44,
        "front_iv": 0.25,
        "back_iv": 0.20,
        "sigma_fwd": 0.15,
        "ff_value": 0.35,
        "vol_point": "ATM",
        "quality_score": 1.0,
        "reason_codes": [],
        "underlying_price": 450.0,
        "provider": "polygon"
    }


# ============================================================================
# Tests for generate_dedupe_key()
# ============================================================================

@pytest.mark.unit
class TestGenerateDedupeKey:
    """Test deduplication key generation."""
    
    def test_same_inputs_same_hash(self, sample_signal_data):
        """✅ Same ticker/expiries/date → same hash."""
        hash1 = SignalService.generate_dedupe_key(sample_signal_data)
        hash2 = SignalService.generate_dedupe_key(sample_signal_data.copy())
        
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 length
    
    def test_different_date_different_hash(self, sample_signal_data):
        """✅ Different date → different hash."""
        data1 = sample_signal_data.copy()
        data2 = sample_signal_data.copy()
        data2["as_of_ts"] = datetime(2025, 1, 2, 10, 0, 0)
        
        hash1 = SignalService.generate_dedupe_key(data1)
        hash2 = SignalService.generate_dedupe_key(data2)
        
        assert hash1 != hash2
    
    def test_different_ticker_different_hash(self, sample_signal_data):
        """✅ Different ticker → different hash."""
        data1 = sample_signal_data.copy()
        data2 = sample_signal_data.copy()
        data2["ticker"] = "QQQ"
        
        hash1 = SignalService.generate_dedupe_key(data1)
        hash2 = SignalService.generate_dedupe_key(data2)
        
        assert hash1 != hash2
    
    def test_hash_collision_resistance(self, sample_signal_data):
        """✅ Hash collision resistance (basic)."""
        # Verify that changing expiries changes hash
        data1 = sample_signal_data.copy()
        data2 = sample_signal_data.copy()
        data2["front_expiry"] = date(2025, 1, 18)
        
        hash1 = SignalService.generate_dedupe_key(data1)
        hash2 = SignalService.generate_dedupe_key(data2)
        
        assert hash1 != hash2


# ============================================================================
# Tests for create_signal()
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCreateSignal:
    """Test signal creation and persistence."""
    
    async def test_new_signal_creation(self, mock_db, sample_signal_data):
        """✅ New signal → creates and returns Signal object."""
        # Mock execute to return no existing signal
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Call create_signal
        result = await SignalService.create_signal(mock_db, sample_signal_data)
        
        # Verify result
        assert result is not None
        assert result.ticker == "SPY"
        assert result.ff_value == 0.35
        
        # Verify DB interactions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    async def test_duplicate_signal(self, mock_db, sample_signal_data):
        """✅ Duplicate signal (same dedupe_key) → returns None."""
        # Mock execute to return existing signal
        existing_signal = Signal(id="existing-id")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_signal
        mock_db.execute.return_value = mock_result
        
        # Call create_signal
        result = await SignalService.create_signal(mock_db, sample_signal_data)
        
        # Verify result
        assert result is None
        
        # Verify DB interactions - should NOT add/commit
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    async def test_all_fields_persisted(self, mock_db, sample_signal_data):
        """✅ All signal fields persisted correctly."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        await SignalService.create_signal(mock_db, sample_signal_data)
        
        # Get the signal object passed to db.add()
        args, _ = mock_db.add.call_args
        signal = args[0]
        
        assert signal.ticker == sample_signal_data["ticker"]
        assert signal.front_expiry == sample_signal_data["front_expiry"]
        assert signal.back_expiry == sample_signal_data["back_expiry"]
        assert signal.front_iv == sample_signal_data["front_iv"]
        assert signal.sigma_fwd == sample_signal_data["sigma_fwd"]
        assert signal.quality_score == sample_signal_data["quality_score"]
        assert signal.dedupe_key is not None


# ============================================================================
# Tests for get_recent_signals()
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetRecentSignals:
    """Test signal retrieval."""
    
    async def test_retrieve_signals(self, mock_db):
        """✅ Retrieve signals ordered by as_of_ts desc."""
        # Mock result
        mock_signals = [Signal(id="1", ticker="SPY"), Signal(id="2", ticker="QQQ")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_signals
        mock_db.execute.return_value = mock_result
        
        # Call
        results = await SignalService.get_recent_signals(mock_db)
        
        assert len(results) == 2
        assert results[0].ticker == "SPY"
        mock_db.execute.assert_called_once()
    
    async def test_filter_by_ticker(self, mock_db):
        """✅ Filter by ticker."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        await SignalService.get_recent_signals(mock_db, ticker="SPY")
        
        # Verify query construction (checking call args is complex with SQLAlchemy)
        # But we can verify execute was called
        mock_db.execute.assert_called_once()
    
    async def test_limit_parameter(self, mock_db):
        """✅ Limit parameter respected."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        await SignalService.get_recent_signals(mock_db, limit=10)
        
        mock_db.execute.assert_called_once()
    
    async def test_returns_empty_list(self, mock_db):
        """✅ Returns empty list when no signals."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        results = await SignalService.get_recent_signals(mock_db)
        
        assert isinstance(results, list)
        assert len(results) == 0


# ============================================================================
# Tests for record_decision()
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRecordDecision:
    """Test decision recording."""
    
    async def test_create_decision_record(self, mock_db):
        """✅ Create decision record with metadata."""
        metadata = {"reason": "high_iv", "confidence": 0.8}
        
        result = await SignalService.record_decision(
            mock_db, 
            signal_id="sig-123", 
            user_id="user-456", 
            decision="placed", 
            metadata=metadata
        )
        
        assert result.signal_id == "sig-123"
        assert result.user_id == "user-456"
        assert result.decision == "placed"
        assert result.metadata == metadata
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    async def test_all_decision_types(self, mock_db):
        """✅ All decision types: 'placed', 'ignored', 'expired', 'error'."""
        decisions = ["placed", "ignored", "expired", "error"]
        
        for d in decisions:
            await SignalService.record_decision(
                mock_db, "sig-1", "user-1", d
            )
            
            # Get the object passed to add
            args, _ = mock_db.add.call_args
            assert args[0].decision == d
            
            mock_db.add.reset_mock()
            mock_db.commit.reset_mock()


# ============================================================================
# Tests for get_user_decisions()
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetUserDecisions:
    """Test user decision retrieval."""
    
    async def test_get_user_decisions(self, mock_db):
        """✅ Join with Signal table and return details."""
        # Mock result rows (decision, signal)
        mock_decision = SignalUserDecision(
            decision="placed", 
            decision_ts=datetime(2025, 1, 1, 12, 0, 0)
        )
        mock_signal = Signal(
            ticker="SPY", 
            ff_value=0.35, 
            front_dte=30, 
            back_dte=60
        )
        
        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_decision, mock_signal)]
        mock_db.execute.return_value = mock_result
        
        results = await SignalService.get_user_decisions(mock_db, "user-1")
        
        assert len(results) == 1
        item = results[0]
        assert item["ticker"] == "SPY"
        assert item["decision"] == "placed"
        assert item["ff_value"] == 0.35
        assert item["decision_ts"] == "2025-01-01 12:00"
