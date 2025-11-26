# Test Coverage Plan: Backend Unit Tests

## Executive Summary

This document provides a comprehensive list of all API endpoints, functions, and components requiring unit test coverage in the Forward Factor trading bot. Special emphasis is placed on the **Signal Engine** which implements the core mathematical calculations defined in strategy.md.

---

## 1. Signal Engine (Critical - Top Priority)

The Signal Engine is the core mathematical component that implements the Forward Factor calculation strategy. All functions must be tested against the requirements in strategy.md.

### 1.1 Core Mathematical Functions

#### `forward_factor()` - [signal_engine.py](file:///Users/a/Repositories/forward-factor/app/services/signal_engine.py#L9-L58)

**Purpose**: Calculate Forward Factor (FF) value based on front/back IV and DTE

**Critical Test Cases**:
- ✅ Valid calculation with typical values (front_iv=0.25, front_dte=30, back_iv=0.20, back_dte=60)
- ✅ Edge case: t1 <= 0 (invalid DTE) → returns None
- ✅ Edge case: t2 <= 0 (invalid DTE) → returns None
- ✅ Edge case: t1 >= t2 (front >= back) → returns None
- ✅ Negative forward variance (v_fwd < 0) → returns None
- ✅ Zero or negative sigma_fwd → returns None
- ✅ Verify formula correctness: V1 = σ1² * T1, V2 = σ2² * T2, V_fwd = (V2-V1)/(T2-T1), FF = (σ1 - σ_fwd) / σ_fwd
- ✅ Boundary: very small forward variance (near zero)
- ✅ Boundary: very large FF values (>1.0)
- ✅ Units test: verify DTE/365.0 conversion is correct

**Strategy.md Requirements**:
- Must reject negative forward variance
- Must handle division by zero in sigma_fwd
- Must validate t1 < t2 constraint

---

#### `select_vol_point()` - [signal_engine.py](file:///Users/a/Repositories/forward-factor/app/services/signal_engine.py#L61-L96)

**Purpose**: Select IV from expiry based on method (ATM, 35d_put, etc.)

**Test Cases**:
- ✅ ATM call selection with valid underlying price
- ✅ ATM put selection with valid underlying price
- ✅ Delta-based selection: "35d_put" → 0.35 delta put
- ✅ Delta-based selection: "35d_call" → 0.35 delta call
- ✅ Invalid method → returns None
- ✅ No contracts available at strike → returns None
- ✅ Contract exists but no IV → returns None
- ✅ Parsing: "25d_put", "40d_call" etc.

**Strategy.md Requirements**:
- Must use consistent vol point across front and back expiries
- Do not mix ATM with delta strikes

---

#### `pair_expiries()` - [signal_engine.py](file:///Users/a/Repositories/forward-factor/app/services/signal_engine.py#L99-L137)

**Purpose**: Pair front and back expiries based on DTE target windows

**Test Cases**:
- ✅ Valid pairing: front=30±5, back=60±10
- ✅ Multiple DTE pair configs
- ✅ No matching front expiry → no pair returned
- ✅ No matching back expiry → no pair returned
- ✅ Front DTE >= back DTE → rejected
- ✅ Tolerance window respected (front_tol, back_tol)
- ✅ Edge case: exact DTE match
- ✅ Edge case: DTE at tolerance boundary

**Strategy.md Requirements**:
- Keep to fixed windows (30 vs 60, 30 vs 90, etc.)
- Define tolerance bands

---

#### `apply_liquidity_filters()` - [signal_engine.py](file:///Users/a/Repositories/forward-factor/app/services/signal_engine.py#L140-L181)

**Purpose**: Filter contracts based on liquidity and data quality

**Test Cases**:
- ✅ Missing bid or ask → fails with "missing_quotes"
- ✅ Bid-ask spread exceeds max_bid_ask_pct → fails with reason code
- ✅ Open interest below threshold → fails with "low_oi"
- ✅ Volume below threshold → fails with "low_volume"
- ✅ All checks pass → returns (True, [])
- ✅ Multiple failures → returns all reason codes
- ✅ Zero mid price handling
- ✅ Spread percentage calculation accuracy

**Strategy.md Requirements**:
- Tight bid-ask spread requirement
- Sufficient volume and open interest
- Use mid quotes for IV

---

#### `compute_signals()` - [signal_engine.py](file:///Users/a/Repositories/forward-factor/app/services/signal_engine.py#L184-L289)

**Purpose**: Main orchestrator - compute all signals for a chain snapshot

**Test Cases**:
- ✅ End-to-end: valid chain with signals above threshold
- ✅ No expiry pairs match → empty signal list
- ✅ FF below threshold → signal excluded
- ✅ sigma_fwd below floor → signal excluded with reason code
- ✅ Liquidity filters fail → signal marked with low quality_score
- ✅ Multiple signals → sorted by FF value (highest first)
- ✅ Settings extraction (ff_threshold, dte_pairs, vol_point, etc.)
- ✅ All signal fields populated correctly
- ✅ Invalid FF calculation → signal skipped
- ✅ Quality score: 1.0 when no reason codes, 0.5 when filters fail

**Strategy.md Requirements**:
- Filter out earnings events (not yet implemented - note in test)
- Require stability across consecutive scans (handled by StabilityTracker)
- Sigma_fwd floor check (default 0.05)

---

### 1.2 Helper Functions

#### Provider Models - [providers/models.py](file:///Users/a/Repositories/forward-factor/app/providers/models.py)

**Test `ChainSnapshot` methods**:
- ✅ `get_expiry_by_dte()` with tolerance
- ✅ Edge case: no expiries in range
- ✅ Edge case: multiple expiries in range (pick closest)

**Test `Expiry` methods**:
- ✅ `get_atm_contract()` - find closest strike to underlying price
- ✅ `get_delta_contract()` - find contract by target delta
- ✅ Edge cases: no contracts available

**Test `Contract` model**:
- ✅ Proper field population
- ✅ Bid/ask validation

---

## 2. Stability Tracker (High Priority)

### `StabilityTracker` - [stability_tracker.py](file:///Users/a/Repositories/forward-factor/app/services/stability_tracker.py)

**Purpose**: Track signal stability across consecutive scans using Redis

**Critical Test Cases**:

#### `check_stability()`
- ✅ First scan → should_alert=False, reason="first_scan"
- ✅ Consecutive scans < required_scans → should_alert=False
- ✅ Consecutive scans >= required_scans → should_alert=True
- ✅ Cooldown period active → should_alert=False with reason
- ✅ FF delta below threshold → should_alert=False
- ✅ FF increase above delta_ff_min after cooldown → should_alert=True
- ✅ Redis key uses expiry dates (not DTE) to prevent daily resets
- ✅ TTL expiration (24 hour) behavior
- ✅ State persistence across calls

#### `reset()`
- ✅ Clears stability tracking for ticker/expiry pair

**Strategy.md Requirements**:
- Require dislocation to persist (2+ consecutive scans)
- Kill one-tick spikes
- Use expiry dates in keys (NOT DTE which changes daily)

**Testing Note**: Requires Redis mock or test container

---

## 3. Signal Service (High Priority)

### `SignalService` - [signal_service.py](file:///Users/a/Repositories/forward-factor/app/services/signal_service.py)

#### `generate_dedupe_key()` - Line 13
- ✅ Same ticker/expiries/date → same hash
- ✅ Different date → different hash
- ✅ Different ticker → different hash
- ✅ Hash collision resistance (basic)

#### `create_signal()` - Line 28
- ✅ New signal → creates and returns Signal object
- ✅ Duplicate signal (same dedupe_key) → returns None
- ✅ All signal fields persisted correctly
- ✅ Database transaction committed

#### `get_recent_signals()` - Line 80
- ✅ Retrieve signals ordered by as_of_ts desc
- ✅ Filter by ticker
- ✅ Limit parameter respected
- ✅ Returns empty list when no signals

#### `record_decision()` - Line 95
- ✅ Create decision record with metadata
- ✅ All decision types: "placed", "ignored", "expired", "error"
- ✅ Optional metadata stored correctly
- ✅ Decision timestamp recorded

#### `get_user_decisions()` - Line 129
- ✅ Join with Signal table
- ✅ Filter by user_id
- ✅ Order by decision_ts desc
- ✅ Return decision + signal details
- ✅ Limit parameter

---

## 4. API Endpoints (Medium Priority)

All endpoints require authentication testing and error cases.

### 4.1 Authentication Routes - [api/routes/auth.py](file:///Users/a/Repositories/forward-factor/app/api/routes/auth.py)

#### `POST /api/auth/register` - Line 49
- ✅ Valid registration → 201 + access token
- ✅ Registration disabled → 403
- ✅ Weak password (< 8 chars) → 400
- ✅ Duplicate email → error from AuthService
- ✅ Returns user data and token

#### `POST /api/auth/login` - Line 101
- ✅ Valid credentials → 200 + access token
- ✅ Invalid credentials → 401
- ✅ Returns user data including telegram_username

#### `POST /api/auth/link-telegram` - Line 138
- ✅ Requires authentication
- ✅ Links telegram username to account
- ✅ Returns updated user data
- ✅ Error if user not found

#### `POST /api/auth/unlink-telegram` - Line 165
- ✅ Requires authentication
- ✅ Unlinks telegram account
- ✅ Returns updated user data

#### `GET /api/auth/me` - Line 190
- ✅ Requires authentication
- ✅ Returns current user info
- ✅ No authentication → 401

---

### 4.2 Signals Routes - [api/routes/signals.py](file:///Users/a/Repositories/forward-factor/app/api/routes/signals.py)

#### `GET /api/signals` - Line 62
- ✅ Requires authentication
- ✅ Returns signals for user's watchlist
- ✅ Filter by ticker parameter
- ✅ Limit parameter
- ✅ Empty watchlist → empty array
- ✅ Only subscribed tickers returned
- ✅ Ordered by as_of_ts desc

#### `GET /api/signals/history` - Line 120
- ✅ Requires authentication
- ✅ Returns user's decision history with signals
- ✅ Join SignalUserDecision + Signal
- ✅ Includes PnL and exit_price
- ✅ Ordered by decision_ts desc
- ✅ Limit parameter

#### `POST /api/signals/{signal_id}/decision` - Line 171
- ✅ Requires authentication
- ✅ Valid decision types: "placed", "ignored"
- ✅ Invalid decision type → 400
- ✅ Signal not found → 404
- ✅ Create new decision → 201
- ✅ Update existing decision
- ✅ Optional fields: entry_price, exit_price, pnl, notes
- ✅ Returns decision data

---

### 4.3 Watchlist Routes - [api/routes/watchlist.py](file:///Users/a/Repositories/forward-factor/app/api/routes/watchlist.py)

#### `GET /api/watchlist` - Line 27
- ✅ Requires authentication
- ✅ Returns user's subscriptions
- ✅ Includes ticker, added_at, active
- ✅ Empty watchlist → []

#### `POST /api/watchlist` - Line 49
- ✅ Requires authentication
- ✅ Add ticker (normalized to uppercase)
- ✅ Empty ticker → 400
- ✅ Duplicate ticker → reactivate if inactive
- ✅ Returns subscription data + message

#### `DELETE /api/watchlist/{ticker}` - Line 84
- ✅ Requires authentication
- ✅ Remove ticker (case-insensitive)
- ✅ Returns success message
- ✅ Non-existent ticker → still returns success

---

### 4.4 Settings Routes - [api/routes/settings.py](file:///Users/a/Repositories/forward-factor/app/api/routes/settings.py)

#### `GET /api/settings` - Line 64
- ✅ Requires authentication
- ✅ Returns all user settings
- ✅ DTE pairs as array of objects
- ✅ Quiet hours structure

#### `PUT /api/settings` - Line 93
- ✅ Requires authentication
- ✅ Partial updates (only provided fields)
- ✅ DTE pair validation: front < back
- ✅ DTE pair validation: non-negative values
- ✅ Invalid DTE pairs → 400
- ✅ All setting fields updateable
- ✅ Returns updated settings

---

## 5. Service Layer (Medium Priority)

### 5.1 AuthService - [auth_service.py](file:///Users/a/Repositories/forward-factor/app/services/auth_service.py)

#### `register_user()` - Line 17
- ✅ Create new user with hashed password
- ✅ Create default UserSettings
- ✅ Duplicate email → HTTPException 409
- ✅ Password hashing verified
- ✅ Status = "active"

#### `authenticate_user()` - Line 78
- ✅ Valid credentials → return User
- ✅ Invalid email → return None
- ✅ Invalid password → return None
- ✅ Password verification

#### `link_telegram_username()` - Line 105
- ✅ Find bot user by telegram_username
- ✅ Merge bot user subscriptions to web user
- ✅ Delete bot user after merge
- ✅ Update web user with telegram data
- ✅ User not found → HTTPException 404
- ✅ No matching bot user → just update username

#### `unlink_telegram_username()` - Line 192
- ✅ Clear telegram_chat_id and telegram_username
- ✅ User not found → HTTPException 404
- ✅ Returns updated user

#### `get_user_by_email()` - Line 225
- ✅ Find user by email
- ✅ Not found → return None

#### `get_user_by_telegram_chat_id()` - Line 240
- ✅ Find user by telegram_chat_id
- ✅ Not found → return None

---

### 5.2 UserService - [user_service.py](file:///Users/a/Repositories/forward-factor/app/services/user_service.py)

#### `get_or_create_user()` - Line 12
- ✅ Existing user found → return user
- ✅ Update telegram_username if different
- ✅ New user → create with default settings
- ✅ Default settings use app config values
- ✅ Flush and commit transaction

#### `get_user_by_chat_id()` - Line 67
- ✅ Find by telegram_chat_id
- ✅ Not found → None

#### `get_user_settings()` - Line 75
- ✅ Find settings by user_id
- ✅ Not found → None

#### `update_user_settings()` - Line 83
- ✅ Update provided kwargs only
- ✅ Hasattr check for valid fields
- ✅ Commit and refresh
- ✅ Return updated settings

---

### 5.3 SubscriptionService - [subscription_service.py](file:///Users/a/Repositories/forward-factor/app/services/subscription_service.py)

#### `add_subscription()` - Line 11
- ✅ Ticker uppercased
- ✅ New subscription created
- ✅ Existing inactive → reactivate
- ✅ Existing active → return existing
- ✅ Commit and refresh

#### `remove_subscription()` - Line 58
- ✅ Delete subscription
- ✅ Ticker uppercased
- ✅ Returns true if deleted
- ✅ Not found → returns false

#### `get_user_subscriptions()` - Line 87
- ✅ Filter by user_id
- ✅ active_only parameter
- ✅ Returns Subscription objects
- ✅ Empty list when no subscriptions

#### `get_ticker_subscribers()` - Line 112
- ✅ Find all users subscribed to ticker
- ✅ Ticker uppercased
- ✅ Only active subscriptions
- ✅ Returns list of user_ids
- ✅ Empty list when no subscribers

---

## 6. Workers (Low-Medium Priority)

### 6.1 ScanWorker - [scan_worker.py](file:///Users/a/Repositories/forward-factor/app/workers/scan_worker.py)

#### `scan_ticker()` - Line 29
**Integration test** (requires Polygon mock + DB + Redis):
- ✅ Fetch chain from provider
- ✅ Cache snapshot in Redis
- ✅ Get subscribers for ticker
- ✅ No subscribers → skip
- ✅ For each subscriber: compute signals with user settings
- ✅ Check stability for each signal
- ✅ Stable signal → persist and queue notification
- ✅ Unstable signal → log and skip
- ✅ Duplicate signal → skip notification
- ✅ Update last scan time
- ✅ Error handling and logging

#### `run()` - Line 120
**Integration test**:
- ✅ Poll Redis scan_queue
- ✅ Process ticker on queue
- ✅ Timeout handling
- ✅ Error recovery (sleep and retry)
- ✅ Cleanup on exit

---

## 7. Provider Layer (Low Priority)

### 7.1 PolygonProvider - [polygon.py](file:///Users/a/Repositories/forward-factor/app/providers/polygon.py)

#### `get_chain_snapshot()` - Line 19
**Mock HTTP responses**:
- ✅ Success → ChainSnapshot with expiries
- ✅ API error (non-OK status) → ProviderError
- ✅ HTTP error → ProviderError
- ✅ Underlying price fetched
- ✅ Contracts parsed and grouped

#### `_get_underlying_price()` - Line 59
- ✅ Success → return close price
- ✅ No results → ProviderError

#### `_parse_contracts()` - Line 73
- ✅ Parse Polygon JSON into Contract objects
- ✅ Handle missing fields gracefully
- ✅ Expiry date parsing
- ✅ Call vs put type
- ✅ Greeks and quote data

#### `_group_by_expiry()` - Line 111
- ✅ Group contracts by expiry_date
- ✅ Calculate DTE for each expiry
- ✅ Sort by expiry date
- ✅ Return Expiry objects

---

## 8. Bot Handlers (Low Priority)

### 8.1 Start Handler - [bot/handlers/start.py](file:///Users/a/Repositories/forward-factor/app/bot/handlers/start.py)
- ✅ `/start` command → welcome message
- ✅ User registration/retrieval
- ✅ Keyboard markup display

### 8.2 Watchlist Handler - [bot/handlers/watchlist.py](file:///Users/a/Repositories/forward-factor/app/bot/handlers/watchlist.py)
- ✅ Add ticker via bot
- ✅ Remove ticker via bot
- ✅ View watchlist

### 8.3 Settings Handler - [bot/handlers/settings.py](file:///Users/a/Repositories/forward-factor/app/bot/handlers/settings.py)
- ✅ View settings
- ✅ Update settings

### 8.4 History Handler - [bot/handlers/history.py](file:///Users/a/Repositories/forward-factor/app/bot/handlers/history.py)
- ✅ View decision history

### 8.5 Callbacks Handler - [bot/handlers/callbacks.py](file:///Users/a/Repositories/forward-factor/app/bot/handlers/callbacks.py)
- ✅ Signal decision callbacks
- ✅ "Place" action
- ✅ "Ignore" action

---

## 9. Utilities (Low Priority)

### 9.1 Time Utils - [utils/time.py](file:///Users/a/Repositories/forward-factor/app/utils/time.py)
- ✅ `calculate_dte()` - days between today and expiry
- ✅ Edge cases: past dates, today, future dates

### 9.2 Formatting Utils - [utils/formatting.py](file:///Users/a/Repositories/forward-factor/app/utils/formatting.py)
- ✅ Message formatting functions
- ✅ Markdown escaping

---

## 10. Models (Low Priority)

### Data Integrity Tests

For each model, test:
- ✅ Creation with valid data
- ✅ Required fields validation
- ✅ Relationships (foreign keys)
- ✅ Defaults applied
- ✅ Constraints (unique, not null, etc.)

**Models to test**:
- `User` - [models/user.py](file:///Users/a/Repositories/forward-factor/app/models/user.py)
- `UserSettings` - [models/user.py](file:///Users/a/Repositories/forward-factor/app/models/user.py)
- `Signal` - [models/signal.py](file:///Users/a/Repositories/forward-factor/app/models/signal.py)
- `SignalUserDecision` - [models/decision.py](file:///Users/a/Repositories/forward-factor/app/models/decision.py)
- `Subscription` - [models/subscription.py](file:///Users/a/Repositories/forward-factor/app/models/subscription.py)
- `Ticker` - [models/ticker.py](file:///Users/a/Repositories/forward-factor/app/models/ticker.py)

---

## Priority Matrix

| Priority Level | Component | Reason |
|---------------|-----------|---------|
| **Critical** | Signal Engine (`forward_factor`, `compute_signals`) | Core math - errors affect all trading decisions |
| **Critical** | Stability Tracker | Prevents false signals and spam |
| **High** | Signal Service | Persistence and deduplication logic |
| **High** | API Endpoints - Signals | User-facing signal delivery |
| **Medium** | Auth Service | Account security and linking |
| **Medium** | Subscription Service | Watchlist management |
| **Medium** | API Endpoints - Auth/Watchlist/Settings | User features |
| **Low-Medium** | Scan Worker | Integration layer (harder to unit test) |
| **Low** | Provider Layer | External dependency (mock-heavy) |
| **Low** | Bot Handlers | UI layer |
| **Low** | Models | ORM-generated, less risk |

---

## Testing Strategy Recommendations

### Unit Tests
Use `pytest` with the following fixtures:
- **Database**: In-memory SQLite or pytest-postgresql
- **Redis**: `fakeredis` library for pure Python mock
- **HTTP**: `httpx-mock` or `responses` library
- **Telegram**: Mock `Update` and `Context` objects

### Test File Structure
```
tests/
├── unit/
│   ├── services/
│   │   ├── test_signal_engine.py          # PRIORITY 1
│   │   ├── test_signal_service.py
│   │   ├── test_stability_tracker.py      # PRIORITY 1
│   │   ├── test_auth_service.py
│   │   ├── test_user_service.py
│   │   └── test_subscription_service.py
│   ├── api/
│   │   ├── test_auth_routes.py
│   │   ├── test_signals_routes.py
│   │   ├── test_watchlist_routes.py
│   │   └── test_settings_routes.py
│   ├── providers/
│   │   └── test_polygon_provider.py
│   ├── workers/
│   │   └── test_scan_worker.py
│   ├── bot/
│   │   └── test_handlers.py
│   └── models/
│       └── test_models.py
└── integration/
    └── test_scan_to_notification_flow.py
```

### Key Testing Dependencies
```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
fakeredis==2.20.1
httpx-mock==0.10.1
pytest-postgresql==5.0.0
factory-boy==3.3.0  # For test fixtures
```

---

## Compliance with strategy.md

### Signal Engine Validation Checklist

From strategy.md, the following critical requirements MUST be tested:
- [x] **Units**: Vols in decimals (0.25 not 25%), DTE in days, convert by 365.0
- [x] **Negative forward variance**: Must return None
- [x] **Vol consistency**: Same vol point (ATM/delta) for front and back
- [x] **Liquidity filters**: Bid-ask spread, volume, OI thresholds
- [x] **Stability filter**: Consecutive scans (handled by StabilityTracker)
- [x] **Sigma forward floor**: Minimum threshold (default 0.05)
- [x] **Pair selection**: DTE tolerance windows
- [x] **Output fields**: All required fields in signal dict

**Not yet implemented** (note in tests):
- [ ] Earnings event filtering
- [ ] Early exercise / dividend awareness
- [ ] Regime filtering (market vol index)

---

## Next Steps

1. **Create test files** for Priority 1 components (Signal Engine, Stability Tracker)
2. **Set up test infrastructure** (pytest, fixtures, mocks)
3. **Implement critical tests** for mathematical correctness
4. **Add API endpoint tests** with authentication
5. **Integration tests** for scan worker flow
6. **Code coverage reporting** (target: 80%+ for critical components)
