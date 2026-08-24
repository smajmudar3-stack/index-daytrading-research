# Twelve ways a backtest lies

Four of these produced *fake winning strategies* in this repo before being
caught. Check every new backtest against this list before believing it.

---

## The four that actually faked a win here

### 1. Capital-at-risk that ignores naked legs
A jade lizard showed **+800%/year** and a **−1.8-billion%** drawdown in the same
run. The denominator was computed from strike width, which silently treats a
naked short leg as if it were defined-risk.

**Fix:** evaluate the true payoff across a terminal-price grid and detect
unbounded loss explicitly. `max_loss_at_expiry()` in `scripts/structure_lab.py`.

### 2. Survivorship in the exit chain
A liquidity screen (`bid > 0.02`) applied at *exit* deletes options that expired
worthless — which is to say, it deletes the losers. Produced 100% win rates.

**Fix:** the liquidity screen may be applied **only at entry**. Entry and exit
need separate universes.

```python
ch_exit  = ch[ch.ask >= ch.bid].copy()          # no bid floor
ch_entry = ch[(ch.bid > 0.02) & (ch.ask > ch.bid) & (ch.open_interest > 5)]
```

### 3. Overlap leak
`resid.shift(1)` against a 5-day forward return shares 4 days with the outcome.
Produced **t = +13**. After correcting to `shift(H)`, the effect went *negative*.

**Fix:** shift by the full horizon. Sample non-overlapping trades — overlapping
samples inflate t by roughly √H.

### 4. `pct_change` pad-filling
Pandas' default `fill_method` carries a price across a ticker's pre-inception
NaNs and fabricates a return out of nothing. Hit XLRE and XLC.

**Fix:** always `pct_change(n, fill_method=None)`. The `pch()` helper in
`scripts/swing_lab.py` exists solely to make this the default.

---

## The other eight

**5. Conditional accuracy ≠ expected return.** "Right 70% of the time" says
nothing about profit if the 30% are larger. Always measure expectancy.

**6. Whole-group transforms are look-ahead.** Normalizing, ranking or
winsorizing across the full sample uses future data. Transform within the
training window only.

**7. Calendar annualization.** Annualizing by elapsed time a signal that fires
~5×/year inflated CAGR by more than 2×. Annualize by exposure, not wall clock.

**8. Duplicate trades.** Two DTE targets resolving to the same expiry
double-counted: 153,340 → 147,350 after dedup.

**9. Mid-price fills.** The single largest source of fake edge in options
backtesting. Enter at ask, exit at bid, or the result is fiction.

**10. Multiple testing.** Expected best |t| under the null is ≈ √(2·ln N). Test
200 variants and a |t| of 3.2 is the *expected* maximum from noise alone. Use
Deflated Sharpe (Bailey & López de Prado).

**11. Bin-width sensitivity.** If a result changes when you change bucket
boundaries, it is a binning artifact, not a signal.

**12. Fixed strike vs delta-based selection.** A fixed % moneyness is a
different amount of risk in different volatility regimes. Select by delta.

---

## Two unit traps that cost real time

- **`^TNX` is already in percent.** Dividing by 10 made every yield 10× too
  small. Legacy convention, wrong for this feed.
- **Daily betas ≠ horizon betas.** XLU's beta flips sign between them: +0.83
  daily, **−1.52** at 5 days. Compute beta at the horizon you trade.

---

## The process trap

Silent no-op edits happened **four-plus times** — an edit targeting an anchor
that doesn't exist reports success and changes nothing. `refresh_signal.refresh()`
was reported fixed while never actually running. `decide_direction()` was written,
wired into nothing, and reported as live.

**Rule adopted:** assert the anchor text exists before claiming an edit
succeeded, and verify the new code path actually executes — not that the file
contains it.
