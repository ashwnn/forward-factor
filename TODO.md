1. Market-Wide Scanner (The "Golden Goose")
Feature: All US Options Tickers + Reference Data
Current State: Your bot only scans tickers that users explicitly subscribe to.
Upgrade: You can now build a "Discovery Mode".
Use the Reference Data API to get a list of all liquid optionable stocks (e.g., top 100 by volume).
The bot can autonomously scan these tickers to find "Forward Factor" anomalies that you didn't know about.
Result: The bot tells you what to trade, instead of you telling it what to watch.
2. Event-Driven Scanning (Smarter, Not Harder)
Feature: WebSockets
Current State: The bot likely polls or loops through tickers blindly.
Upgrade: Connect to the Polygon WebSocket stream (even with 15m delay).
Listen for "Trade" or "Quote" updates on your watched tickers.
Only trigger a heavy get_chain_snapshot calculation when the underlying price moves significantly (e.g., > 0.5%).
Result: Saves resources and ensures you scan at the most relevant moments.
3. Stability Backtesting
Feature: Minute Aggregates
Current State: Your stability_tracker seems to wait for live scans to confirm if a signal is real.
Upgrade: When a signal appears, fetch the last 60 minutes of Minute Aggregates for the option contract.
Check if the price/IV has been stable over the last hour historically.
Result: Instant "Stability" verification without waiting for future scans.
4. Corporate Actions Handling
Feature: Corporate Actions
Upgrade: If your bot holds positions or tracks performance over weeks, you must handle stock splits and dividends.
Use this endpoint to automatically adjust your strike price targets if a split occurs.