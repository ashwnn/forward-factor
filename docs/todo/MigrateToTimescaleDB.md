# Migrate to TimescaleDB

## Overview

This document provides a comprehensive plan to migrate the Forward Factor bot from SQLite to TimescaleDB (PostgreSQL extension). This migration will unlock better concurrency, performance, and enable storing time-series market data for backtesting.

## Why TimescaleDB?

**Current Problem with SQLite:**
- **Concurrency Issues:** Multiple workers (`scan_worker`, `reminder_worker`, `scheduler`, `bot`, `api`) writing simultaneously causes "database is locked" errors
- **No Connection Pooling:** SQLite doesn't support connection pooling, limiting scalability
- **Limited Analytics:** No native time-series optimizations for market data analysis

**TimescaleDB Benefits:**
- **Production-Grade Concurrency:** Row-level locking allows multiple writers
- **Time-Series Optimization:** Hypertables automatically partition data by time
- **100% PostgreSQL Compatible:** Works seamlessly with SQLAlchemy and Alembic
- **Advanced Analytics:** Native time-series functions for aggregations and continuous queries
- **Scalability:** Connection pooling, replication, and horizontal scaling support

---

## Current Architecture Analysis

### Database Models
The project has 6 main models:

1. **`Signal`** - Stores computed Forward Factor signals (time-series candidate)
2. **`OptionChainSnapshot`** - Raw option chain snapshots (time-series candidate)
3. **`MasterTicker`** - Ticker registry with scan metadata
4. **`User`** - User accounts (Telegram + Web)
5. **`UserSettings`** - User-specific preferences
6. **`Subscription`** - User watchlist entries
7. **`SignalUserDecision`** - User feedback on signals

### Services Using the Database
- **API (`api/main.py`)** - FastAPI endpoints
- **Bot (`bot/main.py`)** - Telegram bot handlers
- **Scheduler (`scheduler/main.py`)** - Periodic scan scheduling
- **Workers:**
  - `scan_worker.py` - Processes tickers for signals
  - `reminder_worker.py` - Sends signal reminders
  - `discovery_worker.py` - Market-wide discovery

### Existing Configuration
- **Database:** `app/core/database.py` using async SQLAlchemy
- **Config:** `app/core/config.py` with `database_url` setting
- **Migrations:** Alembic with 2 existing migrations
- **Docker:** `docker-compose.yml` with hardcoded SQLite paths

---

## Migration Plan

### Phase 1: Add TimescaleDB Infrastructure

#### 1.1 Update Docker Compose
Add TimescaleDB container to `docker-compose.yml`:

```yaml
timescaledb:
  image: timescale/timescaledb:latest-pg16
  container_name: ff-bot-timescaledb
  environment:
    - POSTGRES_USER=${DB_USER:-ffbot}
    - POSTGRES_PASSWORD=${DB_PASSWORD}
    - POSTGRES_DB=${DB_NAME:-ffbot}
  ports:
    - "${DB_PORT:-5432}:5432"
  volumes:
    - timescale-data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-ffbot}"]
    interval: 10s
    timeout: 5s
    retries: 5
  networks:
    - apps
  labels:
    - "com.centurylinklabs.watchtower.enable=false"
```

Add volume:
```yaml
volumes:
  timescale-data:
```

#### 1.2 Update Environment Variables
Add to `.env.example` and `.env`:
```bash
# TimescaleDB Configuration
DB_USER=ffbot
DB_PASSWORD=<secure-password>
DB_NAME=ffbot
DB_HOST=timescaledb
DB_PORT=5432
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
```

#### 1.3 Update Requirements
Add to `requirements.txt`:
```
asyncpg==0.29.0  # PostgreSQL async driver
psycopg2-binary==2.9.9  # For Alembic migrations (sync)
```

### Phase 2: Database Schema Migration

#### 2.1 Create TimescaleDB Migration
Create new Alembic migration: `alembic/versions/YYYYMMDD_HHMM_migrate_to_timescaledb.py`

Key changes:
1. **Enable TimescaleDB Extension:**
   ```python
   op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
   ```

2. **Convert Time-Series Tables to Hypertables:**
   ```python
   # Signals table - partition by as_of_ts
   op.execute("""
       SELECT create_hypertable(
           'signals',
           'as_of_ts',
           chunk_time_interval => INTERVAL '1 day',
           if_not_exists => TRUE
       );
   """)
   
   # Option chain snapshots - partition by as_of_ts
   op.execute("""
       SELECT create_hypertable(
           'option_chain_snapshots',
           'as_of_ts',
           chunk_time_interval => INTERVAL '1 day',
           if_not_exists => TRUE
       );
   """)
   ```

3. **Add Compression Policies (Optional but Recommended):**
   ```python
   # Compress data older than 7 days
   op.execute("""
       SELECT add_compression_policy(
           'signals',
           INTERVAL '7 days'
       );
   """)
   ```

4. **Create Continuous Aggregates for Analytics (Future):**
   ```python
   # Example: Hourly signal counts per ticker
   op.execute("""
       CREATE MATERIALIZED VIEW signals_hourly
       WITH (timescaledb.continuous) AS
       SELECT
           time_bucket('1 hour', as_of_ts) AS bucket,
           ticker,
           COUNT(*) as signal_count,
           AVG(ff_value) as avg_ff
       FROM signals
       GROUP BY bucket, ticker
       WITH NO DATA;
   """)
   ```

#### 2.2 Handle Data Type Differences
- **UUID Fields:** SQLite uses `String` but PostgreSQL has native `UUID` type
  - Current: `id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))`
  - Consider switching to: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
  - **Decision:** Keep as `String` for backwards compatibility, migrate UUID type later

- **JSON Fields:** Both support JSON, no changes needed

- **DateTime with Timezone:** SQLite stores as string, PostgreSQL is timezone-aware
  - Current: `Column(DateTime, default=lambda: datetime.now(timezone.utc))`
  - PostgreSQL will properly store with timezone, no code changes needed

#### 2.3 Update Indexes
TimescaleDB automatically creates time-based indexes on hypertables. Review existing indexes:
- `signals`: Already has indexes on `ticker`, `as_of_ts`, `ff_value`, `dedupe_key`
- Consider adding composite indexes for common queries:
  ```python
  op.create_index(
      'idx_signals_ticker_time',
      'signals',
      ['ticker', 'as_of_ts'],
      postgresql_using='btree'
  )
  ```

### Phase 3: Application Changes

#### 3.1 Update Database Configuration
Modify `app/core/database.py`:

```python
# Remove SQLite-specific logic
is_sqlite = "sqlite" in settings.database_url
if not is_sqlite:
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20
```

Change to:
```python
# Always use connection pooling (PostgreSQL)
engine_args["pool_size"] = 10
engine_args["max_overflow"] = 20
engine_args["pool_timeout"] = 30
engine_args["pool_recycle"] = 3600  # Recycle connections hourly
```

#### 3.2 Update All Services
Change hardcoded `DATABASE_URL` in `docker-compose.yml`:

**Before:**
```yaml
environment:
  - DATABASE_URL=sqlite+aiosqlite:///./data/ffbot.db
```

**After:**
```yaml
environment:
  - DATABASE_URL=${DATABASE_URL}
```

Apply to: `api`, `bot`, `scheduler`, `worker`, `reminder-worker`

#### 3.3 No Code Changes Required
Since we're using SQLAlchemy ORM, **no application code changes** are needed. The ORM abstracts the database layer.

### Phase 4: Data Migration Strategy

#### Option A: Fresh Start (Recommended for Development)
- Start with empty TimescaleDB
- Run Alembic migrations from scratch
- Users re-subscribe to tickers
- **Pros:** Clean, no migration complexity
- **Cons:** Lose historical signals

#### Option B: SQLite → PostgreSQL Data Migration (Production)
1. **Export SQLite Data:**
   ```python
   # Create script: scripts/export_sqlite_data.py
   import sqlite3
   import json
   
   conn = sqlite3.connect('./data/ffbot.db')
   cursor = conn.cursor()
   
   # Export each table to JSON
   for table in ['users', 'user_settings', 'subscriptions', ...]:
       cursor.execute(f"SELECT * FROM {table}")
       rows = cursor.fetchall()
       # ... export to JSON file
   ```

2. **Import into TimescaleDB:**
   ```python
   # Create script: scripts/import_to_timescale.py
   from app.core.database import get_async_session
   from app.models import *
   import json
   
   async def import_data():
       async with get_async_session() as session:
           # Read JSON files and insert
   ```

3. **Validation Script:**
   ```python
   # Verify row counts match
   # Verify sample data integrity
   ```

### Phase 5: Testing Strategy

#### 5.1 Unit Tests
All existing unit tests should pass without modification since they use in-memory SQLite via `fakeredis` and pytest fixtures.

**Run tests:**
```bash
pytest tests/unit/ -v
```

**Potential Issues:**
- Tests using `sqlite+aiosqlite:///` connection strings directly
- **Fix:** Update `conftest.py` to use PostgreSQL test database

#### 5.2 Integration Tests
Create new integration test: `tests/integration/test_timescaledb.py`

```python
import pytest
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_hypertable_insertion(async_session):
    """Verify hypertables work correctly."""
    signal = Signal(
        ticker="AAPL",
        as_of_ts=datetime.now(timezone.utc),
        # ... other fields
    )
    async_session.add(signal)
    await async_session.commit()
    
    # Verify insertion
    result = await async_session.execute(
        select(Signal).where(Signal.ticker == "AAPL")
    )
    assert result.scalar_one()

@pytest.mark.asyncio
async def test_concurrent_writes(async_session):
    """Verify multiple workers can write simultaneously."""
    # Simulate concurrent signal writes
    tasks = [create_signal(f"TICKER{i}") for i in range(10)]
    await asyncio.gather(*tasks)
```

**Run integration tests:**
```bash
pytest tests/integration/ -v --capture=no
```

#### 5.3 Performance Tests
Create `tests/performance/test_query_performance.py`:

```python
@pytest.mark.asyncio
async def test_time_range_query_performance():
    """Verify TimescaleDB time-series query performance."""
    start = time.time()
    
    # Query signals from last 24 hours
    result = await session.execute(
        select(Signal)
        .where(Signal.as_of_ts > datetime.now(timezone.utc) - timedelta(days=1))
    )
    
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Query took {elapsed}s, expected < 1s"
```

#### 5.4 Manual Testing Checklist
- [ ] Start services with TimescaleDB: `docker-compose up -d`
- [ ] Verify migrations run: Check container logs for `alembic upgrade head`
- [ ] Test Telegram bot: Send `/start` command
- [ ] Test API: `curl http://localhost:8000/api/v1/health`
- [ ] Subscribe to ticker via bot: `/watchlist add AAPL`
- [ ] Trigger scan: Verify signal appears in database
- [ ] Check frontend: Login and view watchlist
- [ ] Verify background workers: Check logs for scan activity

### Phase 6: Monitoring & Rollback

#### 6.1 Health Checks
Add database health endpoint in `app/api/routes/health.py`:

```python
@router.get("/health/db")
async def check_database(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "timescaledb"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

#### 6.2 Rollback Plan
If issues arise, rollback to SQLite:

1. **Stop all services:**
   ```bash
   docker-compose down
   ```

2. **Revert DATABASE_URL:**
   ```bash
   # .env
   DATABASE_URL=sqlite+aiosqlite:///./data/ffbot.db
   ```

3. **Revert docker-compose.yml:**
   ```bash
   git checkout docker-compose.yml
   ```

4. **Restart services:**
   ```bash
   docker-compose up -d
   ```

5. **Restore data backup (if Option B was used):**
   ```bash
   cp backups/ffbot_backup.db data/ffbot.db
   ```

---

## Potential Issues & Solutions

### Issue 1: "Database is Locked" During Migration
**Cause:** SQLite limitations during heavy concurrent access
**Solution:** 
- Run migrations manually with all other services stopped
- Or use Option A (fresh start) to avoid data migration complexity

### Issue 2: Connection Pool Exhaustion
**Cause:** Too many concurrent async connections
**Solution:**
- Tune `pool_size` and `max_overflow` in `database.py`
- Monitor with: `SELECT count(*) FROM pg_stat_activity;`

### Issue 3: Alembic Migration Fails
**Cause:** PostgreSQL dialect differences (e.g., `AUTOINCREMENT` → `SERIAL`)
**Solution:**
- Use `render_as_batch=True` in Alembic (already configured)
- Test migrations on staging environment first

### Issue 4: Test Suite Fails
**Cause:** Tests using hardcoded SQLite connection strings
**Solution:**
- Update `tests/conftest.py` to use environment variable
- Use `pytest.ini` to set `TEST_DATABASE_URL`

### Issue 5: Hypertable Constraints
**Cause:** TimescaleDB requires time column to be NOT NULL
**Solution:**
- All time-series models already have `nullable=False` on `as_of_ts` ✓

### Issue 6: Frontend Not Connecting
**Cause:** CORS configuration or backend URL mismatch
**Solution:**
- Verify `BACKEND_URL` in frontend environment
- Check `cors_origins` in backend config

---

## Enhanced Features (Post-Migration)

### 1. Store Historical Market Data
Create new models in `app/models/market_data.py`:

```python
class OHLCVBar(Base):
    """OHLC + Volume bars from Polygon."""
    __tablename__ = "ohlcv_bars"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    timeframe = Column(String, nullable=False)  # '1min', '1hour', '1day'
```

Convert to hypertable:
```sql
SELECT create_hypertable('ohlcv_bars', 'timestamp', chunk_time_interval => INTERVAL '7 days');
```

### 2. Backtesting Infrastructure
Create continuous aggregate for easy backtesting:

```sql
CREATE MATERIALIZED VIEW signals_daily_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', as_of_ts) AS day,
    ticker,
    COUNT(*) as signal_count,
    AVG(ff_value) as avg_ff,
    MAX(ff_value) as max_ff
FROM signals
GROUP BY day, ticker;
```

### 3. Advanced Analytics
Add retention policies:

```sql
-- Delete raw signals older than 90 days
SELECT add_retention_policy('signals', INTERVAL '90 days');

-- Compress option chain snapshots older than 14 days
SELECT add_compression_policy('option_chain_snapshots', INTERVAL '14 days');
```

---

## Timeline Estimate

| Phase | Estimated Time | Priority |
|-------|----------------|----------|
| 1. Infrastructure Setup | 2 hours | High |
| 2. Schema Migration | 3 hours | High |
| 3. Application Changes | 1 hour | High |
| 4. Data Migration (if needed) | 4 hours | Medium |
| 5. Testing | 4 hours | High |
| 6. Monitoring Setup | 1 hour | Medium |
| **Total** | **15 hours** | - |

---

## Conclusion

Migrating to TimescaleDB is a **high-value, low-risk** change:
- ✅ Solves concurrency issues with minimal code changes
- ✅ Unlocks time-series analytics for backtesting
- ✅ Production-ready with connection pooling and replication
- ✅ Clear rollback path if issues arise

**Recommended Approach:**
1. Start with **Option A (Fresh Start)** in development
2. Test thoroughly with integration tests
3. Run in staging for 1 week
4. Deploy to production with **Option B (Data Migration)**
