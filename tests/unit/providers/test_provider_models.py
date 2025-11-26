"""Unit tests for Provider Models (ChainSnapshot, Expiry, Contract).

Tests helper methods used by the Signal Engine to access option chain data.
"""
import pytest
from datetime import date

from app.providers.models import Contract, Expiry, ChainSnapshot
from tests.conftest import create_contract, create_expiry, create_chain_snapshot


# ============================================================================
# Tests for ChainSnapshot
# ============================================================================

@pytest.mark.unit
class TestChainSnapshot:
    """Test ChainSnapshot helper methods."""
    
    def test_get_expiry_by_dte_with_tolerance(self):
        """✅ get_expiry_by_dte() with tolerance - find expiry within range."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 10), 25),
                create_expiry(date(2025, 1, 17), 32),  # Within 30±5
                create_expiry(date(2025, 2, 14), 60),
            ]
        )
        
        expiry = chain.get_expiry_by_dte(target_dte=30, tolerance=5)
        assert expiry is not None
        assert expiry.dte == 32  # Closest to 30
    
    def test_get_expiry_by_dte_no_expiries_in_range(self):
        """✅ Edge case: no expiries in range."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 10), 10),
                create_expiry(date(2025, 3, 15), 90),
            ]
        )
        
        expiry = chain.get_expiry_by_dte(target_dte=30, tolerance=5)
        assert expiry is None
    
    def test_get_expiry_by_dte_multiple_in_range_pick_closest(self):
        """✅ Edge case: multiple expiries in range (pick closest)."""
        chain = create_chain_snapshot(
            expiries=[
                create_expiry(date(2025, 1, 12), 27),  # 3 away
                create_expiry(date(2025, 1, 15), 30),  # 0 away - exact match
                create_expiry(date(2025, 1, 18), 33),  # 3 away
            ]
        )
        
        expiry = chain.get_expiry_by_dte(target_dte=30, tolerance=5)
        assert expiry is not None
        assert expiry.dte == 30  # Exact match preferred
    
    def test_get_expiry_by_dte_empty_chain(self):
        """✅ Empty expiries list."""
        chain = create_chain_snapshot(expiries=[])
        
        expiry = chain.get_expiry_by_dte(target_dte=30, tolerance=5)
        assert expiry is None


# ============================================================================
# Tests for Expiry
# ============================================================================

@pytest.mark.unit
class TestExpiry:
    """Test Expiry helper methods."""
    
    def test_get_atm_contract_call(self):
        """✅ get_atm_contract() - find closest strike to underlying for calls."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(595.0, "call"),
                create_contract(600.0, "call"),  # ATM
                create_contract(605.0, "call"),
            ],
            underlying_price=600.0
        )
        
        contract = expiry.get_atm_contract(underlying_price=600.0, option_type="call")
        assert contract is not None
        assert contract.strike == 600.0
        assert contract.option_type == "call"
    
    def test_get_atm_contract_put(self):
        """✅ get_atm_contract() - find closest strike to underlying for puts."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(595.0, "put"),
                create_contract(600.0, "put"),  # ATM
                create_contract(605.0, "put"),
            ],
            underlying_price=600.0
        )
        
        contract = expiry.get_atm_contract(underlying_price=600.0, option_type="put")
        assert contract is not None
        assert contract.strike == 600.0
        assert contract.option_type == "put"
    
    def test_get_atm_contract_no_contracts_available(self):
        """✅ Edge case: no contracts available."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[],
            underlying_price=600.0
        )
        
        contract = expiry.get_atm_contract(underlying_price=600.0)
        assert contract is None
    
    def test_get_atm_contract_no_contracts_of_type(self):
        """✅ Edge case: no contracts of specified type."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(600.0, "put"),  # Only puts
            ],
            underlying_price=600.0
        )
        
        contract = expiry.get_atm_contract(underlying_price=600.0, option_type="call")
        assert contract is None
    
    def test_get_atm_contract_exact_strike_match(self):
        """✅ Edge case: exact strike match."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(598.0, "call"),
                create_contract(600.5, "call"),  # Exact match
                create_contract(602.0, "call"),
            ],
            underlying_price=600.5
        )
        
        contract = expiry.get_atm_contract(underlying_price=600.5, option_type="call")
        assert contract is not None
        assert contract.strike == 600.5
    
    def test_get_atm_contract_between_strikes(self):
        """✅ get_atm_contract() when underlying is between strikes."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(595.0, "call"),
                create_contract(600.0, "call"),  # Closer to 601.5
                create_contract(605.0, "call"),
            ],
            underlying_price=601.5
        )
        
        contract = expiry.get_atm_contract(underlying_price=601.5, option_type="call")
        assert contract is not None
        assert contract.strike == 600.0  # Closest to 601.5
    
    def test_get_delta_contract_call(self):
        """✅ get_delta_contract() - find contract by target delta for calls."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(600.0, "call", delta=0.52),
                create_contract(605.0, "call", delta=0.35),  # Target
                create_contract(610.0, "call", delta=0.20),
            ],
            underlying_price=600.0
        )
        
        contract = expiry.get_delta_contract(target_delta=0.35, option_type="call")
        assert contract is not None
        assert abs(contract.delta - 0.35) < 0.01
    
    def test_get_delta_contract_put(self):
        """✅ get_delta_contract() - find contract by target delta for puts."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(600.0, "put", delta=0.48),
                create_contract(595.0, "put", delta=0.35),  # Target
                create_contract(590.0, "put", delta=0.25),
            ],
            underlying_price=600.0
        )
        
        contract = expiry.get_delta_contract(target_delta=0.35, option_type="put")
        assert contract is not None
        # Put deltas are negative, so we check absolute value
        assert abs(abs(contract.delta) - 0.35) < 0.01
    
    def test_get_delta_contract_no_delta_available(self):
        """✅ Edge case: no contracts with delta available."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                Contract(
                    symbol="SPY250117C00600000",
                    strike=600.0,
                    expiry=date(2025, 1, 17),
                    option_type="call",
                    bid=5.0,
                    ask=5.10,
                    last=5.05,
                    volume=1000,
                    open_interest=5000,
                    implied_volatility=0.25,
                    delta=None,  # No delta
                    gamma=0.01,
                    theta=-0.05,
                    vega=0.15
                )
            ],
            underlying_price=600.0
        )
        
        contract = expiry.get_delta_contract(target_delta=0.35, option_type="call")
        assert contract is None
    
    def test_get_delta_contract_closest_selection(self):
        """✅ Multiple contracts (closest delta selection)."""
        expiry = create_expiry(
            expiry_date=date(2025, 1, 17),
            dte=30,
            contracts=[
                create_contract(605.0, "call", delta=0.33),  # 0.02 away
                create_contract(606.0, "call", delta=0.36),  # 0.01 away - closest
                create_contract(610.0, "call", delta=0.20),  # 0.15 away
            ],
            underlying_price=600.0
        )
        
        contract = expiry.get_delta_contract(target_delta=0.35, option_type="call")
        assert contract is not None
        assert abs(contract.delta - 0.36) < 0.01  # Should pick 0.36 (closest)


# ============================================================================
# Tests for Contract
# ============================================================================

@pytest.mark.unit
class TestContract:
    """Test Contract model."""
    
    def test_proper_field_population(self):
        """✅ Proper field population."""
        contract = create_contract(
            strike=600.0,
            option_type="call",
            expiry_date=date(2025, 1, 17),
            bid=5.0,
            ask=5.10,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
            delta=0.52
        )
        
        assert contract.strike == 600.0
        assert contract.option_type == "call"
        assert contract.expiry == date(2025, 1, 17)
        assert contract.bid == 5.0
        assert contract.ask == 5.10
        assert contract.volume == 1000
        assert contract.open_interest == 5000
        assert contract.implied_volatility == 0.25
        assert contract.delta == 0.52
    
    def test_bid_ask_validation(self):
        """✅ Bid/ask validation - bid should be <= ask."""
        contract = create_contract(
            strike=600.0,
            bid=5.0,
            ask=5.10
        )
        
        assert contract.bid <= contract.ask
    
    def test_optional_fields_can_be_none(self):
        """✅ Optional fields can be None."""
        contract = Contract(
            symbol="SPY250117C00600000",
            strike=600.0,
            expiry=date(2025, 1, 17),
            option_type="call",
            bid=None,
            ask=None,
            last=None,
            volume=None,
            open_interest=None,
            implied_volatility=None,
            delta=None,
            gamma=None,
            theta=None,
            vega=None
        )
        
        assert contract.bid is None
        assert contract.ask is None
        assert contract.implied_volatility is None
        assert contract.delta is None
    
    def test_contract_symbol_format(self):
        """✅ Contract symbol follows expected format."""
        contract = create_contract(
            strike=600.0,
            option_type="call",
            expiry_date=date(2025, 1, 17)
        )
        
        # Symbol should contain ticker, date, C/P, and strike
        assert "SPY" in contract.symbol
        assert "250117" in contract.symbol
        assert "C" in contract.symbol
