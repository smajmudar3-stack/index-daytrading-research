# The earnings variance risk premium — measured, and it holds

**Status: CURRENT. Measured 2026-09-06.** The first Unusual Whales input in this repo with a
history behind it rather than a prior.

## The question

`04_live_system/earnings_vol.py` reads a name's variance risk premium — the gap between what
options imply and what the stock goes on to do — against its own year, and says a high
percentile argues for selling the event rather than buying it. That is a plausible story, and
this repo's method is that a plausible story is worth nothing until it is measured.

## Why this one could be measured at all

Every other UW input in the vote (`flow_lean`, `dp_buy_share`, `insider_open_buys`) is served
same-day only. `signal_weights` tiers them "unmeasured" and says their weight is a prior that
can only be earned forward. Two endpoints break the pattern:

    /api/stock/{t}/volatility/variance-risk-premium   ~232 rows, a year of daily premium
    /api/earnings/{t}                                 report dates + expected_move_perc

The realised move is computed from daily closes already batched for the scan, because
`/api/earnings/{t}` leaves `pre_earnings_close` and `post_earnings_close` NULL even on reports
that already happened. Reading them returned zero usable events across all 90 names — a silent
zero indistinguishable from "no edge exists".

## The result

266 earnings events, 88 names, one year. Edge = implied move minus realised move, in points of
underlying. Positive means the option seller won.

| premium percentile before the print | n   | mean edge | median | t     | seller wins |
|-------------------------------------|-----|-----------|--------|-------|-------------|
| cheap (<= 25%)                       | 62  | −4.30pt   | −2.70  | −4.26 | 31%         |
| mid (25–75%)                         | 102 | +0.92pt   | +1.38  | +1.75 | 65%         |
| rich (>= 75%)                        | 102 | +3.63pt   | +3.69  | +9.07 | 79%         |

Monotone, and the spread from cheap to rich is +7.93pt.

## The check that mattered: is it tautological?

`t = +9.07` is well past the level where this repo treats a result as a bug until proven
otherwise. The specific worry is circularity: the premium is built from implied vol, and the
"edge" has implied vol on one side of it. A rich premium could simply mean a bigger implied
number, which would inflate the edge mechanically without forecasting anything.

Decomposing the two sides settles it:

| bucket | implied | realised | realised / implied |
|--------|---------|----------|--------------------|
| cheap  | 7.17    | 11.46    | 1.63               |
| mid    | 7.63    | 6.71     | 0.91               |
| rich   | 7.99    | 4.36     | 0.57               |

**Implied is nearly flat across the buckets. Realised is not.** The percentile is forecasting
the move that actually happens, not labelling the ones that were priced expensively. The ratio
difference is t = −6.49.

## Robustness

Three consecutive periods, because a signal that works in one period is a period:

| period                  | n  | rich edge | cheap edge | spread  | rich win rate |
|-------------------------|----|-----------|------------|---------|---------------|
| 2025-12-02 … 2026-03-02 | 87 | +3.23pt   | −2.05pt    | +5.28   | 80%           |
| 2026-03-02 … 2026-05-28 | 88 | +3.17pt   | −5.33pt    | +8.50   | 72%           |
| 2026-06-03 … 2026-09-02 | 88 | +4.24pt   | −6.14pt    | +10.38  | 84%           |

Costs: 65% of rich-bucket events stay positive after a 2.0pt round-trip haircut, 46% after
4.0pt.

## What this does NOT establish

- **The edge is in points of underlying move, not in option P&L.** A short condor capturing a
  3.65pt overprice does not return 3.65%. Converting it needs the payoff engine and the real
  bid-ask, and this repo has already measured condors at −0.25%/trade net of costs. The gross
  edge must survive the spread on names whose expected moves are 6–14%, which is where the
  quotes are widest.
- **One year.** Roughly four reports per name. The t-stats are strong but the calendar is short
  and covers a single vol regime.
- **The universe was the first 90 alphabetically** from the scan list. Arbitrary rather than
  chosen, but not a random sample.
- **It says nothing about direction.** It is a statement about the SIZE of a move, which is why
  it routes to structure selection and never into the directional vote.

## What it changes

An earnings date gives `market_basis` a non-directional basis, which is the only route to
`direction == "neutral"` and therefore the only way the iron condor, iron butterfly and long
straddle branches of `weekly_structures.menu()` can ever fire. This measurement is what tells
those branches which side of the trade to be on: rich sells the event, cheap buys it, fair
means the event is dated and the pricing is unremarkable.

Reproduce with `05_studies/earnings_vrp_test.py`.
