# Corporate Actions Handling

## 1. Introduction
As the Forward Factor bot evolves from a pure scanner to a system that might track performance over time or hold virtual positions, handling corporate actions becomes critical. Events like stock splits and dividends dramatically alter the price structure of the underlying asset, which in turn affects option strike prices and contract deliverables. Failure to account for these can lead to massive errors in P&L tracking and signal validation.

## 2. Current State Analysis
Currently, the system is designed as a **scanner**:
- It detects signals based on *current* market data.
- It does not persist "positions" or track the long-term performance of a specific option contract across multiple days/weeks in a way that requires adjustment logic.
- `SignalService` stores signals, but these are static records of a moment in time.

However, the TODO indicates a desire to:
> "handle stock splits and dividends... automatically adjust your strike price targets if a split occurs."

This implies a future state where we are either:
1.  **Backtesting**: Replaying history where splits occurred.
2.  **Paper Trading / Forward Testing**: Tracking a "virtual portfolio" of signals over weeks.

## 3. Polygon.io API for Corporate Actions
We can use the Polygon.io Reference Data APIs to fetch this information.

### Stock Splits
**Endpoint**: `/v3/reference/splits`
**Python Client**: `client.list_splits(ticker=...)`

**Key Data Points**:
- `execution_date`: The date the split goes into effect.
- `split_from`: The number of shares before the split.
- `split_to`: The number of shares after the split.

**Example**:
A 2-for-1 split would have `split_from=1`, `split_to=2`.
- Price gets divided by 2.
- Strike Price gets divided by 2.
- Number of Contracts gets multiplied by 2.

### Dividends
**Endpoint**: `/v3/reference/dividends`
**Python Client**: `client.list_dividends(ticker=...)`

**Key Data Points**:
- `ex_dividend_date`: The date the stock starts trading without the dividend.
- `cash_amount`: The amount paid per share.
- `dividend_type`: CD (Cash), SC (Special Cash), etc.

**Impact**:
- **Regular Cash Dividends**: Usually do *not* result in contract adjustment. The market prices the dividend into the option premiums (puts get more expensive, calls cheaper).
- **Special Dividends**: May result in contract adjustments (strike price reduction, or deliverables change).

## 4. Implementation Plan

### Phase 1: Data Ingestion (Daily Job)
Create a new worker or a scheduled task that runs once a day (e.g., pre-market).

1.  **Identify Active Tickers**: Get a list of all tickers currently involved in "open" signals or positions.
2.  **Fetch Corporate Actions**: Query Polygon for any splits or dividends with an `execution_date` or `ex_dividend_date` matching today.

```python
# Pseudo-code for checking splits
async def check_corporate_actions(tickers: List[str]):
    for ticker in tickers:
        splits = client.list_splits(
            ticker=ticker, 
            execution_date=date.today()
        )
        for split in splits:
            await handle_split(ticker, split)
```

### Phase 2: Adjustment Logic
When a split is detected, we must update our tracked data.

**Scenario**: We are tracking a target strike of $100 for AAPL.
**Event**: AAPL undergoes a 4-for-1 split (`split_from=1`, `split_to=4`).

**Adjustment**:
$$ \text{New Strike} = \text{Old Strike} \times \frac{\text{split\_from}}{\text{split\_to}} $$
$$ \text{New Strike} = 100 \times \frac{1}{4} = 25 $$

**Database Updates**:
- Update `target_strike` in `signals` or `positions` table.
- Log the adjustment event for audit trails.

### Phase 3: Option Contract Symbol Updates
Option symbols change after a split.
- **Standard Split**: The OCC usually issues new contracts. The old symbol `AAPL...100` might become `AAPL...25`.
- **Non-Standard**: Sometimes symbols get an integer suffix or other modification.

*Note: Polygon's Option Ticker format is `O:{Ticker}{Date}{Type}{Strike}`. If the strike changes, the ticker symbol changes.*

We need to regenerate the option ticker symbol based on the new strike price to continue fetching data for it.

## 5. Testing Strategy

### Unit Tests
1.  **Split Logic**:
    - Input: Strike $150, Split 3-for-1.
    - Expected: New Strike $50.
    - Input: Strike $100, Reverse Split 1-for-10.
    - Expected: New Strike $1000.
2.  **API Mocking**:
    - Mock `list_splits` to return a known split event.
    - Verify the handler function is called.

### Integration Tests
- Create a dummy signal in the test DB with a specific strike.
- Run the "Corporate Action Worker" with a mocked split event for that ticker.
- specific strike.
- Verify the signal in the DB has the updated strike price.

## 6. Future Considerations
- **Reverse Splits**: Logic is the inverse (`split_from` > `split_to`).
- **Mergers/Acquisitions**: These are complex and often result in cash-in-lieu or symbol changes. Might be out of scope for V1.
