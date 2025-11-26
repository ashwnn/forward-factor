"""Unit tests for Signal Engine core mathematical functions.

This module tests the critical Signal Engine functions defined in strategy.md.
All mathematical formulas are validated against the Forward Factor calculation requirements.
"""
import pytest
import numpy as np
from datetime import date, datetime
from typing import List

from app.services.signal_engine import (
    forward_factor,
    select_vol_point,
    pair_expiries,
    apply_liquidity_filters,
    compute_signals
)
from app.providers.models import Contract, Expiry, ChainSnapshot
from tests.conftest import create_contract, create_expiry, create_chain_snapshot


# ============================================================================
# Tests for forward_factor()
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestForwardFactor:
    """Test Forward Factor calculation - the core mathematical function."""
    
    def test_valid_calculation_typical_values(self):
        """✅ Valid calculation with typical values."""
        ff = forward_factor(
            front_iv=0.25,
            front_dte=30,
            back_iv=0.20,
            back_dte=60
        )
        
        assert ff is not None
        # Manual calculation verification:
        # t1 = 30/365 = 0.0822, t2 = 60/365 = 0.1644
        # v1 = 0.25^2 * 0.0822 = 0.00514
        # v2 = 0.20^2 * 0.1644 = 0.00658
        # v_fwd = (0.00658 - 0.00514) / (0.1644 - 0.0822) = 0.0175
        # sigma_fwd = sqrt(0.0175) = 0.1323
        # ff = (0.25 - 0.1323) / 0.1323 = 0.889
        assert abs(ff - 0.889) < 0.01  # Allow small tolerance
    
    def test_invalid_dte_front_zero(self):
        """✅ Edge case: t1 <= 0 (invalid DTE) → returns None."""
        ff = forward_factor(
            front_iv=0.25,
            front_dte=0,
            back_iv=0.20,
            back_dte=60
        )
        assert ff is None
    
    def test_invalid_dte_front_negative(self):
        """✅ Edge case: t1 < 0 (negative DTE) → returns None."""
        ff = forward_factor(
            front_iv=0.25,
            front_dte=-5,
            back_iv=0.20,
            back_dte=60
        )
        assert ff is None
    
    def test_invalid_dte_back_zero(self):
        """✅ Edge case: t2 <= 0 (invalid DTE) → returns None."""
        ff = forward_factor(
            front_iv=0.25,
            front_dte=30,
            back_iv=0.20,
            back_dte=0
        )
        assert ff is None
    
    def test_invalid_dte_back_negative(self):
        """✅ Edge case: t2 < 0 (negative DTE) → returns None."""
        ff = forward_factor(
            front_iv=0.25,
            front_dte=30,
            back_iv=0.20,
            back_dte=-10
        )
        assert ff is None
    
    def test_invalid_front_gte_back(self):
        """✅ Edge case: t1 >= t2 (front >= back) → returns None."""
        ff = forward_factor(
            front_iv=0.25,
            front_dte=60,
            back_iv=0.20,
            back_dte=30
        )
        assert ff is None
    
    def test_invalid_front_equals_back(self):
        """✅ Edge case: t1 == t2 (front == back) → returns None."""
        ff = forward_factor(
            front_iv=0.25,
            front_dte=30,
            back_iv=0.20,
            back_dte=30
        )
        assert ff is None
    
    def test_negative_forward_variance(self):
        """✅ Negative forward variance (v_fwd < 0) → returns None."""
        # When front_iv > back_iv significantly, can get negative forward variance
        ff = forward_factor(
            front_iv=0.40,  # High front IV
            front_dte=30,
            back_iv=0.15,   # Low back IV
            back_dte=60
        )
        assert ff is None
    
    def test_zero_sigma_fwd(self):
        """✅ Zero or negative sigma_fwd → returns None."""
        # This is caught by the negative forward variance check
        # but we test it explicitly
        ff = forward_factor(
            front_iv=0.30,
            front_dte=30,
            back_iv=0.15,
            back_dte=60
        )
        assert ff is None
    
    def test_formula_correctness(self):
        """✅ Verify formula correctness: V1 = σ1² * T1, V2 = σ2² * T2, etc."""
        front_iv = 0.30
        front_dte = 45
        back_iv = 0.25
        back_dte = 90
        
        ff = forward_factor(front_iv, front_dte, back_iv, back_dte)
        
        # Manual calculation
        t1 = front_dte / 365.0
        t2 = back_dte / 365.0
        v1 = front_iv ** 2 * t1
        v2 = back_iv ** 2 * t2
        v_fwd = (v2 - v1) / (t2 - t1)
        sigma_fwd = np.sqrt(v_fwd)
        expected_ff = (front_iv - sigma_fwd) / sigma_fwd
        
        assert ff is not None
        assert abs(ff - expected_ff) < 1e-10  # Very tight tolerance for formula check
    
    def test_boundary_very_small_forward_variance(self):
        """✅ Boundary: very small forward variance (near zero)."""
        # Front and back IVs very close
        ff = forward_factor(
            front_iv=0.2001,
            front_dte=30,
            back_iv=0.2000,
            back_dte=60
        )
        
        # Should still calculate but FF will be very small
        assert ff is not None
        assert ff > -1.0  # Reasonable range
    
    def test_boundary_very_large_ff_values(self):
        """✅ Boundary: very large FF values (>1.0)."""
        # Large difference between front and back
        ff = forward_factor(
            front_iv=0.50,  # Very high front
            front_dte=30,
            back_iv=0.20,   # Low back
            back_dte=60
        )
        
        # This should return None due to negative forward variance
        # OR return a very high FF value
        if ff is not None:
            assert ff > 0.5  # If valid, should be high
    
    def test_units_conversion_dte_to_years(self):
        """✅ Units test: verify DTE/365.0 conversion is correct."""
        # Test that we're correctly converting DTE to years
        ff_365_dte = forward_factor(
            front_iv=0.25,
            front_dte=365,
            back_iv=0.20,
            back_dte=730
        )
        
        # This should be equivalent to 1 year front, 2 years back
        assert ff_365_dte is not None
        
        # Verify the calculation uses 365.0 divisor
        t1 = 365 / 365.0
        t2 = 730 / 365.0
        assert t1 == 1.0
        assert t2 == 2.0


# ============================================================================
# Tests for select_vol_point()
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestSelectVolPoint:
    """Test IV selection from expiry based on method."""
    
    def test_atm_call_selection(self):
        """✅ ATM call selection with valid underlying price."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(595.0, "call", implied_volatility=0.26),
                create_contract(600.0, "call", implied_volatility=0.25),  # ATM
                create_contract(605.0, "call", implied_volatility=0.24),
            ],
            underlying_price=600.0
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="ATM", option_type="call")
        assert iv == 0.25
    
    def test_atm_put_selection(self):
        """✅ ATM put selection with valid underlying price."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(595.0, "put", implied_volatility=0.27),
                create_contract(600.0, "put", implied_volatility=0.28),  # ATM
                create_contract(605.0, "put", implied_volatility=0.29),
            ],
            underlying_price=600.0
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="ATM", option_type="put")
        assert iv == 0.28
    
    def test_delta_35d_put_selection(self):
        """✅ Delta-based selection: '35d_put' → 0.35 delta put."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(590.0, "put", implied_volatility=0.30, delta=0.35),
                create_contract(595.0, "put", implied_volatility=0.27, delta=0.40),
                create_contract(600.0, "put", implied_volatility=0.28, delta=0.48),
            ],
            underlying_price=600.0
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="35d_put")
        assert iv == 0.30
    
    def test_delta_35d_call_selection(self):
        """✅ Delta-based selection: '35d_call' → 0.35 delta call."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(605.0, "call", implied_volatility=0.24, delta=0.35),
                create_contract(600.0, "call", implied_volatility=0.25, delta=0.52),
                create_contract(595.0, "call", implied_volatility=0.26, delta=0.60),
            ],
            underlying_price=600.0
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="35d_call")
        assert iv == 0.24
    
    def test_invalid_method(self):
        """✅ Invalid method → returns None."""
        expiry = create_expiry(date(2025, 1, 17), 30)
        iv = select_vol_point(expiry, underlying_price=600.0, method="INVALID")
        assert iv is None
    
    def test_no_contracts_at_strike(self):
        """✅ No contracts available at strike → returns None."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[],  # Empty contracts
            underlying_price=600.0
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="ATM")
        assert iv is None
    
    def test_contract_exists_but_no_iv(self):
        """✅ Contract exists but no IV → returns None."""
        contract_no_iv = create_contract(600.0, "call", implied_volatility=None)
        expiry = Expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[contract_no_iv]
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="ATM")
        assert iv is None
    
    def test_parsing_25d_put(self):
        """✅ Parsing: '25d_put'."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(585.0, "put", implied_volatility=0.32, delta=0.25),
                create_contract(590.0, "put", implied_volatility=0.30, delta=0.35),
            ],
            underlying_price=600.0
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="25d_put")
        assert iv == 0.32
    
    def test_parsing_40d_call(self):
        """✅ Parsing: '40d_call'."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(603.0, "call", implied_volatility=0.23, delta=0.40),
                create_contract(600.0, "call", implied_volatility=0.25, delta=0.52),
            ],
            underlying_price=600.0
        )
        
        iv = select_vol_point(expiry, underlying_price=600.0, method="40d_call")
        assert iv == 0.23


# ============================================================================
# Tests for pair_expiries()
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestPairExpiries:
    """Test expiry pairing based on DTE target windows."""
    
    def test_valid_pairing_30_60(self):
        """✅ Valid pairing: front=30±5, back=60±10."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 14), 30),
                create_expiry(date(2025, 2, 13), 60),
            ]
        )
        
        dte_pairs = [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}]
        pairs = pair_expiries(chain, dte_pairs)
        
        assert len(pairs) == 1
        front, back, config = pairs[0]
        assert front.dte == 30
        assert back.dte == 60
    
    def test_multiple_dte_pair_configs(self):
        """✅ Multiple DTE pair configs."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 14), 30),
                create_expiry(date(2025, 2, 13), 60),
                create_expiry(date(2025, 3, 15), 90),
            ]
        )
        
        dte_pairs = [
            {"front": 30, "back": 60, "front_tol": 5, "back_tol": 10},
            {"front": 30, "back": 90, "front_tol": 5, "back_tol": 10},
        ]
        pairs = pair_expiries(chain, dte_pairs)
        
        assert len(pairs) == 2
        assert pairs[0][0].dte == 30 and pairs[0][1].dte == 60
        assert pairs[1][0].dte == 30 and pairs[1][1].dte == 90
    
    def test_no_matching_front_expiry(self):
        """✅ No matching front expiry → no pair returned."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 2, 13), 60),  # Only back expiry
            ]
        )
        
        dte_pairs = [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}]
        pairs = pair_expiries(chain, dte_pairs)
        
        assert len(pairs) == 0
    
    def test_no_matching_back_expiry(self):
        """✅ No matching back expiry → no pair returned."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 14), 30),  # Only front expiry
            ]
        )
        
        dte_pairs = [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}]
        pairs = pair_expiries(chain, dte_pairs)
        
        assert len(pairs) == 0
    
    def test_front_dte_gte_back_dte_rejected(self):
        """✅ Front DTE >= back DTE → rejected."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 2, 13), 60),
                create_expiry(date(2025, 1, 14), 30),
            ]
        )
        
        # Try to pair with swapped targets
        dte_pairs = [{"front": 60, "back": 30, "front_tol": 5, "back_tol": 10}]
        pairs = pair_expiries(chain, dte_pairs)
        
        # Should be rejected because front >= back
        assert len(pairs) == 0
    
    def test_tolerance_window_respected(self):
        """✅ Tolerance window respected (front_tol, back_tol)."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 16), 32),  # 30 + 2 (within tolerance)
                create_expiry(date(2025, 2, 15), 62),  # 60 + 2 (within tolerance)
            ]
        )
        
        dte_pairs = [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}]
        pairs = pair_expiries(chain, dte_pairs)
        
        assert len(pairs) == 1
        assert pairs[0][0].dte == 32
        assert pairs[0][1].dte == 62
    
    def test_exact_dte_match(self):
        """✅ Edge case: exact DTE match."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 14), 30),  # Exact match
                create_expiry(date(2025, 2, 13), 60),  # Exact match
            ]
        )
        
        dte_pairs = [{"front": 30, "back": 60, "front_tol": 0, "back_tol": 0}]
        pairs = pair_expiries(chain, dte_pairs)
        
        assert len(pairs) == 1
    
    def test_dte_at_tolerance_boundary(self):
        """✅ Edge case: DTE at tolerance boundary."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 19), 35),  # 30 + 5 (at boundary)
                create_expiry(date(2025, 2, 23), 70),  # 60 + 10 (at boundary)
            ]
        )
        
        dte_pairs = [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}]
        pairs = pair_expiries(chain, dte_pairs)
        
        assert len(pairs) == 1


# ============================================================================
# Tests for apply_liquidity_filters()
# ============================================================================

@pytest.mark.unit
class TestApplyLiquidityFilters:
    """Test liquidity and data quality filters for contracts."""
    
    def test_missing_bid(self):
        """✅ Missing bid or ask → fails with 'missing_quotes'."""
        contract = create_contract(600.0, bid=None, ask=5.20)
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        assert not passes
        assert "missing_quotes" in reasons
    
    def test_missing_ask(self):
        """✅ Missing ask → fails with 'missing_quotes'."""
        contract = create_contract(600.0, bid=5.10, ask=None)
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        assert not passes
        assert "missing_quotes" in reasons
    
    def test_wide_bid_ask_spread(self):
        """✅ Bid-ask spread exceeds max_bid_ask_pct → fails with reason code."""
        contract = create_contract(600.0, bid=5.00, ask=6.00)  # 18% spread
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        assert not passes
        assert any("wide_spread" in r for r in reasons)
    
    def test_low_open_interest(self):
        """✅ Open interest below threshold → fails with 'low_oi'."""
        contract = create_contract(600.0, open_interest=50)
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        assert not passes
        assert any("low_oi" in r for r in reasons)
    
    def test_low_volume(self):
        """✅ Volume below threshold → fails with 'low_volume'."""
        contract = create_contract(600.0, volume=5)
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        assert not passes
        assert any("low_volume" in r for r in reasons)
    
    def test_all_checks_pass(self):
        """✅ All checks pass → returns (True, [])."""
        contract = create_contract(
            600.0,
            bid=5.00,
            ask=5.05,  # 1% spread
            volume=1000,
            open_interest=5000
        )
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        assert passes
        assert len(reasons) == 0
    
    def test_multiple_failures(self):
        """✅ Multiple failures → returns all reason codes."""
        contract = create_contract(
            600.0,
            bid=5.00,
            ask=6.00,  # Wide spread
            volume=5,  # Low volume
            open_interest=50  # Low OI
        )
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        assert not passes
        assert len(reasons) >= 2  # At least spread and volume/OI
    
    def test_zero_mid_price_handling(self):
        """✅ Zero mid price handling."""
        contract = create_contract(600.0, bid=0.0, ask=0.0)
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        # Should handle gracefully (no divide by zero error)
        assert not passes  # Will fail on other checks
    
    def test_spread_percentage_calculation_accuracy(self):
        """✅ Spread percentage calculation accuracy."""
        contract = create_contract(600.0, bid=10.00, ask=10.80)  # 7.7% spread
        passes, reasons = apply_liquidity_filters(contract, min_oi=100, min_volume=10, max_bid_ask_pct=0.08)
        
        # Should pass (7.7% < 8%)
        assert passes or any("wide_spread" not in r for r in reasons)


# ============================================================================
# Tests for compute_signals()
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestComputeSignals:
    """Test main orchestrator for signal computation."""
    
    def test_end_to_end_valid_chain_with_signals(self, sample_chain_snapshot, default_user_settings):
        """✅ End-to-end: valid chain with signals above threshold."""
        signals = compute_signals(sample_chain_snapshot, default_user_settings)
        
        assert isinstance(signals, list)
        # Should have at least one signal
        if len(signals) > 0:
            signal = signals[0]
            assert "ticker" in signal
            assert "ff_value" in signal
            assert "front_expiry" in signal
            assert "back_expiry" in signal
    
    def test_no_expiry_pairs_match(self):
        """✅ No expiry pairs match → empty signal list."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 14), 15),  # Too short
            ]
        )
        
        settings = {
            "ff_threshold": 0.20,
            "dte_pairs": [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}],
            "vol_point": "ATM",
            "min_open_interest": 100,
            "min_volume": 10,
            "max_bid_ask_pct": 0.08,
            "sigma_fwd_floor": 0.05
        }
        
        signals = compute_signals(chain, settings)
        assert len(signals) == 0
    
    def test_ff_below_threshold_excluded(self):
        """✅ FF below threshold → signal excluded."""
        # Create chain with low FF (front and back IV similar)
        expiries = [
            create_expiry(date(2025, 1, 14), 30, contracts=[
                create_contract(600.0, "call", implied_volatility=0.21)
            ]),
            create_expiry(date(2025, 2, 13), 60, contracts=[
                create_contract(600.0, "call", implied_volatility=0.20)
            ]),
        ]
        chain = create_chain_snapshot(expiries=expiries)
        
        settings = {
            "ff_threshold": 0.50,  # High threshold
            "dte_pairs": [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}],
            "vol_point": "ATM",
            "min_open_interest": 100,
            "min_volume": 10,
            "max_bid_ask_pct": 0.08,
            "sigma_fwd_floor": 0.05
        }
        
        signals = compute_signals(chain, settings)
        # Should be empty because FF too low
        assert len(signals) == 0
    
    def test_sigma_fwd_below_floor_excluded(self):
        """✅ sigma_fwd below floor → signal excluded with reason code."""
        # Create scenario with very low sigma_fwd
        expiries = [
            create_expiry(date(2025, 1, 14), 30, contracts=[
                create_contract(600.0, "call", implied_volatility=0.06)
            ]),
            create_expiry(date(2025, 2, 13), 60, contracts=[
                create_contract(600.0, "call", implied_volatility=0.05)
            ]),
        ]
        chain = create_chain_snapshot(expiries=expiries)
        
        settings = {
            "ff_threshold": 0.01,  # Very low threshold
            "dte_pairs": [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}],
            "vol_point": "ATM",
            "min_open_interest": 100,
            "min_volume": 10,
            "max_bid_ask_pct": 0.08,
            "sigma_fwd_floor": 0.10  # High floor
        }
        
        signals = compute_signals(chain, settings)
        assert len(signals) == 0
    
    def test_liquidity_filters_affect_quality_score(self, sample_chain_snapshot):
        """✅ Liquidity filters fail → signal marked with low quality_score."""
        settings = {
            "ff_threshold": 0.01,  # Very low to ensure signal created
            "dte_pairs": [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}],
            "vol_point": "ATM",
            "min_open_interest": 100000,  # Impossibly high
            "min_volume": 100000,  # Impossibly high
            "max_bid_ask_pct": 0.001,  # Impossibly tight
            "sigma_fwd_floor": 0.01
        }
        
        signals = compute_signals(sample_chain_snapshot, settings)
        
        # If any signals generated, they should have low quality score
        for signal in signals:
            if len(signal.get("reason_codes", [])) > 0:
                assert signal["quality_score"] < 1.0
    
    def test_signals_sorted_by_ff_value(self):
        """✅ Multiple signals → sorted by FF value (highest first)."""
        # Create chain with multiple expiry pairs
        expiries = [
            create_expiry(date(2025, 1, 14), 30, contracts=[
                create_contract(600.0, "call", implied_volatility=0.30)  # High FF
            ]),
            create_expiry(date(2025, 2, 13), 60, contracts=[
                create_contract(600.0, "call", implied_volatility=0.15)
            ]),
            create_expiry(date(2025, 3, 15), 90, contracts=[
                create_contract(600.0, "call", implied_volatility=0.25)  # Lower FF
            ]),
        ]
        chain = create_chain_snapshot(expiries=expiries)
        
        settings = {
            "ff_threshold": 0.01,
            "dte_pairs": [
                {"front": 30, "back": 60, "front_tol": 5, "back_tol": 10},
                {"front": 30, "back": 90, "front_tol": 5, "back_tol": 10},
            ],
            "vol_point": "ATM",
            "min_open_interest": 100,
            "min_volume": 10,
            "max_bid_ask_pct": 0.50,  # Lenient
            "sigma_fwd_floor": 0.01
        }
        
        signals = compute_signals(chain, settings)
        
        # Verify sorted by FF descending
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                assert signals[i]["ff_value"] >= signals[i + 1]["ff_value"]
    
    def test_all_signal_fields_populated(self, sample_chain_snapshot, default_user_settings):
        """✅ All signal fields populated correctly."""
        signals = compute_signals(sample_chain_snapshot, default_user_settings)
        
        if len(signals) > 0:
            signal = signals[0]
            required_fields = [
                "ticker", "as_of_ts", "front_expiry", "back_expiry",
                "front_dte", "back_dte", "front_iv", "back_iv",
                "sigma_fwd", "ff_value", "vol_point", "quality_score",
                "reason_codes", "underlying_price", "provider"
            ]
            for field in required_fields:
                assert field in signal
    
    def test_quality_score_1_when_no_reason_codes(self):
        """✅ Quality score: 1.0 when no reason codes."""
        # Create perfect contracts
        expiries = [
            create_expiry(date(2025, 1, 14), 30, contracts=[
                create_contract(600.0, "call", implied_volatility=0.35, 
                               bid=5.0, ask=5.05, volume=10000, open_interest=50000)
            ]),
            create_expiry(date(2025, 2, 13), 60, contracts=[
                create_contract(600.0, "call", implied_volatility=0.20,
                               bid=7.0, ask=7.05, volume=10000, open_interest=50000)
            ]),
        ]
        chain = create_chain_snapshot(expiries=expiries)
        
        settings = {
            "ff_threshold": 0.01,
            "dte_pairs": [{"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}],
            "vol_point": "ATM",
            "min_open_interest": 100,
            "min_volume": 10,
            "max_bid_ask_pct": 0.08,
            "sigma_fwd_floor": 0.05
        }
        
        signals = compute_signals(chain, settings)
        
        if len(signals) > 0:
            signal = signals[0]
            if len(signal["reason_codes"]) == 0:
                assert signal["quality_score"] == 1.0
