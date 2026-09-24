# The stress book — buying the biggest losers, only while VIX is above 25

**Written 2026-09-24.** The one thing in the 68-factor accuracy sweep
(`signal_accuracy.md`) that cleared a 52% hit rate did so in a regime, not a factor:
short-term reversal in a stressed tape. Study: `05_studies/regime_reversal_test.py` on the
same panel (643,687 name-weeks, 2,200 optionable names, 2018–2026, close ≥ $10 and
$10m/day, excess over SPY from the next open). Live: `04_live_system/stress_reversal.py`,
paper, with a ledger.

## The trade

Composite = mean rank of last-month return, last-week return and 20-day Bollinger position.
Buy the bottom of it (the biggest losers). Hold 5, 10 or 21 sessions. Only when the tape
is stressed.

## Why it is allowed to run on 34 dates

Because it is not a pattern found by searching: it is the published reversal-liquidity
mechanism (Nagel 2012, *RFS*, "Evaporating Liquidity": short-term reversal profits are the
price of providing liquidity and are predicted by VIX; abstract not fetched this session,
publisher 403s), and because it passes every robustness cut without tuning:

| regime (known at the time) | hold | dates | excess / hold | t | hit | payoff | net of 15 bp/side | splits A / B / C |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **VIX > 25** | 5 | 70 | +0.83% | 1.7 | 0.544 | 1.26 | +0.53% | +0.94 / +0.55 / +0.94 |
| **VIX > 25** | **10** | **34** | **+1.55%** | **2.0** | **0.550** | **1.30** | **+1.25%** | **+0.93 / +1.83 / +1.68** |
| **VIX > 25** | 21 | 16 | +3.76% | 2.8 | 0.551 | 1.51 | +3.46% | +4.50 / +2.66 / +3.13 |
| VIX top 30% of its year | 10 | 68 | +1.16% | 2.5 | 0.544 | 1.20 | +0.86% | +1.78 / +2.03 / +0.48 |
| SPY < 200-day MA | 10 | 45 | +1.32% | 2.1 | 0.558 | 1.18 | +1.02% | +1.45 / +1.45 / +1.20 |
| SPY 12-month < 0 | 10 | 35 | +1.04% | 1.7 | 0.525 | 1.14 | +0.74% | +3.40 / +0.42 / +1.38 |
| *out of regime (control)* | 10 | 187 | −0.01% | 0.0 | 0.482 | 1.06 | −0.31% | flat / negative |

Robustness on the VIX > 25, 10-session row: liquid names only ($25m/day) +1.58% (t 2.8);
the bottom **40 names** instead of the decile **+2.59% (t 2.6), hit 0.562, payoff 1.42,
splits +0.92 / +3.66 / +3.75**; at 30 bp a side +0.95% net; positive in every year that
had an on-week (2018, 2020, 2021, 2022, 2025, 2026). The "crash names" variant (down more
than 10% in the week, VIX > 25, 21-session hold): +4.36% (t 2.0), hit 0.56, all splits
positive. The same composite OUT of the regime: −0.01% per hold, hit 0.48, −8 to −13%/yr
net. The switch is the whole result.

## What it is and is not

- **It is on about 16% of weeks.** VIX closed above 25 in 2018Q4, 2020, briefly 2021, most
  of 2022, and a handful of weeks in 2025–26. The rest of the time the book is off and says
  so. A 25%-a-year-when-on figure is not 25% a year.
- **Hit rate 55–56%, wins 1.3–1.4× losses.** The best accuracy anywhere in this repo, and
  still a book of 40 names, not a call on one.
- **Costs are higher when it is on.** Spreads widen in stressed tapes; the 30 bp row is the
  honest one for a retail account, and it still clears.
- **Sample.** 34 non-overlapping dates at ten sessions, 16 at twenty-one. The splits and the
  four regime definitions are the defence, and the ledger is the test.

## The live book

`stress_reversal.py` runs in the daily cycle: reads ^VIX; if the last close is above 25 and
no cohort was issued in the last five sessions, prices the discovered universe (~1,550
names, batched), screens price and volume, ranks the composite, issues the bottom 40, and
the ledger fills each at the next open, marks against SPY, closes after ten sessions.
Overlapping cohorts are expected. It places nothing. Panel on the Markets view:
"Stress book". On 2026-09-24 VIX was ~17: **the book is off**, which is the correct state
and the state it will be in most of the time.
