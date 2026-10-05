# The first 15 minutes — what the opening range says about the rest of the day

**Written 2026-10-05.** Sholo asked for the S&P 500 and Nasdaq-100 opening range, first 15
minutes, "how that affects the day, any patterns or edges". Measured on the tradeable
proxies (SPY, QQQ) with 1-minute bars, **554 sessions each, 2024-07-12 → 2026-10-02**
(the quant-factory store to 2026-07 plus the vendor's bars after it). Study:
`05_studies/opening_range_study.py`; per-session table in
`DATA_ROOT/opening_range_sessions.parquet`. The earlier breakout tests
(`influencer_report.md`, `orb_proper.py`: eight configurations, largest |t| 1.15, the taught
stop cuts the win rate from 52% to 37%) are not repeated; this is the wider question.

Everything below is measured from the 09:45 price, the first one available after the range
is known. 56 conditional cells were run across both proxies, so the largest |t| expected
from noise alone is about 2.8. Two years of minute bars allow about seven independent
configurations before an in-sample Sharpe of 1 is expected by chance.

## Verdict

- **Direction: nothing.** No conditioning on the first 15 minutes — its direction, where
  the 09:45 price sits in the range, the gap it opened on, its width or its volume — tells
  you the sign of the rest of the day with any reliability that survives the second year of
  the sample or a 2 bp round trip.
- **Volatility: real, and already the thing worth using.** The width of the first 15
  minutes forecasts the size of the rest of the day with t-statistics of 14 to 27 in both
  halves. That is not a direction edge; it is an input to how wide a 0DTE structure must be,
  and the one thing from this study that belongs in the live system.
- **Three facts about the day's shape** that any intraday rule has to live with are below.

## The shape of the day (both proxies, 554 sessions)

| fact | SPY | QQQ |
|---|---:|---:|
| the day's HIGH is set inside the first 15 minutes | 19% | 24% |
| the day's LOW is set inside the first 15 minutes | 21% | 25% |
| either extreme is set in the first 15 minutes (random: ~8%) | **41%** | **48%** |
| OR high broken before the close | 81% | 76% |
| OR low broken before the close | 79% | 75% |
| BOTH sides broken (whipsaw) | **59%** | **52%** |
| neither side broken | 0% | 0% |
| median minutes from 09:45 to the first break | **2** | **2** |
| first break within 5 minutes / within 30 | 71% / 98% | 70% / 97% |
| close above the OR, given the high broke first | 56% | 55% |
| close below the OR, given the low broke first | 51% | 49% |

Read together: the opening range is broken almost immediately on almost every day, both
sides are broken on more than half of days, and the side that breaks first ends the day on
its own side of the range only slightly more often than a coin flip. That is why a stop at
the other side of the range bleeds: it is inside the day's noise by construction. And on
four to five days in ten the first 15 minutes already contain the day's high or low, which
is the real reason "fade the open" and "follow the open" both feel right in hindsight.

## The conditionals

Rest-of-day return in basis points from 09:45 to the close; "signed" means multiplied by
+1 if the first 15 minutes closed up and −1 if down, so continuation reads positive.

| cell | SPY: all (t) · train · test | QQQ: all (t) · train · test |
|---|---|---|
| A. follow the first 15 min (signed), gross | +3.3 (0.97) · +8.4 · **−1.7** | +7.6 (1.75) · +16.8 · **−1.5** |
| …net of 2 bp a side | +1.3 (0.39) | +5.6 (1.29) |
| the fade, net | −5.3 (−1.55) | −9.6 (−2.21) |
| B. 09:45 close in the top third of the range | +2.1 (0.45) · +9.1 · −4.3 | +4.3 (0.70) · +8.8 · −0.4 |
| B. …bottom third | +4.6 (0.90) · +0.5 · +8.2 | −4.0 (−0.59) · −11.1 · +3.4 |
| C. gap down then first 15 min UP | +17.1 (1.40) · +39.2 · **−1.0** | +17.0 (1.33) · +33.2 · **−2.7** |
| C. gap up then first 15 min DOWN | −4.5 (−0.79) | −8.9 (−1.13) |
| E2. wide opening range, follow it (signed) | +5.7 (0.63) · +21.0 · **−10.3** | +21.8 (2.13) · +33.8 · +10.2 |
| F2. heavy opening volume, follow it (signed) | +6.4 (0.76) · +18.0 · **−6.5** | +16.0 (1.58) · +31.4 · **−2.2** |
| G. first break → close, from the break LEVEL, net | −1.2 (−0.37) · +3.4 · **−5.9** | +0.8 (0.20) · +8.8 · **−7.1** |

Every directional cell that looks alive in the first year is flat or negative in the
second. The best-looking one, QQQ's wide-range continuation at t 2.1, is one half-year:
+58 bp in 2025H1 (the April tariff tape) against +9 to +17 in the other four halves; on SPY
the same cell is +47 in 2025H1 and negative in every other half. The slippage sweep on the
simplest rule (follow the open on QQQ) goes from +7.6 bp gross to +2.6 at 5 bp a side and is
negative in the test half at every cost.

**Trap caught in the writing.** The first draft of cell G conditioned on "which side broke
first" but measured from the 09:45 price, and read t 2.5–2.9. The break happens after 09:45,
so 9–13 bp of the move from 09:45 to the break level is included in the outcome and cannot
be earned. Measured from the level that triggers the condition it is zero. This is trap 6
in `METHODOLOGY_TRAPS.md`, and it is the exact way the breakout literature reports its edge.

## What is real: the width of the open forecasts the width of the day

| OR width tercile | SPY OR width | SPY rest-of-day range | QQQ OR width | QQQ rest-of-day range |
|---|---:|---:|---:|---:|
| narrow | 18 bp | 0.80% | 32 bp | 1.12% |
| mid | 27 bp | 0.97% | 47 bp | 1.36% |
| wide | 46 bp | **1.36%** | 73 bp | **1.68%** |

t 14–27, both halves, both proxies; the same holds for opening volume (heavy-volume opens
run a 1.32% / 1.68% rest-of-day range against 0.87% / 1.19% for quiet ones). The mean
absolute rest-of-day move is 40 bp after a narrow SPY open and 69 bp after a wide one. This
is volatility predictability, which the repo already knows is two orders of magnitude more
forecastable than direction (`INTRADAY_DIRECTION.md`), and it arrives at 09:45, before the
0DTE desk's decision window. The 0DTE expected range on the Today page is set from the prior
close's gamma exposure; the opening-range width is the first in-session update to it and
the next thing to wire: a condor sized to a 0.94% expected range on a wide-open day is
sized to a day that will run 1.4%.

## What this does not change

The weekly engine, the stock books and the stress book are untouched: none of them trades
the open. The 0DTE index gates stay as they are. No direction rule from the first 15
minutes enters anything, and the registry's `gamma_direction` and `orb` nulls stand.
