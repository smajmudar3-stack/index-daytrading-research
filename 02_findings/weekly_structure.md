# The weekly book's trade, replayed on seven years of real chains

**Status: CURRENT. Measured 2026-09-21.** Companion to `weekly_predictors.md`, which found no
usable weekly direction edge. This asks what the book's STRUCTURES and EXITS cost, and
whether any volatility read pays for them. Data: the Dolt EOD chains (2019-05 → 2026-08),
every leg at the ask when bought and the bid when sold.

Reproduce: `05_studies/xsec_vertical_test.py`, `05_studies/xsec_straddle_test.py`.

## 1. What a vertical costs with no edge

67,380 trades. Entries are the top and bottom decile of one-week reversal each week (a
signal that measured IC +0.015; the side matched the move to expiry 49.4% of the time, so
this is the no-edge case). Debit: long ~50-delta, short ~25-delta. Credit: short ~30-delta,
long ~15-delta. Expiry nearest 14 days. P&L as % of max risk.

| structure | exit | n | mean | median | win rate | t |
|---|---|---:|---:|---:|---:|---:|
| debit vertical | expiry | 38,024 | **−14.5%** | −95% | 37% | −26.8 |
| credit vertical | expiry | 28,890 | **−8.4%** | +11% | 73% | −33.8 |

Same in every split: debit −18.8 / −10.1 / −15.1, credit −8.8 / −8.3 / −8.1 (A/B/C).

Held to expiry there is no exit spread, so these numbers are the ENTRY bid-ask alone,
expressed as a share of the money at risk. A debit spread gives up a seventh of its risk
at the door; a credit spread a twelfth. The invariants hold: the 25-delta short leg
finished in the money 22.2% of the time, and no debit lost more than its debit.

The time-exit rows (5d / 10d at chain marks) came out at −40% / −17% but are BIASED and
are not results: the thinned chain keeps ~11 strikes around spot, so a leg is still quoted
a week later mostly when spot moved toward it — that selects losing credit spreads and
winning debit spreads. They are reported in the script as bounds only.

**What this fixes in the engine.** The ledger's −50% price stop on debit spreads fired on
70% of the first 129 cards, and cards whose direction was RIGHT still averaged −12.6%
because the stop took them out before they came back. A defined-risk debit does not need a
price stop; its risk is the debit. `_exits` now sets no `stop_net` on a debit structure —
the exits are the thesis (the invalidation price) and the calendar. Credit structures keep
the 2× stop, because their loss is not the credit.

## 2. Long single-name straddles, and the one month that made them look good

155,170 ATM straddles, nearest-30-day expiry, bought at the ask, held to expiry:

| | n | mean | median | win rate |
|---|---:|---:|---:|---:|
| all | 153,741 | +2.6% | −19.6% | 40% |
| **Feb 2020 alone** | 2,148 | **+392%** | +359% | — |
| excluding 2020 | 134,659 | **−3.2%** | −19.6% | 40% |

The whole positive mean is one month. Excluding 2020, long premium loses 3.2% of its cost
per ~30 days at the ask (weekly-mean t = −3.4). The mirror is the honest description of
selling single-name premium: about +3% a month gross, 60% of the time, against a month
that cost 392% of the premium. Defined-risk versions pay for the wings.

## 3. Does any volatility read sort the straddle returns? Weakly, and not robustly

D10 (the sort says vol is cheap: buy) minus D1 (rich: sell), long-straddle return over cost,
per-date deciles:

| sort | exit | D10−D1 | t | weeks positive | A | B | C |
|---|---|---:|---:|---:|---:|---:|---:|
| IV − 20d realised (the live engine's band) | expiry | +0.8% | 0.3 | 49% | −1.9 | +1.1 | +2.8 |
| IV − 252d realised (Goyal-Saretto) | expiry | +3.5% | 2.4 | 57% | +4.5 | +1.6 | +4.3 |
| IV − 252d realised | 1 week | +1.4% | 3.1 | 55% | +2.5 | +1.2 | +1.0 |
| term slope | expiry | +2.8% | 1.0 | 47% | +2.5 | +6.3 | +0.1 |
| straddle % of spot | expiry | −4.8% | −1.7 | 42% | −13.8 | +2.1 | −3.1 |

The Goyal-Saretto sort is the only one positive in every split on both exits. But it does
not survive a change of construction: bucketing the same names on the RATIO IV/RV252 at
fixed cutoffs (rather than per-date deciles of the difference) puts the least-negative
long-straddle return in the RICHEST bucket (>1.35×: −0.7%) and the most negative in the
cheapest (<0.85×: −4.4%). A result that reverses between two reasonable constructions is
trap #15 (bin sensitivity). Verdict: **not an edge to build on.** The live engine's own
band — IV against 20-day trimmed realised, the thing `IV_RICH_VS_RV = 1.15` gates on —
sorts nothing at all (t = 0.3).

## 4. The earnings premium, in option P&L: NOT reproduced with a proxy

`earnings_vrp.md` measured a +3.6pt seller edge on 266 events using the vendor's variance
risk premium percentile. Rebuilt here with a proxy (IV − HV from Dolt `volatility_history`,
percentile within the name's own trailing year) on 44,302 straddles whose expiry contains
the print:

| VRP percentile | n | long straddle to expiry | long straddle, 1-week exit (print ≤ 5d away) |
|---|---:|---:|---:|
| cheap ≤ 25% | 3,411 | −0.6% | −15.1% |
| mid | 17,501 | −2.2% | −13.1% |
| rich ≥ 75% | 22,605 | −1.4% | −12.6% |

Short-rich minus short-cheap: −2.0% (t −0.6) to expiry, −0.7% (t −0.2) on the 1-week exit.
Implied straddle 10.9% vs realised 11.2% in the rich bucket. **No seller edge, no buyer edge,
no ordering.** Either the vendor's own VRP series carries something the Dolt proxy does not,
or the 266-event, one-year result was a period. The vendor series can be re-pulled
(`05_studies/scripts/uw_history_pull.py`) once the quota allows; until then the finding's
status is "measured in points on one year, unconfirmed in option P&L on seven", and every
card that uses it says so.

## 5. What the book is, after all of this

| question | measured answer |
|---|---|
| which way? | no input ranks next week better than IC 0.02; a composite is right 52% |
| how far? | IV vs 20d realised sorts nothing; IV vs 252d weakly and not robustly |
| what does it cost? | 8.4% of risk (credit) / 14.5% (debit) per trade at 14 DTE, entry spread only |
| what survived? | VIX backwardation (index, all splits), post-earnings drift (small, all splits), the earnings premium read (one year, unconfirmed) |

So the engine now refuses a card that rests on nothing measured (`REQUIRE_MEASURED_BASIS`),
prints the structure's measured cost next to whatever basis it has, and stops out debits on
the thesis rather than on a mark. The book will be nearly empty most weeks. That is the
result, not a defect: **there is no configuration of this book, on this evidence, that turns
$5,000 into $50,000, and the honest expectation for a book that trades only on the measured
bases is a small number of cards a quarter.** The index overlay in `goal_feasibility.md`
(15%/yr at 2× with a high-50s drawdown) remains the best-supported thing in the repo.
