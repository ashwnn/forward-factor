## Core mathematics

### Inputs

* (T_1, T_2): times to expiry in years for front and back expirations, with (0 < T_1 < T_2).
* (\sigma_1, \sigma_2): annualized implied vols (ATM or chosen delta) for front and back expirations, expressed as decimals (e.g., 0.25 for 25 percent).

### Step 1. Total variance to each expiry

Variance over a horizon is additive, so convert each IV to total variance:

[
V_1 = \sigma_1^2 , T_1
]
[
V_2 = \sigma_2^2 , T_2
]

### Step 2. Forward (between-expiries) annualized variance

Forward variance for the window ([T_1, T_2]):

[
V_{\text{fwd}} = \frac{V_2 - V_1}{T_2 - T_1}
= \frac{\sigma_2^2 T_2 - \sigma_1^2 T_1}{T_2 - T_1}
]

Sanity requirement: (V_{\text{fwd}} \ge 0). If negative, treat as bad data or an arbitrage distortion and discard.

### Step 3. Forward volatility

[
\sigma_{\text{fwd}} = \sqrt{V_{\text{fwd}}}
]

### Step 4. Forward Factor

Forward Factor measures how expensive front IV is relative to implied forward IV:

[
FF = \frac{\sigma_1 - \sigma_{\text{fwd}}}{\sigma_{\text{fwd}}}
]

Interpretation:

* (FF > 0): front IV above forward IV (backwardation). Candidate long calendar.
* Larger (FF) means stronger dislocation. Typical trigger is (FF \ge \theta), where (\theta) is often 0.20, sometimes lower for certain DTE pairs.

---

## Pseudo code (signal engine)

```python
# Inputs should be decimals for vol, integer days for dte.

def forward_factor(front_iv, front_dte, back_iv, back_dte):
    # convert days to years
    t1 = front_dte / 365.0
    t2 = back_dte / 365.0
    
    if t1 <= 0 or t2 <= 0 or t1 >= t2:
        return None  # invalid pair
    
    # total variance to each expiry
    v1 = (front_iv ** 2) * t1
    v2 = (back_iv ** 2) * t2
    
    # annualized forward variance
    vfwd = (v2 - v1) / (t2 - t1)
    if vfwd < 0:
        return None  # bad data or inconsistent surface
    
    sigma_fwd = vfwd ** 0.5
    if sigma_fwd <= 0:
        return None
    
    ff = (front_iv - sigma_fwd) / sigma_fwd
    return ff


def scan_chain_for_signals(chain, dte_pairs, threshold):
    """
    chain: option chain grouped by expiry, with per-expiry ATM iv (or chosen delta iv)
    dte_pairs: list of (front_target_dte, back_target_dte) windows or rules
    threshold: e.g. 0.20
    """
    signals = []

    # pre-filter: corporate events
    if earnings_between_any_pair(chain, dte_pairs):
        return signals

    for (front_exp, back_exp) in valid_expiry_pairs(chain, dte_pairs):
        front = chain[front_exp]
        back  = chain[back_exp]

        # choose consistent vol point on surface
        front_iv = get_surface_iv(front, method="ATM")  # or "35d_put", etc
        back_iv  = get_surface_iv(back,  method="ATM")

        if front_iv is None or back_iv is None:
            continue

        ff = forward_factor(front_iv, front.dte, back_iv, back.dte)
        if ff is None:
            continue

        if ff >= threshold:
            signals.append({
                "front_expiry": front_exp,
                "back_expiry": back_exp,
                "front_dte": front.dte,
                "back_dte": back.dte,
                "front_iv": front_iv,
                "back_iv": back_iv,
                "sigma_fwd": ( (back_iv**2)*(back.dte/365.0) - (front_iv**2)*(front.dte/365.0) ) \
                             / ((back.dte-front.dte)/365.0) ** 0.5,
                "forward_factor": ff,
                "structure": "sell front, buy back, same strike (calendar)"
            })

    # rank strongest dislocations first
    signals.sort(key=lambda x: x["forward_factor"], reverse=True)
    return signals
```

---

## What to watch out for (bad signal prevention)

### 1. Units and consistency

* Ensure vols are in decimals, not percent. A 25 percent IV must be 0.25.
* Use the same vol definition for both expiries: same strike or same delta. Do not mix ATM with 35 delta, etc.

### 2. DTE handling

* Use actual calendar days to expiry, not trading days, and convert by 365.0.
* Be careful around holidays or half days that can shift DTE by 1 day and change (FF) slightly. Best practice is to recompute daily and require stability (see item 8).

### 3. Negative or tiny forward variance

* If (V_{\text{fwd}} < 0), discard. This usually means data errors, crossed markets, or stale quotes.
* If (V_{\text{fwd}}) is extremely small, the denominator in (FF) makes the ratio explode. Put a floor, e.g. require (\sigma_{\text{fwd}} \ge 0.05) (5 percent) or another sensible minimum for your universe.

### 4. Event contamination

* Earnings, FDA decisions, major economic releases, or known binary events between (T_1) and (T_2) can inflate front IV and produce a false "edge" that is actually priced risk.
* Filter out any ticker with a scheduled event in the window. If you can compute ex-earnings IV, use that instead.

### 5. Liquidity and microstructure

* Use mid quotes for IV, not last trade.
* Require:

  * tight bid ask on both expiries (IV spread or option price spread below a threshold),
  * sufficient volume and open interest,
  * no obvious quote staleness (timestamp checks).
* Thin names often show artificial backwardation.

### 6. Strike selection for the trade

Signal detection can be ATM based, but execution should be at a tradable strike:

* same strike calendar (classic),
* double calendar or 35 delta skew variants only if your bot also models skew correctly.
  If your signal uses ATM vol but you trade a skew strike, your realized edge can diverge.

### 7. Carry effects

Dividends, borrow costs, and early exercise risk affect calendar pricing even if IVs look clean.

* For American options on high dividend names, front calls can be exercised early. Adopt rule to avoid front calls near ex-div dates, or trade puts / European style where possible.
* If you incorporate rates and dividends, you can adjust to forward price based ATM.

### 8. Stability filter

Require the dislocation to persist:

* Example: (FF \ge \theta) for 2 consecutive data pulls or across a 10 to 30 minute window.
  This kills one tick spikes.

### 9. Pair selection

Not all tenor gaps behave the same. Keep to fixed windows you have tested, such as:

* 30 vs 60, 30 vs 90, 60 vs 90 DTE bands.
  Define tolerance bands, like front in 25 to 35 days and back in 55 to 70 days, etc.

### 10. Universe and regime

Backwardation is normal in some regimes (market stress) and some products (levered ETFs, meme names).
Consider a regime filter if you want fewer trades:

* only trade if market vol index below some level,
* or size down when broad vol is spiking.

---

## Output of your bot

For each signal, store and emit:

* ticker
* front expiry, back expiry
* front DTE, back DTE
* (\sigma_1, \sigma_2, \sigma_{\text{fwd}})
* (FF)
* liquidity metrics used for filtering
* event flags (earnings between expiries yes/no)
* timestamp and data source

That gives you auditability when a trade works or fails.