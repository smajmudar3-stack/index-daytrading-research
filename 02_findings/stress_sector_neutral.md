# The stress book is a name trade, and ranking against the sector makes it worse

**Verdict (2026-10-24).** Ranking the stress reversal on each name's price relative to its
own sector ETF earns **+1.32% per ten-session hold (t 1.6)** against **+1.88% (t 2.3)** for
the raw composite on the same rows, the same dates and the same universe, and it is weaker
at every hold and under every regime definition. Yet hedging the raw picks with their
sector ETFs keeps **+1.58% (t 2.4)**, and the picks' sector ETFs held alone make **+0.31%
(t 0.9)**. So the money is in the names, not the sector; the sector part of the signal
helps choose the names; and the live book keeps the raw ranking. Weak, not null: the
sector-neutral book is still positive in the regime and flat outside it, it is just the
same trade with a third of the edge removed. Strategy tree node `stress-sector-neutral`.

Found on the way, and larger than the result: **the house signal panel has a hole in the
four crash weeks of 2020.** `ohlcv.parquet` carries rows for ~3,400 symbols on 2020-02-17,
Presidents' Day, and none for the other 70%; the panel's 20-day rolling features were
built on a calendar that includes that session, so `bb_pos`, `vol21` and `rsi14` are NaN
for 92% of names from 2020-02-21 to 2020-03-13. The stress book's three-signal composite
needs `bb_pos`, so on those weeks the house measurement picked its bottom 40 from the 108
names that had a phantom row. Trap 17 in `METHODOLOGY_TRAPS.md`. On a clean calendar
the house **+2.59%/hold restates as +1.88%** (current constituents; the full-universe
rebuild is the first child below). The gap splits cleanly: the panel's composite on this
same universe makes +2.37% on 32 dates, so the sector map's survivorship is worth 0.2
points and the hole 0.5 — and the hole is not noise: the two ten-session dates the panel
cannot fill, 2020-02-28 and 2020-03-13, are the raw book's worst date (−13.9%) and one of
the crash weeks, so the house number was measured with the trade's worst fortnight left
out.

Reproduce: `05_studies/stress_sector_neutral_test.py` (~8 minutes; the panel, the price
file, the GICS map, nothing else).

## What was tested

Universe: the 1,471 names of `signal_panel.parquet` that are current S&P 1500 constituents
with a GICS sector (`opt_panel/gics.parquet`), 498,734 name-weeks, 2018-01 → 2026-08,
close ≥ $10 and $10m/day. Sector ETFs: the eleven Select Sector SPDRs from `ohlcv.parquet`
(XLC from 2018-06). Calendar: a session counts only if 70% of the names have a row, which
drops 2019-08-23, 2019-09-17 and 2020-02-17. Signals: 1-month return, 1-week return and
20-day Bollinger position, computed once on the name's close (raw) and once on the name's
close divided by its sector ETF's close (sector-relative), each ranked per date and
averaged. Book: the bottom 40 by the composite on a date with VIX > 25, filled at the next
open, held 5 / 10 / 21 sessions, non-overlapping dates. P&L over SPY, or over the name's
own sector ETF where stated, both from the next open. Costs 30 bp a side. Splits A 2019–21
/ B 2022–23 / C 2024–26. 39 cells scored; noise bar √(2 ln 39) = 2.71.

## The table (VIX > 25, bottom 40, ten sessions, 34 dates)

| arm | per hold | t | hit | payoff | date-hit | net at 30 bp/side | A / B / C |
|---|---:|---:|---:|---:|---:|---:|---|
| **A raw composite, over SPY** | **+1.88%** | 2.3 | 0.566 | 1.25 | 0.62 | +1.28% | +0.45 / +3.15 / +2.06 |
| A' the house number as measured (panel composite, full 2,200-name panel) | +2.58% | 2.6 | 0.561 | 1.42 | 0.68 | +1.98% | +0.91 / +3.65 / +3.75 |
| A° the panel's composite on this universe (32 dates: the panel cannot fill a book on 2020-02-28 or 03-13) | +2.37% | 3.2 | 0.577 | 1.42 | 0.62 | +1.77% | +1.42 / +3.08 / +2.06 |
| B raw composite, over the name's own sector ETF | +1.58% | 2.4 | 0.560 | 1.22 | 0.68 | +0.98% | +0.77 / +2.07 / +1.79 |
| C the sector ETFs of A's picks, over SPY | +0.31% | 0.9 | 0.523 | 1.14 | 0.50 | −0.29% | −0.32 / +1.08 / +0.27 |
| **D sector-relative composite, over SPY** | **+1.32%** | 1.6 | 0.565 | 1.08 | 0.68 | +0.72% | +0.38 / +1.66 / +2.29 |
| E sector-relative composite, over own sector ETF | +1.14% | 1.5 | 0.546 | 1.13 | 0.65 | +0.54% | +0.58 / +0.90 / +2.44 |
| F raw composite, at most 8 names per sector | +1.40% | 2.0 | 0.554 | 1.17 | 0.71 | +0.80% | +0.56 / +1.85 / +1.85 |
| G raw composite, bottom 4 of every sector (44 names) | +1.06% | 1.6 | 0.532 | 1.17 | 0.68 | +0.46% | +0.47 / +1.54 / +1.27 |
| control: A out of regime (187 dates) | +0.31% | 1.4 | 0.501 | 1.11 | 0.51 | −0.29% | +0.56 / −0.18 / +0.38 |
| control: D out of regime | +0.15% | 0.7 | 0.493 | 1.09 | 0.48 | −0.45% | +0.35 / −0.20 / +0.19 |

The same ordering at the other holds. Five sessions (70 dates): A +0.94%, D +0.77%,
C +0.14%. Twenty-one sessions (16 dates): A +3.43% (t 2.2), B +2.73% (t 2.5), D +2.55%
(t 1.9), C +0.92% (t 1.2). Under the other regime definitions at ten sessions, A beats D
every time: VIX in its top 30% +1.46% (t 2.8) vs +1.08%; SPY below its 200-day +1.91%
(t 2.9) vs +1.45%; SPY 12-month return negative +1.24% vs +0.75%.

Robustness. A and D choose 70% of the same names on the median date. Leave-one-date-out
at ten sessions: dropping A's best date (2022-09-23, +14.6%) leaves +1.50% (t 2.0);
dropping D's best (2018-12-21, +8.0%) leaves +1.12% (t 1.4); both arms' worst date is
2020-02-28 (−13.9% and −16.0%). The raw book's largest sector is a median 30% of the 40
names, at most 62–68% (energy on 2022-06-24, consumer discretionary on 2022-05-20,
technology on 2022-07-01); Herfindahl 0.19 against 0.09 for an equal spread. Concentrated,
never a single-sector bet, and arm C says the concentration earns little on its own.

No VIX > 25 cell clears this study's noise bar of 2.71; two of the alternative-regime raw
cells do (t 2.8 and 2.9). That is the same standing the parent had: the defence of the
stress book is the four regime definitions, the three holds and the switch against the
out-of-regime control, not any one t.

## What it rules in and out

- **Out:** ranking the stress book on sector-relative returns. It removes a third of the
  edge and a third of the t, under every regime definition and at every hold. A name that
  fell with its sector is as good a buy in a stressed tape as one that fell alone, and the
  raw composite already knows that.
- **Out:** per-sector caps and per-sector quotas (F, G) as improvements. Both are lower
  than A. The cap costs little (+1.40% vs +1.88%) if concentration is a risk the account
  cannot carry, but it is a cost, not a gain.
- **In:** the raw book, hedged or not. Hedging each pick with its sector ETF gives up 30 bp
  of mean per hold and raises the date-hit from 0.62 to 0.68 and the t from 2.3 to 2.4.
  For a paper ledger that is a free second mark; for a real account it is eleven short ETF
  lines and borrow, which is why it is a child branch and not a change.
- **In, and urgent:** the clean-calendar rebuild of the signal panel. Every rolling feature
  in `signal_panel.parquet` is missing for 92% of names across the four weeks the stress
  book most needs to be right about, and `signal_accuracy.md`, `regime_reversal_test.py`
  and the stress rows of `play_structures_test.py` all read that panel. The honest
  in-regime number is nearer +1.9% a hold than +2.6% until that rebuild says otherwise.

## Children on the tree

- `stress-clean-panel` — rebuild `signal_panel.parquet` on the names' calendar (drop any
  session with under 70% of names, `min_periods` 15 on every rolling feature), re-run
  `regime_reversal_test.py` on the full 2,200-name universe; the house +2.59% is the number
  under test and +1.88% the prior; re-price the `play_structures` stress rows on it.
- `stress-sector-hedged-ledger` — `stress_reversal.py` records each pick's sector ETF at
  issue and the ledger reports P&L over SPY and over the sector ETF side by side; measured
  +1.58% (t 2.4, date-hit 0.68) hedged against +1.88% (t 2.3, 0.62) unhedged.
- `stress-idio-within-sector` — the bottom 40 of the raw composite that are ALSO in the
  bottom 30% of the sector-relative composite (fell more than their sector did), VIX > 25,
  ten sessions, against the raw bottom 40; the 30% of picks the two rankings do not share
  is the cell this isolates.

Nothing here places an order.
