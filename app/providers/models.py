"""Data models for option chain snapshots."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional


@dataclass
class Contract:
    """Individual option contract."""
    symbol: str
    strike: float
    expiry: date
    option_type: str  # "call" or "put"
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    volume: Optional[int]
    open_interest: Optional[int]
    implied_volatility: Optional[float]
    delta: Optional[float]
    gamma: Optional[float]
    theta: Optional[float]
    vega: Optional[float]


@dataclass
class Expiry:
    """Option expiry with all contracts and metadata."""
    expiry_date: date
    dte: int
    contracts: List[Contract]
    
    def get_atm_contract(self, underlying_price: float, option_type: str = "call") -> Optional[Contract]:
        """Get ATM contract for this expiry."""
        type_contracts = [c for c in self.contracts if c.option_type == option_type]
        if not type_contracts:
            return None
        
        # Find strike closest to underlying price
        return min(type_contracts, key=lambda c: abs(c.strike - underlying_price))
    
    def get_delta_contract(self, target_delta: float, option_type: str = "call") -> Optional[Contract]:
        """Get contract with delta closest to target."""
        type_contracts = [
            c for c in self.contracts 
            if c.option_type == option_type and c.delta is not None
        ]
        if not type_contracts:
            return None
        
        return min(type_contracts, key=lambda c: abs(abs(c.delta) - abs(target_delta)))


@dataclass
class ChainSnapshot:
    """Complete option chain snapshot for a ticker."""
    ticker: str
    as_of: datetime
    underlying_price: float
    expiries: List[Expiry]
    provider: str
    
    def get_expiry_by_dte(self, target_dte: int, tolerance: int = 5) -> Optional[Expiry]:
        """Get expiry closest to target DTE within tolerance."""
        candidates = [e for e in self.expiries if abs(e.dte - target_dte) <= tolerance]
        if not candidates:
            return None
        
        return min(candidates, key=lambda e: abs(e.dte - target_dte))
