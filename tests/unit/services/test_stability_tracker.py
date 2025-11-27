"""Unit tests for Stability Tracker.

This module tests the StabilityTracker service which implements signal debouncing
and stability requirements across consecutive scans using Redis.
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
import fakeredis.aioredis

from app.services.stability_tracker import StabilityTracker


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def fake_redis():
    """Create a FakeRedis instance for testing."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()
    await redis.aclose()


@pytest.fixture
async def stability_tracker(fake_redis):
    """Create StabilityTracker instance with mocked Redis."""
    tracker = StabilityTracker()
    # Mock the _get_redis method to return our fake redis
    tracker._get_redis = AsyncMock(return_value=fake_redis)
    tracker.redis = fake_redis
    return tracker


@pytest.fixture
def sample_dates():
    """Sample expiry dates for testing."""
    return {
        "front": date(2025, 1, 17),
        "back": date(2025, 2, 14),
        "front_alt": date(2025, 1, 24),
        "back_alt": date(2025, 2, 21),
    }


# ============================================================================
# Tests for Redis Key Generation
# ============================================================================

@pytest.mark.unit
class TestStabilityTrackerKeyGeneration:
    """Test Redis key format and uniqueness."""
    
    def test_key_uses_expiry_dates_not_dte(self, stability_tracker, sample_dates):
        """✅ Redis key uses expiry dates (not DTE) to prevent daily resets."""
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        
        # Key should contain the actual dates
        assert "SPY" in key
        assert str(sample_dates["front"]) in key
        assert str(sample_dates["back"]) in key
        assert key == f"stability:SPY:{sample_dates['front']}:{sample_dates['back']}"
    
    def test_key_uniqueness_different_tickers(self, stability_tracker, sample_dates):
        """✅ Different tickers produce different keys."""
        key1 = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        key2 = stability_tracker._make_key("QQQ", sample_dates["front"], sample_dates["back"])
        
        assert key1 != key2
    
    def test_key_uniqueness_different_expiries(self, stability_tracker, sample_dates):
        """✅ Different expiries produce different keys."""
        key1 = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        key2 = stability_tracker._make_key("SPY", sample_dates["front_alt"], sample_dates["back_alt"])
        
        assert key1 != key2


# ============================================================================
# Tests for check_stability() - First Scan
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCheckStabilityFirstScan:
    """Test behavior on first scan of a signal."""
    
    @pytest.mark.asyncio
    async def test_first_scan_returns_false_with_reason(self, stability_tracker, sample_dates):
        """✅ First scan → should_alert=False, reason='first_scan'."""
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        assert should_alert is False
        assert state["consecutive_count"] == 1
        assert state["reason"] == "first_scan"
    
    @pytest.mark.asyncio
    async def test_first_scan_stores_initial_state(self, stability_tracker, sample_dates, fake_redis):
        """✅ Verify initial state is stored in Redis."""
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        state = await fake_redis.hgetall(key)
        
        assert state["last_ff"] == "0.35"
        assert state["consecutive_count"] == "1"
        assert state["last_alert_ts"] == ""
        assert "first_seen" in state
    
    @pytest.mark.asyncio
    async def test_first_scan_sets_ttl(self, stability_tracker, sample_dates, fake_redis):
        """✅ Verify TTL is set to 24 hours (86400 seconds)."""
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        ttl = await fake_redis.ttl(key)
        
        # TTL should be set to 24 hours (86400 seconds)
        # Allow some tolerance for execution time
        assert 86395 <= ttl <= 86400


# ============================================================================
# Tests for check_stability() - Consecutive Scans
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCheckStabilityConsecutiveScans:
    """Test consecutive scan tracking."""
    
    @pytest.mark.asyncio
    async def test_consecutive_scans_below_required(self, stability_tracker, sample_dates):
        """✅ Consecutive scans < required_scans → should_alert=False."""
        # First scan
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=3
        )
        
        # Second scan (still below required)
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=3
        )
        
        assert should_alert is False
        assert state["consecutive_count"] == 2
        assert "need_3_scans" in state["reason"]
    
    @pytest.mark.asyncio
    async def test_consecutive_scans_meets_required(self, stability_tracker, sample_dates):
        """✅ Consecutive scans >= required_scans → should_alert=True."""
        # First scan
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        # Second scan (meets required)
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2
        )
        
        assert should_alert is True
        assert state["consecutive_count"] == 2
        assert state["reason"] == "stable"
    
    @pytest.mark.asyncio
    async def test_consecutive_count_increments(self, stability_tracker, sample_dates):
        """✅ Verify consecutive count increments correctly."""
        for i in range(1, 5):
            should_alert, state = await stability_tracker.check_stability(
                ticker="SPY",
                front_expiry=sample_dates["front"],
                back_expiry=sample_dates["back"],
                ff_value=0.30 + (i * 0.01),
                required_scans=10  # High number to prevent alerting
            )
            assert state["consecutive_count"] == i
    
    @pytest.mark.asyncio
    async def test_different_required_scans_values(self, stability_tracker, sample_dates):
        """✅ Test with different required_scans values (2, 3, 4)."""
        for required in [2, 3, 4]:
            # Reset for each test
            await stability_tracker.reset("TEST", sample_dates["front"], sample_dates["back"])
            
            # Run scans up to required amount
            for i in range(required):
                should_alert, state = await stability_tracker.check_stability(
                    ticker="TEST",
                    front_expiry=sample_dates["front"],
                    back_expiry=sample_dates["back"],
                    ff_value=0.30 + (i * 0.01),
                    required_scans=required
                )
            
            # Last scan should alert
            assert should_alert is True
            assert state["consecutive_count"] == required


# ============================================================================
# Tests for check_stability() - Cooldown Period
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCheckStabilityCooldown:
    """Test cooldown period enforcement."""
    
    @pytest.mark.asyncio
    async def test_cooldown_period_active(self, stability_tracker, sample_dates, fake_redis):
        """✅ Cooldown period active → should_alert=False with reason."""
        # First scan
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        # Second scan - triggers alert
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2,
            cooldown_minutes=120
        )
        
        # Third scan - should be in cooldown
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.37,
            required_scans=2,
            cooldown_minutes=120
        )
        
        assert should_alert is False
        assert "cooldown" in state["reason"]
    
    @pytest.mark.asyncio
    async def test_cooldown_period_expired(self, stability_tracker, sample_dates, fake_redis):
        """✅ Cooldown period expired → check other conditions."""
        # First scan
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        # Second scan - triggers alert
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2,
            cooldown_minutes=1  # 1 minute cooldown
        )
        
        # Manually set last_alert_ts to 2 minutes ago
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        past_time = datetime.utcnow() - timedelta(minutes=2)
        await fake_redis.hset(key, "last_alert_ts", past_time.isoformat())
        
        # Third scan with sufficient FF increase - should alert
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.40,  # Significant increase
            required_scans=2,
            cooldown_minutes=1,
            delta_ff_min=0.02
        )
        
        assert should_alert is True
        assert state["reason"] == "stable"
    
    @pytest.mark.asyncio
    async def test_cooldown_time_calculation(self, stability_tracker, sample_dates, fake_redis):
        """✅ Verify cooldown time calculation."""
        # Setup: trigger alert
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2,
            cooldown_minutes=60
        )
        
        # Set last_alert_ts to 30 minutes ago
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        past_time = datetime.utcnow() - timedelta(minutes=30)
        await fake_redis.hset(key, "last_alert_ts", past_time.isoformat())
        
        # Check - should be in cooldown
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.40,
            required_scans=2,
            cooldown_minutes=60
        )
        
        assert should_alert is False
        # Reason should contain time remaining
        assert "cooldown_30" in state["reason"] or "cooldown_29" in state["reason"]


# ============================================================================
# Tests for check_stability() - FF Delta Threshold
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCheckStabilityFFDelta:
    """Test FF delta threshold checking."""
    
    @pytest.mark.asyncio
    async def test_ff_delta_below_threshold(self, stability_tracker, sample_dates, fake_redis):
        """✅ FF delta below threshold → should_alert=False."""
        # Setup: trigger initial alert
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2,
            cooldown_minutes=60
        )
        
        # Set last_alert_ts to past cooldown
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        past_time = datetime.utcnow() - timedelta(minutes=120)
        await fake_redis.hset(key, "last_alert_ts", past_time.isoformat())
        
        # Small FF increase (below threshold)
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.37,  # Only 0.01 increase
            required_scans=2,
            cooldown_minutes=60,
            delta_ff_min=0.02  # Requires 0.02 increase
        )
        
        assert should_alert is False
        assert "ff_delta_too_small" in state["reason"]
    
    @pytest.mark.asyncio
    async def test_ff_delta_above_threshold_after_cooldown(self, stability_tracker, sample_dates, fake_redis):
        """✅ FF delta above threshold after cooldown → should_alert=True."""
        # Setup: trigger initial alert
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2,
            cooldown_minutes=60
        )
        
        # Set last_alert_ts to past cooldown
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        past_time = datetime.utcnow() - timedelta(minutes=120)
        await fake_redis.hset(key, "last_alert_ts", past_time.isoformat())
        
        # Significant FF increase
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.40,  # 0.04 increase from last_ff
            required_scans=2,
            cooldown_minutes=60,
            delta_ff_min=0.02
        )
        
        assert should_alert is True
        assert state["reason"] == "stable"
    
    @pytest.mark.asyncio
    async def test_different_delta_ff_min_values(self, stability_tracker, sample_dates, fake_redis):
        """✅ Test with different delta_ff_min values."""
        for delta_min in [0.01, 0.02, 0.05]:
            # Reset
            await stability_tracker.reset("TEST", sample_dates["front"], sample_dates["back"])
            
            # Setup alert
            await stability_tracker.check_stability(
                ticker="TEST",
                front_expiry=sample_dates["front"],
                back_expiry=sample_dates["back"],
                ff_value=0.30,
                required_scans=2
            )
            
            await stability_tracker.check_stability(
                ticker="TEST",
                front_expiry=sample_dates["front"],
                back_expiry=sample_dates["back"],
                ff_value=0.31,
                required_scans=2,
                cooldown_minutes=1
            )
            
            # Set past cooldown
            key = stability_tracker._make_key("TEST", sample_dates["front"], sample_dates["back"])
            past_time = datetime.utcnow() - timedelta(minutes=5)
            await fake_redis.hset(key, "last_alert_ts", past_time.isoformat())
            
            # Test with FF increase just above threshold
            should_alert, state = await stability_tracker.check_stability(
                ticker="TEST",
                front_expiry=sample_dates["front"],
                back_expiry=sample_dates["back"],
                ff_value=0.31 + delta_min + 0.001,
                required_scans=2,
                cooldown_minutes=1,
                delta_ff_min=delta_min
            )
            
            assert should_alert is True
    
    @pytest.mark.asyncio
    async def test_ff_value_updated_in_state(self, stability_tracker, sample_dates, fake_redis):
        """✅ Verify FF value is updated in state."""
        ff_values = [0.35, 0.36, 0.37, 0.38]
        
        for ff_val in ff_values:
            await stability_tracker.check_stability(
                ticker="SPY",
                front_expiry=sample_dates["front"],
                back_expiry=sample_dates["back"],
                ff_value=ff_val,
                required_scans=10
            )
            
            # Check stored value
            key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
            state = await fake_redis.hgetall(key)
            assert float(state["last_ff"]) == ff_val


# ============================================================================
# Tests for check_stability() - State Persistence
# ============================================================================

@pytest.mark.unit
class TestCheckStabilityStatePersistence:
    """Test state persistence across multiple calls."""
    
    @pytest.mark.asyncio
    async def test_state_persists_across_calls(self, stability_tracker, sample_dates, fake_redis):
        """✅ State persists across multiple calls."""
        # First call
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        # Second call
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36
        )
        
        # Verify state
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        state = await fake_redis.hgetall(key)
        
        assert state["consecutive_count"] == "2"
        assert state["last_ff"] == "0.36"
        assert "first_seen" in state
    
    @pytest.mark.asyncio
    async def test_all_state_fields_stored(self, stability_tracker, sample_dates, fake_redis):
        """✅ Verify all state fields are stored correctly."""
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2
        )
        
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        state = await fake_redis.hgetall(key)
        
        # Check all required fields
        assert "last_ff" in state
        assert "consecutive_count" in state
        assert "last_alert_ts" in state
        assert "first_seen" in state
        
        # Verify values
        assert float(state["last_ff"]) == 0.36
        assert int(state["consecutive_count"]) == 2
        assert state["last_alert_ts"] != ""  # Should be set after alert
    
    @pytest.mark.asyncio
    async def test_state_updates_on_each_call(self, stability_tracker, sample_dates, fake_redis):
        """✅ Test state updates on each call."""
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        
        for i in range(1, 4):
            await stability_tracker.check_stability(
                ticker="SPY",
                front_expiry=sample_dates["front"],
                back_expiry=sample_dates["back"],
                ff_value=0.30 + (i * 0.01),
                required_scans=10
            )
            
            state = await fake_redis.hgetall(key)
            assert int(state["consecutive_count"]) == i
            assert float(state["last_ff"]) == 0.30 + (i * 0.01)


# ============================================================================
# Tests for check_stability() - TTL Expiration
# ============================================================================

@pytest.mark.unit
class TestCheckStabilityTTL:
    """Test TTL expiration behavior."""
    
    @pytest.mark.asyncio
    async def test_ttl_set_on_first_scan(self, stability_tracker, sample_dates, fake_redis):
        """✅ Verify 24-hour TTL is set on first scan."""
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        ttl = await fake_redis.ttl(key)
        
        # Should be approximately 86400 seconds (24 hours)
        assert 86395 <= ttl <= 86400
    
    @pytest.mark.asyncio
    async def test_expired_key_treated_as_first_scan(self, stability_tracker, sample_dates, fake_redis):
        """✅ Test behavior when TTL expires (treated as first scan)."""
        # First scan
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        # Manually delete the key to simulate expiration
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        await fake_redis.delete(key)
        
        # Next scan should behave like first scan
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36
        )
        
        assert should_alert is False
        assert state["consecutive_count"] == 1
        assert state["reason"] == "first_scan"


# ============================================================================
# Tests for check_stability() - Integration Scenarios
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCheckStabilityIntegration:
    """Test complete workflows and integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, stability_tracker, sample_dates, fake_redis):
        """✅ End-to-end: first scan → consecutive scans → alert → cooldown → re-alert."""
        # First scan
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2,
            cooldown_minutes=60,
            delta_ff_min=0.02
        )
        assert should_alert is False
        assert state["reason"] == "first_scan"
        
        # Second scan - should alert
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2,
            cooldown_minutes=60,
            delta_ff_min=0.02
        )
        assert should_alert is True
        assert state["reason"] == "stable"
        
        # Third scan - in cooldown
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.37,
            required_scans=2,
            cooldown_minutes=60,
            delta_ff_min=0.02
        )
        assert should_alert is False
        assert "cooldown" in state["reason"]
        
        # Simulate cooldown expiration
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        past_time = datetime.utcnow() - timedelta(minutes=120)
        await fake_redis.hset(key, "last_alert_ts", past_time.isoformat())
        
        # Fourth scan - significant FF increase, should re-alert
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.40,  # 0.04 increase from last_ff
            required_scans=2,
            cooldown_minutes=60,
            delta_ff_min=0.02
        )
        assert should_alert is True
        assert state["reason"] == "stable"
    
    @pytest.mark.asyncio
    async def test_multiple_ticker_expiry_pairs_independent(self, stability_tracker, sample_dates):
        """✅ Multiple ticker/expiry pairs tracked independently."""
        # Track SPY
        should_alert1, state1 = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        # Track QQQ with same expiries
        should_alert2, state2 = await stability_tracker.check_stability(
            ticker="QQQ",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.40,
            required_scans=2
        )
        
        # Track SPY with different expiries
        should_alert3, state3 = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front_alt"],
            back_expiry=sample_dates["back_alt"],
            ff_value=0.30,
            required_scans=2
        )
        
        # All should be first scan
        assert state1["consecutive_count"] == 1
        assert state2["consecutive_count"] == 1
        assert state3["consecutive_count"] == 1
        
        # Second scan for SPY only
        should_alert1b, state1b = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2
        )
        
        # SPY should alert, others should still be at count 1
        assert should_alert1b is True
        assert state1b["consecutive_count"] == 2
        
        # Verify others unchanged
        should_alert2b, state2b = await stability_tracker.check_stability(
            ticker="QQQ",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.41,
            required_scans=2
        )
        assert should_alert2b is True  # Second scan, should alert
        assert state2b["consecutive_count"] == 2


# ============================================================================
# Tests for reset()
# ============================================================================

@pytest.mark.unit
class TestReset:
    """Test reset functionality."""
    
    @pytest.mark.asyncio
    async def test_reset_clears_tracking(self, stability_tracker, sample_dates, fake_redis):
        """✅ Reset clears stability tracking for ticker/expiry pair."""
        # Setup some state
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36
        )
        
        # Verify state exists
        key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        state_before = await fake_redis.hgetall(key)
        assert len(state_before) > 0
        
        # Reset
        await stability_tracker.reset("SPY", sample_dates["front"], sample_dates["back"])
        
        # Verify state cleared
        state_after = await fake_redis.hgetall(key)
        assert len(state_after) == 0
    
    @pytest.mark.asyncio
    async def test_after_reset_behaves_like_first_scan(self, stability_tracker, sample_dates):
        """✅ After reset, next check behaves like first scan."""
        # Setup and alert
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35,
            required_scans=2
        )
        
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.36,
            required_scans=2
        )
        
        # Reset
        await stability_tracker.reset("SPY", sample_dates["front"], sample_dates["back"])
        
        # Next check should be first scan
        should_alert, state = await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.37,
            required_scans=2
        )
        
        assert should_alert is False
        assert state["consecutive_count"] == 1
        assert state["reason"] == "first_scan"
    
    @pytest.mark.asyncio
    async def test_reset_doesnt_affect_other_pairs(self, stability_tracker, sample_dates, fake_redis):
        """✅ Reset doesn't affect other ticker/expiry pairs."""
        # Setup state for two different pairs
        await stability_tracker.check_stability(
            ticker="SPY",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.35
        )
        
        await stability_tracker.check_stability(
            ticker="QQQ",
            front_expiry=sample_dates["front"],
            back_expiry=sample_dates["back"],
            ff_value=0.40
        )
        
        # Reset SPY only
        await stability_tracker.reset("SPY", sample_dates["front"], sample_dates["back"])
        
        # Verify SPY cleared
        spy_key = stability_tracker._make_key("SPY", sample_dates["front"], sample_dates["back"])
        spy_state = await fake_redis.hgetall(spy_key)
        assert len(spy_state) == 0
        
        # Verify QQQ still has state
        qqq_key = stability_tracker._make_key("QQQ", sample_dates["front"], sample_dates["back"])
        qqq_state = await fake_redis.hgetall(qqq_key)
        assert len(qqq_state) > 0
        assert qqq_state["last_ff"] == "0.4"
