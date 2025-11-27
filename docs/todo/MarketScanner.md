# Market-Wide Scanner ("Discovery Mode") Implementation Plan

## 1. Overview
The goal is to upgrade the Forward Factor bot from a reactive system (scanning only user-subscribed tickers) to a proactive system ("Discovery Mode"). In this mode, the bot will autonomously scan a universe of liquid optionable stocks (e.g., top 100 by volume) to identify "Forward Factor" anomalies that the user might not be aware of.

## 2. Current Architecture Analysis
- **ScanWorker (`app/workers/scan_worker.py`)**: Currently designed to process specific tickers. It fetches the chain, computes signals, and then looks up subscribers for that specific ticker.
- **Subscription Model**: Users explicitly subscribe to tickers.
- **Data Source**: Polygon.io is used for option chains (`get_chain_snapshot`).

## 3. Proposed Implementation

### 3.1. Data Source: Defining the Universe
We need a dynamic list of "liquid optionable stocks".
- **Polygon.io API**: We can use the `get_grouped_daily_aggs` endpoint to fetch daily stats for the entire stocks market.
  - **Endpoint**: `/v2/aggs/grouped/locale/us/market/stocks/{date}`
  - **Logic**: Fetch this data, sort by `volume` (or `turnover`), and take the top N (e.g., 100 or 200).
  - **Filtering**: We need to ensure these stocks have options. We can cross-reference with a "Reference Data" check or simply assume high-volume stocks (like SPY, AAPL, TSLA, NVDA) have options. Alternatively, we can use `list_tickers` with `type=CS` (Common Stock) and `active=true`, but that returns too many. The volume-based approach is best for "liquidity".

### 3.2. New Component: `DiscoveryWorker` (or `UniverseScanner`)
We should create a new worker or extend the existing `ScanWorker` to handle "Discovery" jobs.

**Workflow:**
1.  **Universe Refresh (Scheduled Job)**:
    - Runs periodically (e.g., every morning or every hour).
    - Calls Polygon `get_grouped_daily_aggs`.
    - Identifies top 100 tickers by volume.
    - Pushes these tickers to a new Redis queue: `discovery_queue`.

2.  **Scanning (Worker)**:
    - Consumes from `discovery_queue`.
    - Performs the standard `scan_ticker` logic.
    - **Crucial Change**: In `scan_ticker`, if no direct subscribers are found, we *still* proceed if the ticker is from the "Discovery" batch.

3.  **Notification Logic**:
    - We need a way to route signals to users who haven't subscribed to the ticker but have enabled "Discovery Mode".
    - **User Model Update**: Add `discovery_mode: bool` to `User` model.
    - **Signal Routing**:
        - If Signal Found:
            - Notify explicit subscribers.
            - Notify "Discovery Mode" users (potentially with a higher threshold or distinct alert format).

### 3.3. Code Changes

#### `app/providers/polygon.py`
Add a method to fetch top liquid tickers.
```python
async def get_top_liquid_tickers(self, limit: int = 100) -> List[str]:
    # Implementation using get_grouped_daily_aggs
    # Sort by volume * close (dollar volume) or just volume
    pass
```

#### `app/workers/scan_worker.py`
Modify `scan_ticker` to handle discovery logic.
```python
# Pseudo-code
async def scan_ticker(self, ticker: str, is_discovery: bool = False):
    # ... fetch chain ...
    
    subscribers = await SubscriptionService.get_ticker_subscribers(db, ticker)
    discovery_users = []
    if is_discovery:
        discovery_users = await UserService.get_discovery_users(db)
    
    all_users = set(subscribers + discovery_users)
    
    # ... compute signals for each user's settings ...
    # Note: For discovery users, we might need "Default Discovery Settings" 
    # instead of iterating through every user's custom settings to save compute.
```

#### `app/models/user.py`
Add `discovery_mode` column.

### 3.4. Testing Strategy
- **Mocking Polygon**: Essential. We cannot rely on live API calls for "top 100" in tests.
    - Mock `get_grouped_daily_aggs` to return a controlled list of tickers with fake volumes.
- **End-to-End Flow**:
    1.  Mock the "Universe Refresh" to populate `discovery_queue` with `["FAKE1", "FAKE2"]`.
    2.  Mock `get_chain_snapshot` for `FAKE1` to return a chain that triggers a signal.
    3.  Verify that a user with `discovery_mode=True` (but no subscription to `FAKE1`) receives the signal.
- **Performance**:
    - Scanning 100 tickers might take time. We need to ensure we respect Polygon's rate limits (5 calls/min for free, unlimited for paid). Assuming paid since this is a "Golden Goose" feature.
    - Ensure `compute_signals` is efficient enough.

## 4. Next Steps
1.  Implement `get_top_liquid_tickers` in `PolygonProvider`.
2.  Create a script or scheduler task to populate `discovery_queue`.
3.  Update `ScanWorker` to process `discovery_queue`.
4.  Update `User` model and `UserService`.
5.  Add tests.
