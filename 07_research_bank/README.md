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

## Status — 2026-08-26

**6 banked · 8 running · 0 re-run unnecessarily.** Completed reports are never
relaunched; only failures were restarted.

### Banked — do not re-dispatch

| # | domain | report |
|---|---|---|
| 1 | Kelly, leverage, ruin math | `reports/01_kelly_ruin.md` |
| 2 | GitHub repos with high-return claims | `reports/02_github_repos.md` |
| 3 | Forums, communities, survivorship | `reports/03_forums_communities.md` |
| 4 | Event-driven: where IV mis-prices | `reports/04_event_driven.md` |
| 5 | Meta: fourteen uncovered domains | `reports/05_new_domains.md` |
| 6 | Crypto convexity + access | `reports/06_crypto_convexity.md` |
| 7 | **Warrants — first measured P(10x)** | `reports/07_warrants.md` |
| 8 | **Prop firms — first route to beat the ceiling** | `reports/08_prop_firms.md` |
| 9 | **Capacity edges — thesis killed** | `reports/09_capacity_edges.md` |

### Running — the original cycle, completed

| domain | history |
|---|---|

| Maximum-convexity base rates (delta × DTE) | failed 1× → **relaunched** |
| Optimal betting to a target (Dubins-Savage) | stalled 1× → **relaunched** |
| Vol arb, dispersion, **Section 1256** | failed 2× → **relaunched** |
| Verified track records & retail base rate | failed 3× → **relaunched** |
| Crash winners & strictly-bounded structures | failed 2× → **relaunched, reframed** |



All eight are instructed: **no subagents**, conserve searches, ~30–40 calls. The
earlier fleet died because the meta-agent spawned children and exhausted the
shared search budget.

### Not yet dispatched — remaining HIGH domains from report 05

Reflexive crypto-treasury equities (#1) · prediction markets as digital options
(#2) · option-writing ETF forced flows via N-PORT (#3) · SOFR/rates convexity
(#4) · structured-product barrier clusters (#5).

Report 05 flags **#1, #3 and #5 as one connected system** — forced option sellers
(#3) manufacture the cheap upside convexity in reflexive names (#1), while
structured-product barriers (#5) mark where the downside gap is mechanically
amplified. Dispatch together.

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


| 12 | Crypto convexity + access | ✅ `reports/06_crypto_convexity.md` |

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


## The two findings that survived contact so far

**1. Moderate delta beats the far wing — confirmed twice, independently.**

| study | asset | far wing | moderate delta |
|---|---|---|---|
| ours, 10.5M purchases | US equity | −90% | **+26.1% at 16–30Δ** |
| Almeida et al., 7.8M Deribit trades | BTC | small premium beyond ±60% | **38.7% of premium in [+20%,+60%]** |

Two asset classes, two datasets, same conclusion, and the crypto one comes with a
stated mechanism: **high IV ≠ negative expectancy when the underlying carries a
66%/yr risk premium**. This is the most robust result in the bank.

**2. Independent repeated trials may beat any single edge.**

The martingale ceiling — P($5k→$50k) = 10% — binds *one* sequence of bets.
Report 05's prop-firm domain offers **N independent attempts at bounded cost**,
which is a different problem. That reframing is worth more than any edge found so
far, and it went unexamined because the whole investigation was framed in options.


## Scoreboard — P(10x) by route

Every candidate must be measured against the **10% martingale ceiling**: with a
fair bet and optimal play, P($5k→$50k) = 10% exactly, and no bet sizing beats it.

| route | P(10x) | downside bounded? | evidence |
|---|---:|---|---|
| fair bet (theoretical ceiling) | **10.0%** | — | theorem |
| **warrant basket** | **~5%** (2–10%) | **yes — cash account** | measured |
| single warrant, 12m | 1–2% | yes | measured |
| warrants bought in the 2020–21 boom | **0.0%** | yes | measured |
| far-OTM options held to expiry | ~1% | yes | measured (10.5M purchases) |
| **Apex 20-account correlated cycle** | **14–45%** | **yes — fee only** | modelled; ⚠ counterparty |

**Only one route beats the ceiling, and it does so for a clean reason:** the 10%
bound binds when the payoff is funded by *your own stake*. A prop evaluation fee
is a call-option premium on **someone else's** drawdown allowance — roughly 50:1
free leverage, downside truncated at the fee. The ceiling simply does not apply.

**But its risk is not market risk.** Apex's own disclosure calls the payout
*"discretionary"*; the accounts are simulated, unregulated, and the $50,000 is an
unsecured payable from a private LLC. And the strategy that makes the math work —
correlated copy-trading, one-directional, no stop-loss — is reportedly the same
behaviour cited in past payout denials. **That single unverified fact is the
difference between a 30% plan and a 0% one, and it is the highest-value item
outstanding in the entire bank.**

Among routes where the counterparty is a market rather than a company, the
**warrant basket at ~5%** remains the best, and nothing yet beats a fair coin.

### Report 09 closed the direction report 01 called most promising

Report 01 concluded capacity was the reason a small account might beat
institutions. Report 09 shows the thesis is **half right and the wrong half is
fatal**: every small-capacity edge also has a capacity **FLOOR** set by the
$0.65/contract commission, the 100-share multiplier and combo spreads. The
window is **$100k to a few million — $5,000 is below it.** Hard-to-borrow
conversions are *negative* at $5k and *positive* at $500k.

The one-line reason: **"too small in dollars" and "large in percent" are nearly
incompatible.** That closes the branch, and it means the remaining live routes
are convexity (warrants, moderate-delta options) and someone else's capital
(prop firms) — not arbitrage.
