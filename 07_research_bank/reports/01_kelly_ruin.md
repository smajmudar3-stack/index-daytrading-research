# 01 — Kelly, leverage, ruin, and the arithmetic of extreme returns

**Status:** complete · **Evidence quality:** derivation from established theory,
cross-checked two ways · **Relevance to 10x goal:** defines the yardstick

---

## The identity that governs everything

> **g_max = S² / 2**

Maximum compound growth depends **only on Sharpe**. Leverage is already
optimised inside it. More leverage moves you *down* this ceiling, never up.

| Sharpe | max %/month at ANY leverage |
|---|---|
| 0.5 | 1.0% |
| 1.0 | **4.3%** |
| 2.0 | **18.1%** |
| 2.51 | 30.0% |
| 3.0 | 45.5% |
| 7.0 (Medallion est.) | 670% |

**At Sharpe 1.0 or 2.0, 30%/month is not "risky" — it is unreachable at every
leverage that exists.**

The minimum Sharpe for a target is `S_min = √(2·g_T)`, and it occurs at exactly
**full Kelly** — no margin for error anywhere.

## Ruin depends on k, not on edge

Running fraction `k` of full Kelly, the Sharpe **cancels**:

> **P(wealth ever falls to fraction x) = x^(2/k − 1)**

A better edge does not buy safety. It buys the ability to hit the target at a
*smaller* k, which is where safety comes from.

At the minimum viable Sharpe of 2.51 (k = 1.0, full Kelly): **50% chance of ever
halving, 20% of ever losing 80%, 17.5% of blowing up within 12 months** — and
that is *if the edge is real and known exactly*.

## Double Kelly earns zero

```
g(L) = L·μ − L²σ²/2 ;  L* = μ/σ²  ;  g(2L*) = 0  ;  g(L) < 0 for L > 2L*
```

Worked example (μ=10%, σ=20%): at 5× leverage the *expected* return is 50%/yr and
the *realised* compound return is **0.00%**. At 10×: expected +100%/yr, actual
**−63%/yr**.

**Arithmetic expected return rises linearly with leverage forever; realised
compound return peaks at L\* and is back to zero at 2L\*.**

## The luck identity — the most important result for this project

> **max P(hit target | ZERO edge) = Φ(−S_required)**

The probability of faking it is the normal tail evaluated at the Sharpe you would
need to do it honestly.

For 23.3x in a year: Φ(−2.51) = **0.605%**.

Seed a population of pure gamblers with **no skill whatsoever**:

| population | post a 23x year on pure luck |
|---|---|
| 1,000,000 | **6,048** |

…while **63% of that same population is down 90%+**. The winners are guaranteed
to exist, are indistinguishable ex-post from skill, and are the ones posting
screenshots.

## Why you cannot verify an edge in time

`SE(Ŝ) ≈ √((1 + S²/2)/T)`

| track record | 95% CI around a measured 2.51 |
|---|---|
| 1 year | **[0.54, 4.48]** |
| 3 years | [1.37, 3.65] |
| 10 years | [1.89, 3.13] |

A one-year Sharpe of 2.5 is statistically consistent with **0.5**. And expected
*maximum* Sharpe from N pure-noise backtests on one year of daily data:
N=100 → **2.53**; N=1,000 → **3.26**. The required number sits precisely where
search noise lands for free.

## The 53% win-rate case, with costs

At p=0.53 even money: `f* = 0.06`, `g = 0.18%/trade`. To make 30%/month needs
**146 full-Kelly trades per month at zero cost**.

| round-trip friction | net edge | trades/month needed |
|---|---|---|
| 0% | 6.00% | 146 |
| 2% | 4.00% | 328 |
| 5% | 1.00% | **5,232** |
| **6%** | **0.00%** | **no bet size is profitable** |

A $0.05 spread on a $2.00 0DTE option is ~5% round trip — **83% of the entire
edge**. A 53% direction edge is destroyed by options friction before sizing is
even a question.

## Benchmark reality

| | ann. return | %/month |
|---|---|---|
| **Medallion 1988–2018 GROSS** | 66.0% | **4.31%** |
| Medallion net to insiders | 39.0% | 2.78% |
| Medallion best year ever (2008) | 98.2% | 5.87% |
| Thorp, personal, 28.5 yrs | 20.0% | 1.53% |
| Buffett 1965–2024 | 19.6% | 1.50% |

## What is actually achievable

At quarter-Kelly (median lifetime max drawdown 9.4%):

| Sharpe | who has this | %/month |
|---|---|---|
| 1.0 | solid systematic strategy | **1.84%** |
| 1.5 | top-decile quant fund | 4.19% |
| 2.0 | elite multi-strat | **7.56%** |

**Realistic ceiling at acceptable ruin risk: 2–4%/month for a genuinely good
strategy; 7–13%/month only at institutional-elite Sharpe 2.0.**

---

## What this means for the $5k → $50k goal

The only real lever is buried in `S = s·√N`:

> **g_max = s²N / 2** — growth is **linear in the number of independent bets**
> and **quadratic in per-bet edge quality**. Leverage does not appear.

**The genuine ray of hope, in the agent's own words:** at Sharpe 7, quarter-Kelly
would theoretically yield 144%/month, yet Medallion delivers 4.3%. The binding
constraint at elite Sharpe is **not risk — it is capacity**. That is why Medallion
caps assets, returns profits annually, and closed to outsiders in 1993.

**A $5,000 account faces none of that.** If a high-Sharpe niche survives
anywhere, it survives *because* it is too small for institutions to bother with.
That is what report 04 (capacity-constrained edges) is hunting, and this analysis
says it is the correct place to look.

## Caveat the agent flagged deliberately

Every ruin number assumes lognormal returns, continuous rebalancing, and a
*known* edge. All three favour the trader. Real options books have jump risk,
non-stationary edges, and estimation error. **These are upper bounds on your
safety, not estimates of it.**

## Sources

MacLean/Thorp/Ziemba (2010) *Good and bad properties of the Kelly criterion* ·
Peters & Gell-Mann, *Evaluating gambles using dynamics* (Chaos 2016) ·
Lo (2002) *The Statistics of Sharpe Ratios* · Bailey & López de Prado,
*The Deflated Sharpe Ratio* · ESMA CFD data (74–89% of retail accounts lose) ·
Chague/De-Losso/Giovannetti (2019) — 97% of Brazilian day traders persisting
past 300 days lost money.
