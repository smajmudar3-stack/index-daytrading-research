# Fifteen ways a backtest lies

Seven of these produced *fake winning strategies* in this repo before being
caught. Check every new backtest against this list before believing it.

---

## The seven that actually faked a win here

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

## 5. One extreme day faking a whole matrix of effects

Found 2026-08-24, and it nearly passed. A full intraday predictability matrix on
SPY showed **12 of 78** half-hour bucket pairs beating the multiple-testing
threshold, when noise predicts ~0.2. Top pair 13:00 -> 15:00 at **t = +7.45**.

It was a single session: **2025-04-09**, the tariff-pause rally.

| test | pairs beating threshold | top pair |
|---|---:|---|
| all days, Pearson | 12 / 78 | 13:00 -> 15:00, t = +7.45 |
| drop 2025-04-09 | 10 / 78 | 11:00 -> 13:00 |
| drop 5 largest-range days | 3 / 78 | 13:30 -> 15:30 |
| **Spearman rank** | **1 / 78** | consistent with noise |

**The tell is that the top pair changes identity at every step.** A real effect
does not reshuffle when you remove one day. The mechanism: on a violently
trending day every half-hour bucket moves the same way, so one observation
injects correlation into *many* pairs simultaneously -- which also explains why
13:00 appeared in three of the top four pairs with inconsistent signs.

**Fix:** report Spearman alongside Pearson on any correlation-based signal
hunt, and check leave-one-day-out sensitivity before believing a t-stat.
Dropping the single largest |x| took t from +7.45 to +0.84 here.

---

## 6. Measuring a breakout from before the breakout

Found 2026-08-24. Opening-range breakout on SPY/QQQ, 2024-2026. Measuring the
move from the 10:00 close to the session close, conditioned on which side broke
first, gave **+23.06 bp/trade at t = +5.35** on QQQ.

Entering at the break level -- the first moment the signal exists -- gave
**+5.74 bp at t = +1.36**.

| | from 10:00 | at the break | contamination |
|---|---:|---:|---:|
| SPY | +13.19 bp (t 3.80) | +1.18 bp (t 0.34) | **91% of headline** |
| QQQ | +23.06 bp (t 5.35) | +5.74 bp (t 1.36) | **75% of headline** |

The break is *defined* by price reaching the range boundary, so conditioning on
"broke up" guarantees the leg from 10:00 up to the high already happened. That
leg is unavailable to a trader and pays the backtest anyway.

**Fix:** entry price must be the level that triggers the signal, never an
earlier reference point. This generalises to every threshold-triggered rule --
VWAP crosses, band breaks, stop-outs.

---

## 7. Symmetric conditional accuracy is volatility, not direction

The single cheapest diagnostic in this repo. ES 5-minute opening-range breakouts
reach a 1.0x extension **64.3% of the time upward and 62.9% downward**. Quoted
alone, "64% hit rate" reads as a directional edge. Quoted beside its mirror
image it is obviously a statement about how far price travels.

**Fix:** run every conditional statistic in both directions. If the two numbers
are close, the statistic contains no directional information, however high it
is. A directional edge is a large *one-sided* gap.

Beware the reverse error too: our own mirror test showed a +14.8pp / +16.1pp
"excess over base rate" in both directions, which looked like a two-sided edge
and was mechanical -- price cannot close above a level it never traded through,
so the unconditional base rate is not a valid control for a breakout.

---

## The other eight

**8. Conditional accuracy ≠ expected return.** "Right 70% of the time" says
nothing about profit if the 30% are larger. Always measure expectancy.

**9. Whole-group transforms are look-ahead.** Normalizing, ranking or
winsorizing across the full sample uses future data. Transform within the
training window only.

**10. Calendar annualization.** Annualizing by elapsed time a signal that fires
~5×/year inflated CAGR by more than 2×. Annualize by exposure, not wall clock.

**11. Duplicate trades.** Two DTE targets resolving to the same expiry
double-counted: 153,340 → 147,350 after dedup.

**12. Mid-price fills.** The single largest source of fake edge in options
backtesting. Enter at ask, exit at bid, or the result is fiction.

**13. Multiple testing.** Expected best |t| under the null is ≈ √(2·ln N). Test
200 variants and a |t| of 3.2 is the *expected* maximum from noise alone. Use
Deflated Sharpe (Bailey & López de Prado).

**14. Bin-width sensitivity.** If a result changes when you change bucket
boundaries, it is a binning artifact, not a signal.

**15. Fixed strike vs delta-based selection.** A fixed % moneyness is a
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
