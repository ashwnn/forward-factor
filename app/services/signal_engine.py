"""Core signal engine for Forward Factor calculation."""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from datetime import date
from app.providers.models import ChainSnapshot, Expiry, Contract
from app.utils.time import calculate_dte


def forward_factor(front_iv: float, front_dte: int, back_iv: float, back_dte: int) -> Optional[float]:
    """
    Calculate Forward Factor given front and back IVs and DTEs.
    
    Formula from strategy.md:
    V1 = σ1² * T1
    V2 = σ2² * T2
    V_fwd = (V2 - V1) / (T2 - T1)
    σ_fwd = sqrt(V_fwd)
    FF = (σ1 - σ_fwd) / σ_fwd
    
    Args:
        front_iv: Front expiry implied volatility (decimal, e.g., 0.25 for 25%)
        front_dte: Front days to expiry
        back_iv: Back expiry implied volatility (decimal)
        back_dte: Back days to expiry
        
    Returns:
        Forward Factor value, or None if invalid
    """
    # Convert DTE to years
    t1 = front_dte / 365.0
    t2 = back_dte / 365.0
    
    # Validate inputs
    if t1 <= 0 or t2 <= 0 or t1 >= t2:
        return None
    
    # Total variance to each expiry
    v1 = (front_iv ** 2) * t1
    v2 = (back_iv ** 2) * t2
    
    # Annualized forward variance
    v_fwd = (v2 - v1) / (t2 - t1)
    
    # Reject negative forward variance
    if v_fwd < 0:
        return None
    
    # Forward volatility
    sigma_fwd = np.sqrt(v_fwd)
    
    # Avoid division by zero
    if sigma_fwd <= 0:
        return None
    
    # Forward Factor
    ff = (front_iv - sigma_fwd) / sigma_fwd
    
    return ff


def select_vol_point(
    expiry: Expiry,
    underlying_price: float,
    method: str = "ATM",
    option_type: str = "call"
) -> Optional[float]:
    """
    Select IV from expiry based on method.
    
    Args:
        expiry: Expiry object with contracts
        underlying_price: Current underlying price
        method: "ATM", "35d_put", "35d_call", etc.
        option_type: "call" or "put" for ATM selection
        
    Returns:
        Implied volatility (decimal), or None if not found
    """
    if method == "ATM":
        contract = expiry.get_atm_contract(underlying_price, option_type)
    elif method.endswith("d_put"):
        # Extract delta value (e.g., "35d_put" -> 0.35)
        delta_str = method.split("d_")[0]
        target_delta = float(delta_str) / 100.0
        contract = expiry.get_delta_contract(target_delta, "put")
    elif method.endswith("d_call"):
        delta_str = method.split("d_")[0]
        target_delta = float(delta_str) / 100.0
        contract = expiry.get_delta_contract(target_delta, "call")
    else:
        return None
    
    if contract is None or contract.implied_volatility is None:
        return None
    
    return contract.implied_volatility


def pair_expiries(
    chain: ChainSnapshot,
    dte_pairs: List[Dict[str, int]]
) -> List[Tuple[Expiry, Expiry, Dict[str, int]]]:
    """
    Pair expiries based on DTE target windows.
    
    Args:
        chain: ChainSnapshot with all expiries
        dte_pairs: List of dicts with 'front', 'back', 'front_tol', 'back_tol'
        
    Returns:
        List of (front_expiry, back_expiry, dte_pair_config) tuples
    """
    pairs = []
    
    for dte_pair in dte_pairs:
        front_target = dte_pair["front"]
        back_target = dte_pair["back"]
        front_tol = dte_pair.get("front_tol", 5)
        back_tol = dte_pair.get("back_tol", 10)
        
        # Find front expiry
        front_expiry = chain.get_expiry_by_dte(front_target, front_tol)
        if front_expiry is None:
            continue
        
        # Find back expiry
        back_expiry = chain.get_expiry_by_dte(back_target, back_tol)
        if back_expiry is None:
            continue
        
        # Ensure front < back
        if front_expiry.dte >= back_expiry.dte:
            continue
        
        pairs.append((front_expiry, back_expiry, dte_pair))
    
    return pairs


def apply_liquidity_filters(
    contract: Contract,
    min_oi: int,
    min_volume: int,
    max_bid_ask_pct: float
) -> Tuple[bool, List[str]]:
    """
    Apply liquidity and data quality filters to a contract.
    
    Args:
        contract: Contract to check
        min_oi: Minimum open interest
        min_volume: Minimum volume
        max_bid_ask_pct: Maximum bid-ask spread as percentage of mid
        
    Returns:
        (passes, reason_codes) tuple
    """
    reasons = []
    
    # Check bid/ask exist
    if contract.bid is None or contract.ask is None:
        reasons.append("missing_quotes")
        return False, reasons
    
    # Check bid-ask spread
    mid = (contract.bid + contract.ask) / 2.0
    if mid <= 0:
        reasons.append("zero_mid_price")
        return False, reasons
        
    spread_pct = (contract.ask - contract.bid) / mid
    if spread_pct > max_bid_ask_pct:
        reasons.append(f"wide_spread_{spread_pct:.2%}")
    
    # Check OI
    if contract.open_interest is None or contract.open_interest < min_oi:
        reasons.append(f"low_oi_{contract.open_interest}")
    
    # Check volume
    if contract.volume is None or contract.volume < min_volume:
        reasons.append(f"low_volume_{contract.volume}")
    
    passes = len(reasons) == 0
    return passes, reasons


def compute_signals(
    chain: ChainSnapshot,
    user_settings: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compute all signals for a chain snapshot given user settings.
    
    Args:
        chain: ChainSnapshot from provider
        user_settings: User settings dict with thresholds and filters
        
    Returns:
        List of signal dictionaries
    """
    signals = []
    
    # Extract settings
    ff_threshold = user_settings.get("ff_threshold", 0.20)
    dte_pairs = user_settings.get("dte_pairs", [])
    vol_point = user_settings.get("vol_point", "ATM")
    min_oi = user_settings.get("min_open_interest", 100)
    min_volume = user_settings.get("min_volume", 10)
    max_bid_ask_pct = user_settings.get("max_bid_ask_pct", 0.08)
    sigma_fwd_floor = user_settings.get("sigma_fwd_floor", 0.05)
    
    # Pair expiries
    expiry_pairs = pair_expiries(chain, dte_pairs)
    
    for front_expiry, back_expiry, dte_config in expiry_pairs:
        # Select vol points
        front_iv = select_vol_point(front_expiry, chain.underlying_price, vol_point)
        back_iv = select_vol_point(back_expiry, chain.underlying_price, vol_point)
        
        if front_iv is None or back_iv is None:
            continue
        
        # Get contracts for liquidity checks
        front_contract = front_expiry.get_atm_contract(chain.underlying_price)
        back_contract = back_expiry.get_atm_contract(chain.underlying_price)
        
        if front_contract is None or back_contract is None:
            continue
        
        # Apply liquidity filters
        front_passes, front_reasons = apply_liquidity_filters(
            front_contract, min_oi, min_volume, max_bid_ask_pct
        )
        back_passes, back_reasons = apply_liquidity_filters(
            back_contract, min_oi, min_volume, max_bid_ask_pct
        )
        
        reason_codes = []
        if not front_passes:
            reason_codes.extend([f"front_{r}" for r in front_reasons])
        if not back_passes:
            reason_codes.extend([f"back_{r}" for r in back_reasons])
        
        # Calculate Forward Factor
        ff = forward_factor(front_iv, front_expiry.dte, back_iv, back_expiry.dte)
        
        if ff is None:
            reason_codes.append("invalid_ff_calculation")
            continue
        
        # Calculate sigma_fwd for floor check
        t1 = front_expiry.dte / 365.0
        t2 = back_expiry.dte / 365.0
        v1 = (front_iv ** 2) * t1
        v2 = (back_iv ** 2) * t2
        v_fwd = (v2 - v1) / (t2 - t1)
        sigma_fwd = np.sqrt(v_fwd) if v_fwd >= 0 else 0.0
        
        # Check sigma_fwd floor
        if sigma_fwd < sigma_fwd_floor:
            reason_codes.append(f"sigma_fwd_below_floor_{sigma_fwd:.4f}")
            continue
        
        # Check FF threshold
        if ff < ff_threshold:
            continue
        
        # Create signal
        signal = {
            "ticker": chain.ticker,
            "as_of_ts": chain.as_of,
            "front_expiry": front_expiry.expiry_date,
            "back_expiry": back_expiry.expiry_date,
            "front_dte": front_expiry.dte,
            "back_dte": back_expiry.dte,
            "front_iv": front_iv,
            "back_iv": back_iv,
            "sigma_fwd": sigma_fwd,
            "ff_value": ff,
            "vol_point": vol_point,
            "quality_score": 1.0 if len(reason_codes) == 0 else 0.5,
            "reason_codes": reason_codes,
            "underlying_price": chain.underlying_price,
            "provider": chain.provider
        }
        
        signals.append(signal)
    
    # Sort by FF value (highest first)
    signals.sort(key=lambda s: s["ff_value"], reverse=True)
    
    return signals
