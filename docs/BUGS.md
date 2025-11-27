# Backend Bugs, Issues, and Recommendations

This document catalogs potential bugs, logic errors, security vulnerabilities, and areas for improvement identified in the backend codebase.

---

## ✅ Fixed Issues (Updated: Bug Fix Sprint)

The following issues have been addressed:

### Critical Issues
- **1.1 Double Commit in Database Session Handler** - ✅ Fixed in `app/core/database.py` - Removed auto-commit from `get_db()`
- **1.3 Deprecated `datetime.utcnow()` Usage** - ✅ Fixed across all app files - Updated to `datetime.now(timezone.utc)`

### Security Vulnerabilities
- **2.1 JWT Secret Not Validated on Startup** - ✅ Fixed in `app/core/config.py` - Added 32-char minimum validation
- **2.2 No Rate Limiting on Auth Endpoints** - ✅ Fixed - Added slowapi rate limiting to login/register
- **2.3 CORS Wildcard Fallback in Error Handler** - ✅ Fixed in `app/api/main.py` - Only allows configured origins

### Race Conditions & Concurrency Issues
- **3.1 Race Condition in Stability Tracker** - ✅ Fixed in `app/services/stability_tracker.py` - Added Redis locking
- **3.2 Race Condition in Signal Creation** - ✅ Fixed in `app/services/signal_service.py` - Using INSERT OR IGNORE
- **3.3 Double Initialization Risk in Redis Pool** - ✅ Fixed in `app/core/redis.py` - Added asyncio.Lock

### Error Handling Gaps
- **5.1 No Global Error Handler for Telegram Bot** - ✅ Fixed in `app/bot/main.py` - Added error_handler
- **5.4 No Retry Logic for Polygon API Calls** - ✅ Fixed in `app/providers/polygon.py` - Added tenacity retry

### Data Validation Issues
- **6.1 No Ticker Format Validation** - ✅ Fixed in `app/services/ticker_service.py` and `app/api/routes/watchlist.py`
- **6.3 No Timezone Validation** - ✅ Fixed in `app/models/user.py` - Added timezone validation
- **6.4 Missing Numeric Bounds Validation** - ✅ Fixed in `app/models/user.py` - Added validators for settings

### Logic Errors
- **7.3 Timezone-Naive Reminder Scheduling** - ✅ Fixed in `app/services/reminder_service.py` - Now timezone-aware

### Code Quality & Maintainability
- **9.4 MD5 Hash for Dedupe Key** - ✅ Fixed in `app/services/signal_service.py` - Upgraded to SHA256

### Configuration Issues
- **10.2 Log Level Not Validated** - ✅ Fixed in `app/core/config.py` - Added field_validator

---

## Remaining Issues (Not Yet Fixed)

The issues below are still pending:

- **1.2 Missing Signal-User Association in Notifications** - Requires architectural decision
- **5.2 Silent Failures in Notification Router** - Low priority
- **5.3 Missing Database Error Handling in Signal Engine** - Low priority  
- **7.1 DTE Calculation Issue** - Requires design decision on reference time
- **7.2 Missing Back DTE > Front DTE Constraint** - Needs database migration
- **8.1 N+1 Query Potential in Watchlist** - Performance optimization
- **9.1 Magic Strings for Decision Types** - Code quality improvement
- **9.2 Duplicate Tier Calculation Logic** - Code quality improvement
- **9.3 Hardcoded Market Hours** - Configuration improvement

---

## Table of Contents

1. [Critical Issues](#1-critical-issues)
2. [Security Vulnerabilities](#2-security-vulnerabilities)
3. [Race Conditions & Concurrency Issues](#3-race-conditions--concurrency-issues)
4. [Database & Session Management Issues](#4-database--session-management-issues)
5. [Error Handling Gaps](#5-error-handling-gaps)
6. [Data Validation Issues](#6-data-validation-issues)
7. [Logic Errors](#7-logic-errors)
8. [Performance Issues](#8-performance-issues)
9. [Code Quality & Maintainability](#9-code-quality--maintainability)
10. [Configuration Issues](#10-configuration-issues)

---

## 1. Critical Issues

### 1.1 Double Commit in Database Session Handler
**Location:** `app/core/database.py:49-63`

**Issue:** The `get_db()` dependency yields the session and then commits on success. However, many services (e.g., `AuthService.register_user()`, `SignalService.create_signal()`) also call `await db.commit()` explicitly, leading to double commits.

**Code:**
```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Auto-commit here
        except Exception as e:
            await session.rollback()
            raise
```

**Impact:** While SQLAlchemy handles this gracefully, it can cause:
- Unexpected behavior if an exception occurs between the service commit and the dependency commit
- Confusion about transaction boundaries
- Difficulty debugging transaction-related issues

**Recommendation:** Choose one commit strategy:
- Either remove the auto-commit from `get_db()` and let services manage commits explicitly
- Or remove commits from services and rely on the dependency's auto-commit

---

### 1.2 Missing Signal-User Association in Notifications
**Location:** `app/workers/notification_router.py:89-97`

**Issue:** Notifications are sent to all subscribers of a ticker, but signals are computed per-user based on their individual settings. A user might receive a signal notification that doesn't match their configured thresholds.

**Code:**
```python
# Get all subscribers for this ticker
subscriber_ids = await SubscriptionService.get_ticker_subscribers(db, signal.ticker)

# Send to each subscriber
for user_id in subscriber_ids:
    # ... sends to ALL subscribers
```

**Impact:** Users receive signals that may not have been generated with their specific settings (e.g., different FF threshold, min OI).

**Recommendation:** Store the `user_id` that triggered the signal in the Signal model, or implement a per-user signal filtering step before notification.

---

### 1.3 Deprecated `datetime.utcnow()` Usage
**Location:** Multiple files (auth.py, signal.py, decision.py, reminder_worker.py, etc.)

**Issue:** `datetime.utcnow()` is deprecated in Python 3.12+. Should use `datetime.now(datetime.UTC)` instead.

**Files affected:**
- `app/core/auth.py:73, 75`
- `app/services/stability_tracker.py:59, 82, 109`
- `app/services/reminder_service.py:53, 75`
- `app/workers/reminder_worker.py:124`
- `app/utils/formatting.py:51`

**Recommendation:** Replace all instances with `datetime.now(datetime.UTC)` or `datetime.now(timezone.utc)`.

---

## 2. Security Vulnerabilities

### 2.1 JWT Secret Not Validated on Startup
**Location:** `app/core/config.py`

**Issue:** The `jwt_secret` is a required field but there's no validation that it's sufficiently strong. A weak or default secret compromises authentication.

**Recommendation:** Add validation in the config:
```python
@model_validator(mode='after')
def validate_config(self) -> 'Settings':
    if len(self.jwt_secret) < 32:
        raise ValueError("JWT secret must be at least 32 characters")
    return self
```

---

### 2.2 Invite Code Comparison Vulnerable to Timing Attacks
**Location:** `app/bot/handlers/start.py:27-32`

**Issue:** Direct string comparison of invite codes is vulnerable to timing attacks.

**Code:**
```python
if not context.args or context.args[0] != settings.invite_code:
```

**Recommendation:** Use `hmac.compare_digest()` for constant-time comparison:
```python
import hmac
if not context.args or not hmac.compare_digest(context.args[0], settings.invite_code):
```

---

### 2.3 CORS Wildcard Fallback in Exception Handler
**Location:** `app/api/main.py:84-94`

**Issue:** The global exception handler falls back to `*` for CORS origin if the origin header is missing, potentially allowing cross-origin requests from any domain.

**Code:**
```python
headers={
    "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
    "Access-Control-Allow-Credentials": "true",
}
```

**Impact:** When combined with `allow_credentials: true`, this is a security misconfiguration.

**Recommendation:** Only allow configured origins, not wildcard:
```python
origin = request.headers.get("origin", "")
if origin in settings.cors_origins_list:
    headers["Access-Control-Allow-Origin"] = origin
```

---

### 2.4 No Rate Limiting on Authentication Endpoints
**Location:** `app/api/routes/auth.py`

**Issue:** Login and registration endpoints have no rate limiting, making them vulnerable to brute force attacks.

**Recommendation:** Implement rate limiting using:
- FastAPI middleware with Redis-backed counters
- Libraries like `slowapi` or `fastapi-limiter`

---

### 2.5 API Key Logged in Debug Mode
**Location:** `app/providers/polygon.py`

**Issue:** In debug mode with `echo=True`, SQL queries might inadvertently log sensitive data. The API key is also passed in query params which could be logged.

**Recommendation:** Mask API keys in logs and use headers instead of query parameters for API authentication where possible.

---

## 3. Race Conditions & Concurrency Issues

### 3.1 Stability Tracker Redis Race Condition
**Location:** `app/services/stability_tracker.py:53-111`

**Issue:** The `check_stability()` method reads and then writes to Redis without atomicity. Multiple concurrent calls for the same ticker/expiry could cause incorrect consecutive counts.

**Code:**
```python
state = await redis.hgetall(key)  # READ
# ... process ...
await redis.hset(key, mapping={...})  # WRITE (not atomic with read)
```

**Impact:** Concurrent scans might both increment the count, or one might overwrite the other's state.

**Recommendation:** Use Redis transactions (MULTI/EXEC) or Lua scripts for atomic read-modify-write operations.

---

### 3.2 Telegram Account Linking Race Condition
**Location:** `app/services/auth_service.py:99-181`

**Issue:** The `link_telegram_username()` method checks for existing bot users and merges accounts without database-level locking. Two concurrent requests could cause data inconsistency.

**Recommendation:** Use database-level locking (`SELECT ... FOR UPDATE`) or implement optimistic locking with version columns.

---

### 3.3 Global Redis Connection Not Thread-Safe
**Location:** `app/core/redis.py`

**Issue:** The global `_redis_pool` variable is checked and assigned without any locking. In concurrent environments, this could cause multiple pools to be created.

**Code:**
```python
async def get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:  # Check
        _redis_pool = redis.from_url(...)  # Assign (not atomic)
    return _redis_pool
```

**Recommendation:** Use `asyncio.Lock()` for thread-safe initialization:
```python
_redis_lock = asyncio.Lock()

async def get_redis() -> redis.Redis:
    global _redis_pool
    async with _redis_lock:
        if _redis_pool is None:
            _redis_pool = redis.from_url(...)
    return _redis_pool
```

---

### 3.4 Signal Deduplication Race Condition
**Location:** `app/services/signal_service.py:29-51`

**Issue:** The `create_signal()` method checks for duplicates then creates, but this is not atomic. Concurrent calls could both pass the check and create duplicate signals.

**Code:**
```python
result = await db.execute(select(Signal).where(Signal.dedupe_key == dedupe_key))
existing = result.scalar_one_or_none()
if existing:
    return None
# ... create signal (not atomic)
```

**Recommendation:** Add a database-level unique constraint on `dedupe_key` (already present) and handle `IntegrityError`:
```python
try:
    db.add(signal)
    await db.flush()
except IntegrityError:
    return None  # Duplicate
```

---

## 4. Database & Session Management Issues

### 4.1 Missing Explicit Rollback on Exceptions
**Location:** Multiple services

**Issue:** While `get_db()` handles rollback, services that manually commit (like `AuthService.register_user()`) catch exceptions but the rollback might occur after partial commits.

**Code in `auth_service.py:61-69`:**
```python
await db.commit()  # If this succeeds but refresh fails...
await db.refresh(user)  # Exception here won't rollback the commit
```

**Recommendation:** Ensure all operations are within a single transaction boundary.

---

### 4.2 Session Not Closed After Error in `get_db()`
**Location:** `app/core/database.py:49-63`

**Issue:** The `finally` block closes the session even after `AsyncSessionLocal()` context manager should handle it. This is redundant but could mask issues.

**Code:**
```python
async with AsyncSessionLocal() as session:  # Already a context manager
    try:
        yield session
        await session.commit()
    except:
        await session.rollback()
    finally:
        await session.close()  # Redundant - context manager handles this
```

**Recommendation:** Remove the explicit `close()` call as the context manager handles it.

---

### 4.3 Missing Index on Foreign Keys
**Location:** `app/models/decision.py`

**Issue:** `SignalUserDecision.signal_id` and `user_id` have indexes, but composite queries (both signal_id AND user_id) would benefit from a composite index.

**Recommendation:** Add composite index:
```python
__table_args__ = (
    Index('ix_signal_user', 'signal_id', 'user_id'),
)
```

---

### 4.4 N+1 Query Problem in Scan Worker
**Location:** `app/workers/scan_worker.py:46-95`

**Issue:** For each subscriber, the worker makes individual database queries for user settings. This creates N+1 query problems with many subscribers.

**Code:**
```python
for user_id in subscriber_ids:
    user_settings_obj = await UserService.get_user_settings(db, user_id)
```

**Recommendation:** Batch fetch all user settings in a single query before the loop.

---

## 5. Error Handling Gaps

### 5.1 Unhandled Polygon API Pagination
**Location:** `app/providers/polygon.py:23-58`

**Issue:** The Polygon API returns paginated results, but the code only fetches the first page. Large option chains might be truncated.

**Recommendation:** Implement pagination handling using the `next_url` field in Polygon responses.

---

### 5.2 Silent Failure in Reminder Scheduling
**Location:** `app/services/reminder_service.py:83-86`

**Issue:** Errors in reminder scheduling are logged but not propagated. The calling code has no way to know if reminders were scheduled.

**Code:**
```python
except Exception as e:
    logger.error(f"Error scheduling reminders: {e}", exc_info=True)
    # No re-raise or return value indicating failure
```

**Recommendation:** Either return a status or raise the exception.

---

### 5.3 Missing Error Handler in Telegram Bot
**Location:** `app/bot/main.py`

**Issue:** No global error handler is registered for the Telegram bot. Unhandled exceptions in handlers could crash the bot.

**Recommendation:** Add an error handler:
```python
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling update {update}: {context.error}")

application.add_error_handler(error_handler)
```

---

### 5.4 HTTP Client Not Closed on Error
**Location:** `app/providers/polygon.py`

**Issue:** The `PolygonProvider` creates an `httpx.AsyncClient` but if `get_chain_snapshot()` raises an exception, the client may not be properly closed.

**Recommendation:** Use the client as an async context manager or implement proper cleanup in `__aexit__`.

---

### 5.5 No Retry Logic for External API Calls
**Location:** `app/providers/polygon.py`

**Issue:** No retry logic for transient network failures or rate limiting. The provider will fail immediately.

**Recommendation:** Implement retry with exponential backoff using `tenacity` or `httpx` built-in retry.

---

## 6. Data Validation Issues

### 6.1 Missing Ticker Symbol Validation
**Location:** `app/api/routes/watchlist.py`, `app/bot/handlers/watchlist.py`

**Issue:** Ticker symbols are only uppercased and stripped, but not validated against a pattern. Invalid tickers like "A B C" or "!!!" would be accepted.

**Recommendation:** Add regex validation:
```python
import re
if not re.match(r'^[A-Z]{1,5}$', ticker):
    raise HTTPException(status_code=400, detail="Invalid ticker format")
```

---

### 6.2 Missing Timezone Validation
**Location:** `app/api/routes/settings.py`, `app/bot/handlers/settings.py`

**Issue:** Timezone strings are not validated against `pytz` or `zoneinfo`. Invalid timezones will cause runtime errors.

**Recommendation:** Validate timezone before saving:
```python
try:
    pytz.timezone(timezone_str)
except pytz.UnknownTimeZoneError:
    raise HTTPException(status_code=400, detail="Invalid timezone")
```

---

### 6.3 Missing Bounds Validation for Numeric Settings
**Location:** `app/api/routes/settings.py`, `app/bot/handlers/settings.py`

**Issue:** Settings like `ff_threshold`, `min_open_interest`, `cooldown_minutes` have no bounds checking. Negative or extremely large values could cause issues.

**Recommendation:** Add validation:
```python
if request.ff_threshold is not None:
    if not 0 < request.ff_threshold <= 1:
        raise HTTPException(status_code=400, detail="FF threshold must be between 0 and 1")
```

---

### 6.4 SignalUserDecision Metadata Field Misnamed
**Location:** `app/models/decision.py:22`

**Issue:** The model has `decision_metadata` column but `SignalService.record_decision()` passes `metadata` parameter.

**Code in model:**
```python
decision_metadata = Column(JSON, default=dict)
```

**Code in service:**
```python
decision_record = SignalUserDecision(
    ...
    metadata=metadata or {}  # Wrong field name
)
```

**Impact:** Metadata is likely not being saved.

**Recommendation:** Fix the field name in either the model or the service to match.

---

## 7. Logic Errors

### 7.1 DTE Calculated from `date.today()` Not `as_of`
**Location:** `app/providers/polygon.py:117-119`

**Issue:** DTE is calculated from `date.today()` rather than the chain snapshot's `as_of` timestamp. This could cause issues if processing cached/delayed data.

**Code:**
```python
today = date.today()
for expiry_date, expiry_contracts in sorted(expiry_map.items()):
    dte = (expiry_date - today).days
```

**Recommendation:** Pass the reference date from the snapshot's timestamp.

---

### 7.2 Forward Factor Calculation for Zero DTE
**Location:** `app/services/signal_engine.py:26-54`

**Issue:** If front_dte is 0 (expiry day), the calculation divides by very small numbers, potentially causing floating-point issues.

**Code:**
```python
t1 = front_dte / 365.0  # Could be 0
if t1 <= 0 or t2 <= 0 or t1 >= t2:
    return None  # Only catches zero, not near-zero
```

**Recommendation:** Add a minimum DTE threshold (e.g., front_dte >= 1) before calculation.

---

### 7.3 Quiet Hours Check Uses Wrong Timezone Conversion
**Location:** `app/utils/time.py:23-47`

**Issue:** The reminder scheduling in `reminder_service.py` uses UTC times directly (9:30 AM) but claims to be "ET". The quiet hours check uses the user's timezone correctly, but the two are inconsistent.

**Code in reminder_service.py:**
```python
one_day_before = datetime.combine(
    front_expiry_date - timedelta(days=1),
    datetime.min.time().replace(hour=9, minute=30)  # Claims to be ET but is naive
)
```

**Impact:** Reminders are scheduled in naive datetime (no timezone), compared against `datetime.utcnow()` - timezone handling is inconsistent.

**Recommendation:** Use proper timezone-aware datetimes throughout.

---

### 7.4 User Status Check Duplicated
**Location:** `app/core/auth.py:143-155 and 163-176`

**Issue:** `get_current_user()` already checks `user.status != "active"` and raises 403. Then `get_current_active_user()` duplicates this check.

**Recommendation:** Remove the redundant check from one location.

---

### 7.5 Missing Expiry Date in Reminder Cancellation
**Location:** `app/services/reminder_service.py:89-112`

**Issue:** `cancel_reminders()` iterates through ALL reminders to find matches. This is O(n) and inefficient.

**Recommendation:** Store reminders with a composite key (signal_id:user_id) for O(1) lookup.

---

## 8. Performance Issues

### 8.1 No Connection Pooling for PolygonProvider
**Location:** `app/providers/polygon.py`

**Issue:** Each `PolygonProvider` instance creates its own `httpx.AsyncClient`. The `ScanWorker` creates one instance, but if multiple workers run, connection pooling isn't shared.

**Recommendation:** Use a shared client with proper connection limits.

---

### 8.2 Full Table Scan for Ticker Registry Update
**Location:** `app/services/ticker_service.py:17-66`

**Issue:** `update_ticker_registry()` fetches all `MasterTicker` records to check which ones have zero subscribers. This becomes slow with many tickers.

**Recommendation:** Use a targeted UPDATE query instead:
```python
await db.execute(
    update(MasterTicker)
    .where(~MasterTicker.ticker.in_(ticker_counts.keys()))
    .values(active_subscriber_count=0, scan_tier='low')
)
```

---

### 8.3 Unbounded Redis Sorted Set Growth
**Location:** `app/services/reminder_service.py`

**Issue:** Processed reminders are removed, but if reminders are scheduled and never processed (worker down), the sorted set grows unbounded.

**Recommendation:** Add TTL or periodic cleanup of old reminders.

---

### 8.4 MD5 Used for Dedupe Key
**Location:** `app/services/signal_service.py:14-20`

**Issue:** MD5 is cryptographically broken. While this is just for deduplication (not security), it's better practice to use SHA256.

**Recommendation:** Replace with `hashlib.sha256()`.

---

## 9. Code Quality & Maintainability

### 9.1 Inconsistent Error Response Format
**Location:** Various API routes

**Issue:** Some routes return `{"detail": "..."}`, others return `{"message": "..."}`, and some return `{"error": "..."}`.

**Recommendation:** Standardize on one format, preferably using FastAPI's default `{"detail": "..."}` format.

---

### 9.2 Magic Strings for Enums
**Location:** Throughout codebase

**Issue:** Status values ("active", "merged", "placed", "ignored"), scan priorities ("standard", "high", "turbo"), etc. are hardcoded strings.

**Recommendation:** Use Python Enums:
```python
class UserStatus(str, Enum):
    ACTIVE = "active"
    MERGED = "merged"
    INACTIVE = "inactive"
```

---

### 9.3 Duplicate Code in Reminder Formatting
**Location:** `app/workers/reminder_worker.py:28-68` and `app/utils/formatting.py:55-100`

**Issue:** `format_reminder_message()` is implemented twice with nearly identical code.

**Recommendation:** Use the centralized version in `formatting.py` only.

---

### 9.4 Hardcoded Limits
**Location:** Various files

**Issue:** Limits like `50` (default signal limit), `20` (history limit), `300` (cache TTL), `86400` (key TTL) are hardcoded throughout.

**Recommendation:** Move to configuration or constants file.

---

### 9.5 Missing Type Hints
**Location:** Various files

**Issue:** Some functions lack proper type hints, making IDE support and static analysis less effective.

**Examples:**
- `app/utils/formatting.py:format_history(decisions: list)` should be `List[Dict[str, Any]]`
- Return types missing on many functions

---

## 10. Configuration Issues

### 10.1 Log Level Parsing Not Validated
**Location:** `app/core/config.py` and `app/api/main.py`

**Issue:** If an invalid `log_level` is provided, `getattr(logging, settings.log_level.upper())` will raise AttributeError.

**Recommendation:** Validate in config:
```python
@field_validator('log_level')
@classmethod
def validate_log_level(cls, v):
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if v.upper() not in valid_levels:
        raise ValueError(f"log_level must be one of {valid_levels}")
    return v.upper()
```

---

### 10.2 SQLite Pool Settings Applied to SQLite
**Location:** `app/core/database.py:17-22`

**Issue:** The condition `if "sqlite" not in settings.database_url` is correct, but the log message always says "pool_size=10" regardless of database type.

**Recommendation:** Make log message conditional.

---

### 10.3 Redis URL and Port Potentially Inconsistent
**Location:** `app/core/config.py:20-21`

**Issue:** Both `redis_url` and `redis_port` are configured, but only `redis_url` is used. The `redis_port` setting is unused.

**Recommendation:** Either use both or remove `redis_port` to avoid confusion.

---

## Summary

| Category | Count | Critical |
|----------|-------|----------|
| Critical Issues | 3 | 3 |
| Security Vulnerabilities | 5 | 2 |
| Race Conditions | 4 | 2 |
| Database Issues | 4 | 1 |
| Error Handling | 5 | 1 |
| Data Validation | 4 | 1 |
| Logic Errors | 5 | 1 |
| Performance | 4 | 0 |
| Code Quality | 5 | 0 |
| Configuration | 3 | 0 |
| **Total** | **42** | **11** |

---

## Priority Recommendations

### Immediate (Fix Now)
1. Fix double-commit issue in database session management
2. Add rate limiting to authentication endpoints
3. Fix CORS wildcard fallback security issue
4. Add Telegram bot error handler
5. Fix `metadata` vs `decision_metadata` field name mismatch

### High Priority (This Sprint)
1. Address race conditions in stability tracker and signal deduplication
2. Add proper timezone handling for reminders
3. Implement retry logic for Polygon API
4. Add validation for ticker symbols, timezones, and numeric bounds
5. Replace deprecated `datetime.utcnow()`

### Medium Priority (Next Sprint)
1. Add Polygon API pagination handling
2. Optimize N+1 queries in scan worker
3. Standardize error response format
4. Add proper connection pooling for external APIs
5. Create Enums for magic strings

### Low Priority (Backlog)
1. Replace MD5 with SHA256 for dedupe keys
2. Add composite indexes for frequent queries
3. Clean up duplicate reminder formatting code
4. Move hardcoded limits to configuration
5. Add comprehensive type hints
