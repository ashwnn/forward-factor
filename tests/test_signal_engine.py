"""Tests for signal engine Forward Factor calculation."""
import pytest
from app.services.signal_engine import forward_factor


def test_forward_factor_valid():
    """Test valid Forward Factor calculation."""
    # Front: 30 DTE, 25% IV
    # Back: 60 DTE, 20% IV
    ff = forward_factor(0.25, 30, 0.20, 60)
    
    assert ff is not None
    # Front IV higher than forward IV = positive FF (backwardation)
    assert ff > 0


def test_forward_factor_negative_variance():
    """Test that negative forward variance returns None."""
    # Front: 30 DTE, 20% IV
    # Back: 60 DTE, 25% IV (higher than front)
    # This should give negative forward variance
    ff = forward_factor(0.20, 30, 0.25, 60)
    
    # Should return None for negative variance
    assert ff is None


def test_forward_factor_invalid_dte():
    """Test invalid DTE inputs."""
    # T1 >= T2
    ff = forward_factor(0.25, 60, 0.20, 30)
    assert ff is None
    
    # Zero DTE
    ff = forward_factor(0.25, 0, 0.20, 30)
    assert ff is None
    
    # Negative DTE
    ff = forward_factor(0.25, -10, 0.20, 30)
    assert ff is None


def test_forward_factor_zero_sigma_fwd():
    """Test edge case where sigma_fwd is zero."""
    # Same IV for both expiries should give sigma_fwd = 0
    ff = forward_factor(0.20, 30, 0.20, 60)
    
    # Should handle division by zero gracefully
    # In this case, sigma_fwd won't be exactly zero but very small
    # The function should still return a valid result
    assert ff is not None


def test_forward_factor_calculation():
    """Test exact Forward Factor calculation with known values."""
    # Example from strategy.md:
    # Front: 30 DTE, 30% IV
    # Back: 60 DTE, 25% IV
    
    front_iv = 0.30
    front_dte = 30
    back_iv = 0.25
    back_dte = 60
    
    # Manual calculation:
    # T1 = 30/365 = 0.0822
    # T2 = 60/365 = 0.1644
    # V1 = 0.30^2 * 0.0822 = 0.00740
    # V2 = 0.25^2 * 0.1644 = 0.01027
    # V_fwd = (0.01027 - 0.00740) / (0.1644 - 0.0822) = 0.0349
    # sigma_fwd = sqrt(0.0349) = 0.1868
    # FF = (0.30 - 0.1868) / 0.1868 = 0.606 = 60.6%
    
    ff = forward_factor(front_iv, front_dte, back_iv, back_dte)
    
    assert ff is not None
    # Should be around 0.60 (60%)
    assert 0.55 < ff < 0.65


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
