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
| 3 | Verified track records & base rates | 🔁 relaunched (API error) |
| 4 | Small-account capacity-constrained edges | ⏳ running |
| 5 | Forums & practitioner communities | ✅ `reports/03_forums_communities.md` |
| 6 | Vol arb, dispersion, Section 1256 | 🔁 relaunched (died mid-response) |
| 7 | Event-driven: where IV underprices | ⏳ running |
| 8 | Blow-up forensics | 🔁 relaunched (API error) |
| 9 | Meta: find uncovered domains | 🔁 relaunched (spawned children, exhausted budget) |
| 10 | Optimal betting to a target (bold play) | ⏳ running |
| 11 | Maximum-convexity vehicle selection | ⏳ running |

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
