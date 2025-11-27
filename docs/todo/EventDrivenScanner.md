# Event-Driven Scanner Implementation Plan

## 1. Current Architecture Analysis

### Current State
The current scanning mechanism relies on a polling-based architecture implemented in `app/workers/scan_worker.py`.
- **Trigger**: The worker blocks on a Redis list (`scan_queue`) waiting for jobs.
- **Job Source**: Presumably, a scheduler or another process pushes tickers into this queue at regular intervals.
- **Action**: When a job is received, it fetches the *entire* option chain snapshot via `PolygonProvider.get_chain_snapshot`.
- **Inefficiency**: This approach likely scans tickers regardless of whether the underlying price has moved significantly. Fetching full option chains is an expensive operation (both in terms of API credits/limits and data processing) if the market data hasn't changed enough to alter the signal.

### Code Reference
- `app/workers/scan_worker.py`:
  ```python
  # Lines 126-133
  while True:
      result = await redis.brpop("scan_queue", timeout=5)
      if result:
          queue_name, ticker = result
          await self.scan_ticker(ticker)
  ```
- `app/providers/polygon.py`: Uses `httpx` for REST calls. No WebSocket implementation exists yet.

## 2. Proposed Event-Driven Architecture

### The Upgrade: "Smarter, Not Harder"
Instead of blindly scanning, we will invert the control flow using Polygon.io's WebSocket stream.

1.  **WebSocket Listener**: A new service or worker (`StreamWorker`) connects to the Polygon WebSocket API.
2.  **Subscriptions**: It subscribes to `T.*` (Trades) or `Q.*` (Quotes) for all watched tickers.
3.  **State Tracking**: It maintains a local cache (or Redis cache) of the "last scanned price" for each ticker.
4.  **Event Trigger**:
    - When a trade/quote update arrives, calculate the percentage change from the `last_scanned_price`.
    - If `abs(current_price - last_scanned_price) / last_scanned_price > threshold` (e.g., 0.5%):
        - Push a scan job to the `scan_queue`.
        - Update `last_scanned_price` to the current price.
5.  **Existing Worker**: The existing `ScanWorker` continues to process jobs from `scan_queue`. This ensures minimal refactoring of the heavy lifting logic.

### Benefits
-   **Resource Efficiency**: Reduces unnecessary API calls to the heavy `Snapshot` endpoint.
-   **Timeliness**: Scans happen *immediately* when price moves, rather than waiting for the next scheduled poll.
-   **Scalability**: The system focuses resources on active tickers.

## 3. Implementation Plan

### Phase 1: Polygon WebSocket Client Integration
We need to extend the `PolygonProvider` or create a new `PolygonStream` class using the official `polygon-io-client` or `websockets` library.

**Docs Lookup (@mcp:context7)**:
According to the Polygon docs, we can use `polygon.WebSocketClient`.
```python
from polygon import WebSocketClient

async def handle_msg(msgs: List[WebSocketMessage]):
    for m in msgs:
        # Check price change logic here
        pass

ws = WebSocketClient(api_key=..., subscriptions=["T.AAPL", "T.MSFT"])
await ws.run(handle_msg)
```

### Phase 2: The Stream Worker (`app/workers/stream_worker.py`)
Create a new worker that:
1.  Loads all active tickers from the database (`SubscriptionService`).
2.  Connects to Polygon WebSocket.
3.  Implements the "Significant Move" logic.
4.  Enqueues jobs to Redis.

**Significant Move Logic**:
```python
threshold = 0.005 # 0.5%

if abs(new_price - last_price) / last_price > threshold:
    redis.lpush("scan_queue", ticker)
    last_price = new_price
```

### Phase 3: Integration & State Management
-   **Redis State**: Store `last_scanned_price:{ticker}` in Redis to persist state across worker restarts.
-   **Dynamic Subscriptions**: The worker needs to listen for new subscriptions (via Redis Pub/Sub or periodic DB checks) to update the WebSocket subscription list without restarting.

## 4. Testing Strategy

We need to ensure the event logic is robust.

### Unit Tests
-   **Mocking WebSocket**: Use `unittest.mock` or `pytest-asyncio` to mock the `WebSocketClient`. We don't want to connect to real sockets during tests.
-   **Test Logic**:
    -   Feed a sequence of price updates: `100` -> `100.1` (No trigger) -> `100.6` (Trigger).
    -   Verify that `redis.lpush` is called exactly once for the significant move.
-   **Redis Mocking**: Continue using `fakeredis` (as seen in `tests/conftest.py`) to simulate queue operations.

### Integration Tests
-   Spin up the `StreamWorker` with a mock Polygon server (or a replay mechanism) and a real Redis instance (or `fakeredis`).
-   Verify the full pipeline: `Price Update` -> `StreamWorker` -> `Redis Queue` -> `ScanWorker` -> `Signal`.

## 5. New Dependencies
-   `polygon-api-client`: We might need to ensure the standard library is installed and up to date to support WebSockets.
-   `websockets`: Usually a dependency of the polygon client.

## 6. Migration Steps
1.  Install/Update dependencies.
2.  Implement `app/providers/stream.py` (WebSocket wrapper).
3.  Implement `app/workers/stream_worker.py`.
4.  Add unit tests in `tests/unit/workers/test_stream_worker.py`.
5.  Update `docker-compose.yml` (if applicable) to run the new worker.
6.  Disable the old "blind loop" scheduler if it exists, or keep it as a fallback/heartbeat (e.g., scan at least once an hour even if no movement).
