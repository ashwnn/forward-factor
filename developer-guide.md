# Forward Factor Signal Bot

Technical Design Specification

## 1. Purpose

Build a production grade Telegram bot that:

1. Lets users register and manage a personal watchlist of tickers.
2. Scans a shared master ticker list for Forward Factor dislocations using real time options IV and greeks.
3. Notifies subscribed users of validated signals with actionable order metadata for manual execution at Wealthsimple.
4. Records all signals and each user decision (Place or Ignore) to a database.
5. Supports multiple users with independent configurations.

No automated trade placement is performed.

---

## 2. Strategy summary (for implementation context)

Given two expiries:

* Front expiry at time (T_1), implied vol (\sigma_1)
* Back expiry at time (T_2), implied vol (\sigma_2)

Compute:
[
V_1 = \sigma_1^2 T_1
\qquad
V_2 = \sigma_2^2 T_2
]
[
V_{fwd} = \frac{V_2 - V_1}{T_2 - T_1}
\qquad
\sigma_{fwd} = \sqrt{V_{fwd}}
]
[
FF = \frac{\sigma_1 - \sigma_{fwd}}{\sigma_{fwd}}
]

Signal when (FF \ge \theta) and all quality filters pass.

---

## 3. Requirements

### 3.1 Functional requirements

1. **User onboarding**

   * A Telegram user runs /start to create an account.
   * Chat id is persistent identity.

2. **Watchlist management**

   * /add TICKER adds ticker to user subscriptions.
   * /remove TICKER removes ticker.
   * /list shows active tickers.

3. **Per user settings**

   * User can set:

     * FF threshold
     * Target DTE pairs and tolerances
     * Vol point (ATM, 35d put, 35d call)
     * Liquidity filters: min OI, max bid ask percent, min volume
     * Stability requirement (N consecutive scans)
     * Cooldown minutes between alerts
     * Quiet hours
     * Preferred structure (calls, puts, double calendar)

4. **Master ticker scanning**

   * System maintains a global list of active tickers.
   * Each ticker is scanned once per cycle and results are fanned out to all subscribed users.

5. **Signal generation**

   * Pull latest options chain.
   * Compute FF on configured DTE windows.
   * Apply data quality and event filters.
   * Create signal records.

6. **Notifications**

   * Send Telegram message for each user eligible signal.
   * Inline buttons: Place trade, Ignore.
   * Handle callback queries and record decisions. Telegram inline keyboards and callbacks are supported via Bot API. ([core.telegram.org][1])

7. **Persistence**

   * Store every global signal.
   * Store every user decision with timestamp and decision type.

8. **Analytics and audit**

   * /history to view last N signals and decisions.
   * Developer metrics endpoint.

### 3.2 Non functional requirements

1. **Scalability**

   * Support thousands of tickers and users.
   * Horizontal scale via queue based workers.

2. **Reliability**

   * At least once scan jobs with idempotent signal writes.
   * Graceful degradation under API rate limits.

3. **Latency**

   * Target scan to notify time under 2 minutes for active windows.

4. **Security**

   * No broker credentials stored.
   * Encrypt vendor API keys at rest.

---

## 4. External APIs

### 4.1 Options data: Polygon

Polygon.io provides an option chain snapshot endpoint returning per contract IV, greeks, quotes, and OI, suitable for extracting per expiry ATM or delta based IV. ([polygon.io][3])

The provider is abstracted behind a single interface:

**Interface: OptionChainProvider**

* `get_chain_snapshot(ticker) -> ChainSnapshot`

  * includes expiries, contracts, IV, delta, bid, ask, volume, OI, underlying price, as of timestamp.

The Polygon provider is fully implemented in `app/providers/polygon.py`.

### 4.2 Underlying realtime price: Polygon equities snapshot or websocket

Use Polygon equities snapshot or websocket to validate current underlying price and check for halts or stale quotes. Universal or stock snapshot endpoints are recommended. ([polygon.io][3])

### 4.3 Telegram

Use Telegram Bot API:

* `sendMessage`
* `editMessageReplyMarkup` (optional)
* `answerCallbackQuery`
* Webhook or long polling for updates. ([core.telegram.org][1])

---

## 5. System architecture

### 5.1 Services

1. **telegram bot service**

   * Receives Telegram updates.
   * Parses commands.
   * Calls backend APIs.
   * Stateless.

2. **backend api service**

   * User CRUD
   * Settings CRUD
   * Subscription CRUD
   * Reads signals and decisions.

3. **master ticker registry**

   * Maintains global tickers with ref counts.
   * Produces list for scheduler.

4. **scan scheduler**

   * Cron like process producing scan jobs based on cadence rules.

5. **scan workers**

   * Pull chain snapshot.
   * Normalize data.
   * Run signal engine.
   * Persist snapshots and signals.

6. **notification router**

   * Reads new signals.
   * Joins to subscriptions.
   * Applies per user filters.
   * Sends Telegram alerts.

### 5.2 Data flow

1. User adds ticker.
2. backend updates subscriptions and master registry.
3. scheduler enqueues jobs for active tickers.
4. worker fetches chain and price, computes signals.
5. signals persisted globally.
6. router fans out qualified signals to users.
7. decisions stored per user per signal.

---

## 6. Database schema

### 6.1 Tables

**users**

* id uuid pk
* telegram_chat_id text unique
* created_at timestamptz
* status text

**user_settings**

* user_id uuid pk fk users
* ff_threshold float default 0.20
* dte_pairs jsonb
  example:
  `[{ "front": 30, "back": 60, "front_tol": 5, "back_tol": 10 }, ... ]`
* vol_point text default "ATM"
* min_open_interest int default 100
* min_volume int default 10
* max_bid_ask_pct float default 0.08
* sigma_fwd_floor float default 0.05
* stability_scans int default 2
* cooldown_minutes int default 120
* quiet_hours jsonb
* preferred_structure text default "ATM_calendar_call"
* timezone text default "America/Vancouver"

**subscriptions**

* user_id uuid fk users
* ticker text
* active bool
* added_at timestamptz
* pk (user_id, ticker)

**master_tickers**

* ticker text pk
* active_subscriber_count int
* last_scan_at timestamptz
* scan_tier text
  values: high, medium, low

**option_chain_snapshots**

* id uuid pk
* ticker text fk master_tickers
* as_of_ts timestamptz
* provider text
* underlying_price float
* raw_payload jsonb
* quality_score float

**signals**

* id uuid pk
* ticker text
* as_of_ts timestamptz
* front_expiry date
* back_expiry date
* front_dte int
* back_dte int
* front_iv float
* back_iv float
* sigma_fwd float
* ff_value float
* vol_point text
* quality_score float
* reason_codes jsonb
* dedupe_key text unique

**signal_user_decisions**

* id uuid pk
* signal_id uuid fk signals
* user_id uuid fk users
* decision text
  values: placed, ignored, expired, error
* decision_ts timestamptz
* metadata jsonb

---

## 7. Scanning and cadence rules

### 7.1 Active window detection

For each ticker, determine nearest expiries. If any expiry DTE falls inside any user configured front tolerance range, ticker qualifies for high tier scanning.

### 7.2 Cadence

* High tier: every 2 to 5 minutes
* Medium tier: every 15 minutes
* Low tier: every 60 minutes

Tier is recomputed daily and on subscription changes.

### 7.3 API efficiency

* One chain snapshot per ticker per scan cycle.
* Cache snapshot in Redis keyed by ticker and scan timestamp bucket.
* Workers must not re call provider if cached fresh within same cycle.

---

## 8. Signal engine

### 8.1 Inputs

* ChainSnapshot containing list of expiries and contracts.

### 8.2 Vol point selection

Per expiry:

1. Determine target strike:

   * ATM: strike nearest to underlying price.
   * 35d put or call: strike with delta nearest to target delta.
2. Select contract at that strike.
3. Use mid IV:
   [
   \sigma = \frac{\sigma_{bid} + \sigma_{ask}}{2}
   ]
   If vendor provides single IV, use it.

### 8.3 Expiry pairing

For each DTE pair rule ( (d_1, d_2, tol_1, tol_2)):

1. Choose front expiry with DTE in ([d_1 - tol_1, d_1 + tol_1]).
2. Choose back expiry with DTE in ([d_2 - tol_2, d_2 + tol_2]).
3. Prefer closest to targets.

### 8.4 Forward Factor computation

Use formula section above with:
[
T = \frac{DTE}{365}
]

Reject if:

* (T_1 \ge T_2)
* (V_{fwd} < 0)
* (\sigma_{fwd} < sigma_fwd_floor)

### 8.5 Liquidity and sanity filters

Reject if any of:

* bid or ask missing
* bid ask percent > max_bid_ask_pct
  percent = (ask - bid) / midpoint
* OI < min_open_interest for either leg
* volume < min_volume for either leg
* snapshot older than staleness limit (ex 5 minutes)
* underlying halted or stale

### 8.6 Stability and debounce

Maintain per ticker per pair state in Redis:

* `last_ff`
* `consecutive_above_threshold`
* `last_alert_ts`

Emit alert only if:

1. `consecutive_above_threshold >= stability_scans`
2. now - last_alert_ts >= cooldown_minutes
3. FF increased by at least delta_ff_min since last alert (default 0.02)
   This prevents repeating a flat signal.

### 8.7 Output

A global **signal** record with:

* computed fields
* quality_score
* reason_codes for rejections (logged even if no alert)

---

## 9. Notification router

### 9.1 User eligibility

For each new signal:

1. Find all active subscriptions for ticker.
2. For each user:

   * Apply user specific FF threshold override.
   * Apply quiet hours.
   * Apply structure preferences if mismatch is disallowed.

### 9.2 Telegram message payload

Include:

* ticker
* timestamp
* FF, front IV, forward IV, chosen DTEs and expiries
* liquidity stats
* order metadata:

  * legs: 2
  * leg 1: sell front expiry at strike X, quantity 1
  * leg 2: buy back expiry same strike X, quantity 1
  * side: call or put based on preferred_structure
  * expected net debit
  * close rule: close before front expiry

Include compatibility warning:

* Wealthsimple spread support varies by account. User may need a broker supporting calendars.

### 9.3 Inline actions

Attach inline keyboard:

* Place trade
* Ignore

On callback:

* Validate action and signal id.
* Insert into signal_user_decisions.
* Optionally edit message to show recorded decision.

---

## 10. Error handling

1. **Provider errors**

   * Retry on 5xx with exponential backoff.
   * On 429 respect rate limit headers and requeue.
   * Mark snapshot as failed, do not signal off stale data.

2. **Malformed data**

   * If IV missing for selected vol point, skip that pair and log reason code.

3. **Telegram delivery**

   * On send error, retry with backoff.
   * If permanent error (blocked bot), set user status inactive.

4. **Idempotency**

   * dedupe_key ensures no duplicate signals per scan bucket.

---

## 11. Security and privacy

* Telegram chat id is the identity. No passwords.
* Store vendor keys in secrets manager.
* Encrypt sensitive columns (keys, tokens).
* Rate limit user commands to prevent abuse.

---

## 12. Deployment

### 12.1 Components

* API and bot services as stateless containers.
* Scheduler container.
* Worker pool containers.
* Redis.
* Postgres.

### 12.2 Environments

* dev: sandbox keys, reduced cadence.
* prod: full cadence and monitoring.

---

## 13. Testing plan

1. **Unit tests**

   * FF math, including edge cases.
   * DTE pairing logic.
   * Liquidity filters.

2. **Integration tests**

   * Provider adapters with recorded fixtures.
   * Telegram callback flow end to end.

3. **Load tests**

   * Simulate 5k tickers, 10k users.
   * Verify scan latency and router throughput.

4. **Paper trading validation**

   * Run paper mode for several weeks and review hit rate.

---

## 14. Implementation checklist

1. Build provider adapter for Polygon chain snapshots. ✅ Complete
2. Implement DB schema migrations.
3. Implement scheduler plus tiered cadence.
4. Implement worker pool with caching.
5. Implement signal engine exactly per spec above.
6. Implement router and Telegram UX.
7. Add monitoring and alarms.
8. Run paper mode soak test.
9. Launch v1.