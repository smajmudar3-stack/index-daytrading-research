# Research Bank — the $5k → $50k project

Every research agent's findings land here as a standalone report. **Nothing gets
backtested until the bank is complete** — that is the discipline the user asked
for, and it exists so that testing happens against the full picture rather than
against whichever idea arrived first.

## The goal (revised 2026-08-25)

Turn **$5,000 into $50,000 ONCE**. Total loss of the $5k is acceptable. It does
not need to be repeatable or consistent. After $50k, only 10–15%/year is needed.

This is a **bounded-downside convexity** problem, not a steady-edge problem, and
it is scored by **P(10x)** — not by expected return or Sharpe, which rank
strategies differently.

## Status

| # | domain | status |
|---|---|---|
| 1 | Kelly, leverage, ruin math | ✅ `reports/01_kelly_ruin.md` |
| 2 | GitHub repos with high-return claims | ✅ `reports/02_github_repos.md` |
| 3 | Verified track records & base rates | ❌ failed 2x — search budget exhausted |
| 4 | Small-account capacity-constrained edges | ❌ failed — **highest priority to retry** |
| 5 | Forums & practitioner communities | ✅ `reports/03_forums_communities.md` |
| 6 | Vol arb, dispersion, Section 1256 | ❌ failed |
| 7 | Event-driven: where IV underprices | ✅ `reports/04_event_driven.md` |
| 8 | Blow-up forensics | ❌ failed 2x |
| 9 | Meta: find uncovered domains | ❌ failed 2x |
| 10 | Optimal betting to a target (bold play) | ❌ stalled — partially covered by `synthesis/tenx_baseline.txt` |
| 11 | Maximum-convexity vehicle selection | ❌ failed — **highest priority to retry** |

## Rules for this bank

1. **No testing until every report is in.** Partial synthesis biases toward
   whatever finished first.
2. Every claim carries its **evidence quality** — verified, measured, claimed,
   or asserted.
3. Every candidate strategy is scored by **P(10x)**, and separately by whether
   it survives the traps in `BUNDLE/02_findings/METHODOLOGY_TRAPS.md`.
4. Negative results are kept and weighted equally. They are the bulk of what has
   been learned and they define the boundary of what is possible.


## The baseline every candidate must beat

`synthesis/tenx_baseline.txt` — computed, not asserted.

**Martingale ceiling: P($5k → $50k) = 10.00% with a FAIR bet, under ANY
strategy.** Optional stopping makes this exact and unbeatable; bet sizing cannot
improve it. Negative expectancy only lowers it.

### Bold play beats diversification here — the sign of expectancy decides

| bets | each must return | e=0% | e=−15% | e=−30% |
|---|---|---|---|---|
| 1 | 10.00x | 10.00% | **8.50%** | **7.00%** |
| 3 | 2.15x | 10.00% | 6.14% | 3.43% |
| 10 | 1.26x | 10.00% | 1.97% | 0.28% |
| 20 | 1.12x | 10.00% | 0.39% | 0.01% |

With negative expectancy, **every additional trade pays the house again**. This
is the exact opposite of the diversified-basket logic that applies to a steady
edge, and it follows from Dubins & Savage on subfair games.

### But the sign flips the whole strategy

| vehicle | per-trade | 1 bet | 3 bets | 10 bets |
|---|---|---|---|---|
| far-OTM held to expiry | −90.0% | 1.00% | 0.01% | 0.00% |
| far-OTM, spread ≤20% | **+5.6%** | 10.56% | 11.78% | **17.24%** |
| 16–30 delta band | **+26.1%** | 12.61% | **20.05%** | — |

**A vehicle with positive expectancy makes MORE bets better, not worse.**

So the entire strategy structure hinges on one question: do the two
positive-expectancy measurements survive scrutiny? If yes, the answer is many
small convex bets. If no, it is one large one. **This is the first thing to test
when the bank is complete** — the two designs are opposites and cannot be hedged
between.


## Blocker (2026-08-25)

**The session-wide web-search budget is exhausted.** Agents are failing with
"Search budget is exhausted for the session" and stream watchdog stalls.
Relaunching now fails immediately, so no further agents until the quota resets —
the 21:37 cron will pick this up.

**4 of 11 reports are in, and they are the four that matter most for calibration.**
The two highest-value gaps are:

- **04 capacity-constrained small-account edges** — report 01 concluded this is
  the *only* structurally promising direction, because the binding constraint at
  elite Sharpe is capacity, not risk, and a $5k account faces no capacity limit.
- **11 maximum-convexity vehicle selection** — the empirical base rate of a 10x
  by delta × DTE, which is the number that decides everything.

## Open audit item

Our in-house earnings-straddle result (**−35.03%, t = −95.7**) is contradicted by
Milian (2023, *JRFM*, peer-reviewed): **mean +0.48% (n.s.), median −17.69%**. A
t-stat of −95.7 on a fat-tailed near-zero-mean distribution is implausible unless
the exit convention is systematically costly. **Audit before anything is built on
it** — and it is currently published in `BUNDLE/02_findings/` and on GitHub.
