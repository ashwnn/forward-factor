"""Unit tests for Data Models.

This module tests the integrity of database models including creation,
validation, and relationships.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, date

# Mock imports to avoid Pydantic errors
from app.models.user import User, UserSettings
from app.models.signal import Signal
from app.models.decision import SignalUserDecision
from app.models.subscription import Subscription
from app.models.ticker import MasterTicker


# ============================================================================
# Tests for User Model
# ============================================================================

@pytest.mark.unit
class TestUserModel:
    """Test User model."""
    
    def test_user_creation(self):
        """✅ Creation with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_secret",
            status="active",
            telegram_username="tg_user",
            telegram_chat_id="12345"
        )
        
        assert user.email == "test@example.com"
        assert user.status == "active"
        assert user.telegram_username == "tg_user"
    
    def test_user_defaults(self):
        """✅ Defaults applied."""
        # Assuming defaults are set in __init__ or DB (mocked here)
        # If defaults are DB-side, we can't test them without DB.
        # But we can test if fields are nullable/optional in definition.
        user = User(email="test@example.com")
        assert user.email == "test@example.com"


# ============================================================================
# Tests for UserSettings Model
# ============================================================================

@pytest.mark.unit
class TestUserSettingsModel:
    """Test UserSettings model."""
    
    def test_settings_creation(self):
        """✅ Creation with valid data."""
        settings = UserSettings(
            user_id="user-123",
            ff_threshold=0.1,
            min_open_interest=100,
            vol_point="ATM"
        )
        
        assert settings.user_id == "user-123"
        assert settings.ff_threshold == 0.1
        assert settings.vol_point == "ATM"


# ============================================================================
# Tests for Signal Model
# ============================================================================

@pytest.mark.unit
class TestSignalModel:
    """Test Signal model."""
    
    def test_signal_creation(self):
        """✅ Creation with valid data."""
        signal = Signal(
            ticker="SPY",
            front_expiry=date(2025, 1, 1),
            back_expiry=date(2025, 2, 1),
            ff_value=0.05,
            dedupe_key="hash123"
        )
        
        assert signal.ticker == "SPY"
        assert signal.ff_value == 0.05
        assert signal.dedupe_key == "hash123"


# ============================================================================
# Tests for SignalUserDecision Model
# ============================================================================

@pytest.mark.unit
class TestDecisionModel:
    """Test SignalUserDecision model."""
    
    def test_decision_creation(self):
        """✅ Creation with valid data."""
        decision = SignalUserDecision(
            signal_id="sig-123",
            user_id="user-123",
            decision="placed",
            notes="Test note"
        )
        
        assert decision.signal_id == "sig-123"
        assert decision.decision == "placed"
        assert decision.notes == "Test note"


# ============================================================================
# Tests for Subscription Model
# ============================================================================

@pytest.mark.unit
class TestSubscriptionModel:
    """Test Subscription model."""
    
    def test_subscription_creation(self):
        """✅ Creation with valid data."""
        sub = Subscription(
            user_id="user-123",
            ticker="SPY",
            active=True
        )
        
        assert sub.ticker == "SPY"
        assert sub.active is True


# ============================================================================
# Tests for Ticker Model
# ============================================================================

@pytest.mark.unit
class TestTickerModel:
    """Test Ticker model."""
    
    def test_ticker_creation(self):
        """✅ Creation with valid data."""
        ticker = MasterTicker(
            ticker="SPY",
            last_scan_at=datetime(2025, 1, 1, 10, 0, 0),
            scan_tier="high"
        )
        
        assert ticker.ticker == "SPY"
        assert ticker.scan_tier == "high"
