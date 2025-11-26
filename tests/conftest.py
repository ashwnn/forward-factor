"""Shared pytest fixtures for Signal Engine tests."""
import pytest
from datetime import date, datetime
from typing import List
from app.providers.models import Contract, Expiry, ChainSnapshot


@pytest.fixture
def sample_contract_call():
    """Sample call contract with typical values."""
    return Contract(
        symbol="SPY250117C00600000",
        strike=600.0,
        expiry=date(2025, 1, 17),
        option_type="call",
        bid=5.50,
        ask=5.60,
        last=5.55,
        volume=1000,
        open_interest=5000,
        implied_volatility=0.25,
        delta=0.52,
        gamma=0.01,
        theta=-0.05,
        vega=0.15
    )


@pytest.fixture
def sample_contract_put():
    """Sample put contract with typical values."""
    return Contract(
        symbol="SPY250117P00600000",
        strike=600.0,
        expiry=date(2025, 1, 17),
        option_type="put",
        bid=4.80,
        ask=4.90,
        last=4.85,
        volume=800,
        open_interest=4000,
        implied_volatility=0.28,
        delta=-0.48,
        gamma=0.01,
        theta=-0.04,
        vega=0.14
    )


def create_contract(
    strike: float,
    option_type: str = "call",
    expiry_date: date = date(2025, 1, 17),
    bid: float = 5.0,
    ask: float = 5.10,
    volume: int = 1000,
    open_interest: int = 5000,
    implied_volatility: float = 0.25,
    delta: float = 0.50
) -> Contract:
    """Factory function to create Contract instances for testing."""
    return Contract(
        symbol=f"SPY{expiry_date.strftime('%y%m%d')}{'C' if option_type == 'call' else 'P'}{int(strike*1000):08d}",
        strike=strike,
        expiry=expiry_date,
        option_type=option_type,
        bid=bid,
        ask=ask,
        last=(bid + ask) / 2,
        volume=volume,
        open_interest=open_interest,
        implied_volatility=implied_volatility,
        delta=delta if option_type == "call" else -delta,
        gamma=0.01,
        theta=-0.05,
        vega=0.15
    )


def create_expiry(
    expiry_date: date,
    dte: int,
    contracts: List[Contract] = None,
    underlying_price: float = 600.0
) -> Expiry:
    """Factory function to create Expiry instances for testing."""
    if contracts is None:
        # Create default ATM contracts
        contracts = [
            create_contract(underlying_price - 5, "put", expiry_date, delta=0.45),
            create_contract(underlying_price, "call", expiry_date, delta=0.52),
            create_contract(underlying_price, "put", expiry_date, delta=0.48),
            create_contract(underlying_price + 5, "call", expiry_date, delta=0.55),
        ]
    
    return Expiry(
        expiry_date=expiry_date,
        dte=dte,
        contracts=contracts
    )


def create_chain_snapshot(
    ticker: str = "SPY",
    underlying_price: float = 600.0,
    expiries: List[Expiry] = None,
    as_of: datetime = None
) -> ChainSnapshot:
    """Factory function to create ChainSnapshot instances for testing."""
    if as_of is None:
        as_of = datetime(2024, 12, 15, 16, 0, 0)
    
    if expiries is None:
        # Create default expiries at 30 and 60 DTE
        expiries = [
            create_expiry(date(2025, 1, 14), 30, underlying_price=underlying_price),
            create_expiry(date(2025, 2, 13), 60, underlying_price=underlying_price),
        ]
    
    return ChainSnapshot(
        ticker=ticker,
        as_of=as_of,
        underlying_price=underlying_price,
        expiries=expiries,
        provider="polygon"
    )


@pytest.fixture
def sample_expiry_30dte():
    """Sample expiry at 30 DTE with realistic contracts."""
    expiry_date = date(2025, 1, 14)
    contracts = [
        # Calls at various strikes
        create_contract(595.0, "call", expiry_date, bid=10.0, ask=10.20, implied_volatility=0.26, delta=0.60),
        create_contract(600.0, "call", expiry_date, bid=7.0, ask=7.20, implied_volatility=0.25, delta=0.52),
        create_contract(605.0, "call", expiry_date, bid=4.5, ask=4.70, implied_volatility=0.24, delta=0.45),
        # Puts at various strikes
        create_contract(595.0, "put", expiry_date, bid=3.0, ask=3.20, implied_volatility=0.27, delta=0.40),
        create_contract(600.0, "put", expiry_date, bid=5.0, ask=5.20, implied_volatility=0.28, delta=0.48),
        create_contract(605.0, "put", expiry_date, bid=8.0, ask=8.20, implied_volatility=0.29, delta=0.55),
        # Delta strikes for testing
        create_contract(590.0, "put", expiry_date, bid=2.0, ask=2.20, implied_volatility=0.30, delta=0.35),
    ]
    return create_expiry(expiry_date, 30, contracts)


@pytest.fixture
def sample_expiry_60dte():
    """Sample expiry at 60 DTE with realistic contracts."""
    expiry_date = date(2025, 2, 13)
    contracts = [
        # Calls at various strikes
        create_contract(595.0, "call", expiry_date, bid=12.0, ask=12.30, implied_volatility=0.22, delta=0.58),
        create_contract(600.0, "call", expiry_date, bid=9.0, ask=9.30, implied_volatility=0.20, delta=0.50),
        create_contract(605.0, "call", expiry_date, bid=6.5, ask=6.80, implied_volatility=0.19, delta=0.42),
        # Puts at various strikes
        create_contract(595.0, "put", expiry_date, bid=4.0, ask=4.30, implied_volatility=0.23, delta=0.42),
        create_contract(600.0, "put", expiry_date, bid=6.5, ask=6.80, implied_volatility=0.24, delta=0.50),
        create_contract(605.0, "put", expiry_date, bid=9.5, ask=9.80, implied_volatility=0.25, delta=0.58),
        # Delta strikes for testing
        create_contract(590.0, "put", expiry_date, bid=2.5, ask=2.80, implied_volatility=0.26, delta=0.35),
    ]
    return create_expiry(expiry_date, 60, contracts)


@pytest.fixture
def sample_chain_snapshot(sample_expiry_30dte, sample_expiry_60dte):
    """Sample ChainSnapshot with 30 and 60 DTE expiries."""
    return create_chain_snapshot(
        ticker="SPY",
        underlying_price=600.0,
        expiries=[sample_expiry_30dte, sample_expiry_60dte]
    )


@pytest.fixture
def default_user_settings():
    """Default user settings for signal computation."""
    return {
        "ff_threshold": 0.20,
        "dte_pairs": [
            {"front": 30, "back": 60, "front_tol": 5, "back_tol": 10}
        ],
        "vol_point": "ATM",
        "min_open_interest": 100,
        "min_volume": 10,
        "max_bid_ask_pct": 0.08,
        "sigma_fwd_floor": 0.05
    }
