# Stability Backtesting & Minute Aggregates

## 1. Introduction
The goal of this document is to outline the implementation of "Stability Backtesting" using Minute Aggregates from Polygon.io. This feature aims to provide instant verification of signal stability by analyzing historical data immediately upon signal detection, rather than waiting for subsequent live scans.

## 2. Current Implementation Analysis
### Stability Tracker (`app/services/stability_tracker.py`)
Currently, the `StabilityTracker` class uses Redis to debounce signals.
- **Mechanism**: It tracks `consecutive_count` for a signal (identified by ticker and expiry pair).
- **Workflow**:
    1.  Signal detected in `ScanWorker`.
    2.  `check_stability` is called.
    3.  If it's the first time seeing the signal, it stores the state in Redis and returns `False` (do not alert).
    4.  It waits for the next scan cycle (controlled by `ScanWorker` loop and job queue).
    5.  If the signal persists for `required_scans` (default 2), it returns `True` (alert).
- **Limitation**: This introduces a delay equal to the scan interval * `required_scans`. If the scan interval is long, the alert is delayed significantly.

### Scan Worker (`app/workers/scan_worker.py`)
The `ScanWorker` fetches the chain snapshot, computes signals, and then calls `stability_tracker.check_stability`. It passes the `ticker`, `expiry`, and `ff_value`.

## 3. Proposed Solution: Minute Aggregates
Instead of waiting for future scans to prove stability, we can look at the *past* 60 minutes of data for the specific option contract.

### Concept
When a signal is first detected:
1.  Construct the Polygon option ticker symbol (e.g., `O:SPY241220C00500000`).
2.  Fetch the last 60 minutes of 1-minute aggregates (OHLCV) for this option contract.
3.  Analyze the data for stability.
    - **Price Stability**: Check if the price has been relatively consistent or trending smoothly, rather than erratic spikes.
    - **IV Stability**: If available in aggregates (or derived), check IV stability. *Note: Standard aggregates give Price/Volume. IV might need to be inferred or fetched separately if critical, but Price stability is a good proxy for the "Forward Factor" stability in many cases.*
4.  **Decision**:
    - **Stable History**: Treat as if `required_scans` has already been met. Alert immediately.
    - **Unstable History**: Fall back to the existing "wait and see" approach.

### Polygon API Integration
We will use the `list_aggs` method from the Polygon client.
**Endpoint**: `/v2/aggs/ticker/{optionsTicker}/range/1/minute/{from}/{to}`

```python
# Example usage
client.list_aggs(
    ticker="O:AAPL230616C00150000",
    multiplier=1,
    timespan="minute",
    from_="2023-01-01",
    to="2023-01-01",
    limit=60
)
```

## 4. Implementation Plan

### Step 1: Update `StabilityTracker`
Modify `check_stability` to accept a `PolygonProvider` instance (or use the one available in `ScanWorker`).

**New Method Signature:**
```python
async def check_stability(
    self,
    ticker: str,
    front_expiry: date,
    back_expiry: date,
    ff_value: float,
    provider: PolygonProvider,  # New argument
    option_symbol: str,         # New argument: Need the specific option symbol to query
    required_scans: int = 2,
    cooldown_minutes: int = 120,
    delta_ff_min: float = 0.02
) -> tuple[bool, dict]:
```

### Step 2: Implement `verify_historical_stability`
Add a helper method to fetch and analyze aggregates.

```python
async def _verify_historical_stability(self, provider, option_symbol) -> bool:
    # Calculate time range (last 60 mins)
    to_date = datetime.utcnow()
    from_date = to_date - timedelta(minutes=60)
    
    # Fetch aggs
    aggs = await provider.get_aggs(
        ticker=option_symbol,
        multiplier=1,
        timespan="minute",
        from_=from_date,
        to=to_date
    )
    
    if not aggs:
        return False
        
    # Analyze stability (Example logic)
    # 1. Check for sufficient data points (e.g., > 30 mins of trading)
    if len(aggs) < 30:
        return False
        
    # 2. Check price volatility (e.g., standard deviation / mean)
    prices = [a.close for a in aggs]
    # ... calculation ...
    
    return is_stable
```

### Step 3: Integrate in `check_stability`
Inside `check_stability`, when `state` is empty (first scan):
1.  Call `_verify_historical_stability`.
2.  If `True`:
    - Set `consecutive_count` = `required_scans`.
    - Return `True` (Alert).
3.  If `False`:
    - Proceed with existing logic (set count=1, return False).

### Step 4: Update `ScanWorker`
Update the call site in `app/workers/scan_worker.py` to pass the `provider` and the specific `option_symbol` (which needs to be extracted from the signal data).

## 5. Testing Strategy

### Unit Tests (`tests/unit/services/test_stability_tracker.py`)
1.  **Mock PolygonProvider**: Create a mock that returns predefined aggregates.
2.  **Test Stable History**:
    - Input: First scan, mock returns stable price history.
    - Expected: Returns `True` (Alert), Redis state shows `consecutive_count` >= `required_scans`.
3.  **Test Unstable History**:
    - Input: First scan, mock returns volatile price history.
    - Expected: Returns `False`, Redis state shows `consecutive_count` = 1.
4.  **Test API Failure**:
    - Input: Polygon API raises exception or returns empty.
    - Expected: Fallback to standard behavior (Returns `False`).

### Integration Tests
- Run the worker with a live (or recorded) Polygon response and verify the flow end-to-end.

## 6. Other Considerations
- **Option Symbol Format**: Ensure we can construct the correct Polygon option ticker (e.g., `O:{Ticker}{YYMMDD}{C/P}{Strike}`) from the signal data.
- **API Costs/Limits**: Fetching aggregates for every signal might increase API usage. Ensure it fits within the subscription limits.
- **Latency**: This adds an HTTP request to the signal processing loop. Since it's async, it shouldn't block the worker significantly, but it adds latency to the specific signal processing.
