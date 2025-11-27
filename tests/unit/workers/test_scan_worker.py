"""Unit tests for ScanWorker.

This module tests the scan worker logic including ticker scanning,
signal computation, stability checking, and queue processing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date

# Mock imports
from app.workers.scan_worker import ScanWorker


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_provider():
    """Mock PolygonProvider."""
    with patch("app.workers.scan_worker.PolygonProvider") as mock:
        provider_instance = AsyncMock()
        mock.return_value = provider_instance
        yield provider_instance


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    with patch("app.workers.scan_worker.get_redis", new=AsyncMock(return_value=redis)):
        yield redis


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    # Mock context manager
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    
    with patch("app.workers.scan_worker.AsyncSessionLocal", return_value=session):
        yield session


@pytest.fixture
def mock_services():
    """Mock all services used by ScanWorker."""
    with patch("app.workers.scan_worker.SubscriptionService") as sub_svc, \
         patch("app.workers.scan_worker.UserService") as user_svc, \
         patch("app.workers.scan_worker.SignalService") as sig_svc, \
         patch("app.workers.scan_worker.TickerService") as tick_svc, \
         patch("app.workers.scan_worker.stability_tracker") as stab_tracker, \
         patch("app.workers.scan_worker.compute_signals") as comp_sigs:
        
        # Configure async methods
        sub_svc.get_ticker_subscribers = AsyncMock()
        user_svc.get_discovery_users = AsyncMock()
        user_svc.get_user_settings = AsyncMock()
        sig_svc.create_signal = AsyncMock()
        tick_svc.update_last_scan = AsyncMock()
        stab_tracker.check_stability = AsyncMock()
        
        yield {
            "sub": sub_svc,
            "user": user_svc,
            "signal": sig_svc,
            "ticker": tick_svc,
            "stability": stab_tracker,
            "compute": comp_sigs
        }


# ============================================================================
# Tests for scan_ticker
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestScanTicker:
    """Test scan_ticker method."""
    
    async def test_scan_success(self, mock_provider, mock_redis, mock_db_session, mock_services):
        """✅ Full scan workflow success."""
        # Setup mocks
        mock_provider.get_chain_snapshot.return_value = "mock_chain"
        
        # Mock subscribers
        mock_services["sub"].get_ticker_subscribers.return_value = ["user-1"]
        
        # Mock user settings
        settings = MagicMock()
        settings.ff_threshold = 0.1
        settings.stability_scans = 2
        settings.cooldown_minutes = 60
        mock_services["user"].get_user_settings.return_value = settings
        
        # Mock compute signals
        signal_data = {
            "ticker": "SPY",
            "front_expiry": date(2025, 1, 1),
            "back_expiry": date(2025, 2, 1),
            "ff_value": 0.5
        }
        mock_services["compute"].return_value = [signal_data]
        
        # Mock stability (stable)
        mock_services["stability"].check_stability.return_value = (True, {})
        
        # Mock signal creation (new signal)
        signal_obj = MagicMock()
        signal_obj.id = "sig-123"
        mock_services["signal"].create_signal.return_value = signal_obj
        
        # Run scan
        worker = ScanWorker()
        await worker.scan_ticker("SPY")
        
        # Verify provider call
        mock_provider.get_chain_snapshot.assert_called_once_with("SPY")
        
        # Verify redis cache
        mock_redis.setex.assert_called_once()
        
        # Verify signal computation
        mock_services["compute"].assert_called_once()
        
        # Verify stability check
        mock_services["stability"].check_stability.assert_called_once()
        
        # Verify signal creation
        mock_services["signal"].create_signal.assert_called_once()
        
        # Verify notification queue
        mock_redis.lpush.assert_called_once_with("notification_queue", "sig-123")
        
        # Verify last scan update
        mock_services["ticker"].update_last_scan.assert_called_once_with(mock_db_session, "SPY")
    
    async def test_no_subscribers(self, mock_provider, mock_redis, mock_db_session, mock_services):
        """✅ No subscribers → skip."""
        mock_services["sub"].get_ticker_subscribers.return_value = []
        mock_services["user"].get_discovery_users.return_value = []
        
        worker = ScanWorker()
        await worker.scan_ticker("SPY")
        
        # Should fetch chain but stop after checking subscribers
        mock_provider.get_chain_snapshot.assert_called_once()
        mock_services["compute"].assert_not_called()
    
    async def test_discovery_mode_with_users(self, mock_provider, mock_redis, mock_db_session, mock_services):
        """✅ Discovery mode processes even without subscribers."""
        # No regular subscribers
        mock_services["sub"].get_ticker_subscribers.return_value = []
        # But there are discovery users
        mock_services["user"].get_discovery_users.return_value = ["discovery-user-1"]
        
        # Mock user settings
        settings = MagicMock()
        settings.ff_threshold = 0.1
        settings.stability_scans = 2
        settings.cooldown_minutes = 60
        mock_services["user"].get_user_settings.return_value = settings
        
        # Mock compute signals
        signal_data = {
            "ticker": "SPY",
            "front_expiry": date(2025, 1, 1),
            "back_expiry": date(2025, 2, 1),
            "ff_value": 0.5
        }
        mock_services["compute"].return_value = [signal_data]
        
        # Mock stability (stable)
        mock_services["stability"].check_stability.return_value = (True, {})
        
        # Mock signal creation
        signal_obj = MagicMock()
        signal_obj.id = "sig-discovery-123"
        mock_services["signal"].create_signal.return_value = signal_obj
        
        worker = ScanWorker()
        await worker.scan_ticker("SPY", is_discovery=True)
        
        # Should process and create signal
        mock_services["compute"].assert_called_once()
        mock_services["signal"].create_signal.assert_called_once()
        
        # Verify is_discovery is set in signal_data
        created_signal_data = mock_services["signal"].create_signal.call_args[0][1]
        assert created_signal_data.get("is_discovery") == True
    
    async def test_discovery_dedupes_subscribers(self, mock_provider, mock_redis, mock_db_session, mock_services):
        """✅ Discovery mode deduplicates users who are both subscribers and discovery users."""
        # User is both a subscriber and has discovery mode enabled
        mock_services["sub"].get_ticker_subscribers.return_value = ["user-1"]
        mock_services["user"].get_discovery_users.return_value = ["user-1"]
        
        # Mock user settings
        settings = MagicMock()
        settings.ff_threshold = 0.1
        settings.stability_scans = 2
        settings.cooldown_minutes = 60
        mock_services["user"].get_user_settings.return_value = settings
        
        mock_services["compute"].return_value = [{"ticker": "SPY", "front_expiry": date(2025,1,1), "back_expiry": date(2025,2,1), "ff_value": 0.5}]
        mock_services["stability"].check_stability.return_value = (True, {})
        mock_services["signal"].create_signal.return_value = MagicMock(id="sig-1")
        
        worker = ScanWorker()
        await worker.scan_ticker("SPY", is_discovery=True)
        
        # Should only process once (deduped)
        assert mock_services["user"].get_user_settings.call_count == 1
        
        # For a subscriber receiving discovery signal, is_discovery should be False
        created_signal_data = mock_services["signal"].create_signal.call_args[0][1]
        assert created_signal_data.get("is_discovery") == False

    async def test_unstable_signal(self, mock_provider, mock_redis, mock_db_session, mock_services):
        """✅ Unstable signal → log and skip."""
        mock_services["sub"].get_ticker_subscribers.return_value = ["user-1"]
        mock_services["user"].get_user_settings.return_value = MagicMock()
        mock_services["compute"].return_value = [{"ticker": "SPY", "front_expiry": date(2025,1,1), "back_expiry": date(2025,2,1), "ff_value": 0.5}]
        
        # Mock stability (unstable)
        mock_services["stability"].check_stability.return_value = (False, {"reason": "first_scan"})
        
        worker = ScanWorker()
        await worker.scan_ticker("SPY")
        
        mock_services["signal"].create_signal.assert_not_called()
        mock_redis.lpush.assert_not_called()
    
    async def test_duplicate_signal(self, mock_provider, mock_redis, mock_db_session, mock_services):
        """✅ Duplicate signal → skip notification."""
        mock_services["sub"].get_ticker_subscribers.return_value = ["user-1"]
        mock_services["user"].get_user_settings.return_value = MagicMock()
        mock_services["compute"].return_value = [{"ticker": "SPY", "front_expiry": date(2025,1,1), "back_expiry": date(2025,2,1), "ff_value": 0.5}]
        mock_services["stability"].check_stability.return_value = (True, {})
        
        # Mock signal creation (duplicate -> None)
        mock_services["signal"].create_signal.return_value = None
        
        worker = ScanWorker()
        await worker.scan_ticker("SPY")
        
        mock_services["signal"].create_signal.assert_called_once()
        mock_redis.lpush.assert_not_called()


# ============================================================================
# Tests for run
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestWorkerRun:
    """Test worker run loop."""
    
    async def test_process_queue(self, mock_redis, mock_provider):
        """✅ Poll Redis scan_queue and process."""
        # Mock redis pop to return one job then raise exception to break loop
        mock_redis.brpop.side_effect = [
            ("scan_queue", "SPY"),
            KeyboardInterrupt("Break loop")
        ]
        
        worker = ScanWorker()
        worker.scan_ticker = AsyncMock()
        
        try:
            await worker.run()
        except Exception:
            pass  # Expected exception to break loop
        
        worker.scan_ticker.assert_called_once_with("SPY")
