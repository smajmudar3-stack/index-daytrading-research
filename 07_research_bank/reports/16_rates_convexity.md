# 16 — Rates convexity: the premise was factually wrong

**Status:** complete · **Evidence quality:** high — verified contract specs, FRED
exact, Minneapolis Fed MPD dataset (14,293 rows) · **Relevance:** ties the 1.39%
base rate, does not beat it

---

## The flag was wrong on its core premise, twice

**Claim:** rates are bimodal and policy-driven, so a *lognormal*-fitted option
price is wrong in an identifiable direction.

1. **CME prices these on Bachelier (normal), not lognormal** — moved in April
   2020 to handle negative rates. The market does not fit a lognormal to a
   bimodal underlying.
2. **A normal distribution has a *thinner* far tail than a lognormal.** If
   anything the far wing is priced *more* conservatively.

## The cheap contract is the trap, not the feature

The "$12.50–$50 per contract" claim is **true — and that is what kills it.**

| premium | moneyness | delta |
|---|---|---|
| ~$12.50 | 225–270bp OTM | **0.1–0.6Δ** |
| ~$124 | 112bp OTM | 10.6Δ |
| ~$897 | ATM | 50Δ |

**Two arithmetic killers:**

**Tick floor.** Minimum quotable price is **$6.25**. At 270bp OTM the Bachelier
fair value is **$0.86** — you cannot pay less than $6.25, so you **overpay 7.3×**
for the deepest wing. *The grid manufactures richness in exactly the strikes the
thesis wants.*

**Commissions scale with contract count, not premium.** IBKR $0.85/contract plus
~$1–1.60 fees:

| approach | contracts for $5k | round-trip cost | **as % of stake** |
|---|---:|---:|---:|
| $12.50 far wing | **400** | $700–1,600 | **14–32%** |
| $124 at 10Δ | 40 | $70–160 | 1.4–3.2% |

**The cheap-contract approach costs 10× more in commission for the same stake.**

## The P(10x) curve is the same shape as equities

Bachelier, σ=90bp, 1y, net of tick grid and fees:

| moneyness | delta | premium | **P(10×)** |
|---|---|---|---:|
| 1.00σ | 15.9Δ | $187 | 3.17% |
| **1.25σ** | **10.6Δ** | **$124** | **3.59% ← max** |
| 2.00σ | 2.3Δ | $19 | 1.64% |
| **3.00σ** | **0.1Δ** | $12.50 floored | **0.11%** |

Equity lognormal comparison: peak **3.81% at 14.7Δ**, far wing **0.13%**.

> **The two curves are nearly identical.** The distributional difference the flag
> rests on is worth essentially nothing. Deep OTM in rates is dominated by
> **33×** — *worse* than equities' 6×, because of the tick floor.

The optimum sits at **9.5–11.3 delta in every vol regime and tenor tested.**

## The Fed's own data says the wing we want is RICH

Minneapolis Fed MPD (Breeden-Litzenberger on Treasury futures options and
caps/floors), ~600 dates 2013–2026, implied vs realised:

| instrument | implied | realised | ratio |
|---|---:|---:|---:|
| **ZN 3m, yield −71bp (rally)** | 4.42% | 3.87% | **0.88× RICH** |
| ZN 3m, yield +71bp (selloff) | 5.06% | 6.13% | 1.21× |
| **ZF 3m, rally** | 6.13% | 5.03% | **0.82× RICH** |

**The rates-rally wing — exactly what this thesis wants to buy — has been priced
12–18% rich relative to realised frequency over 13 years.**

## And the fat tail is on the wrong side

| | excess kurtosis (p90) | skew |
|---|---:|---:|
| **LR3y3m** (the midcurve) | **+24.16** | **+1.21** |
| SPX 12m | +3.3 | −1.28 |

Two things follow: the market **already prices the midcurve as extremely
fat-tailed** — the "policy jump" is in the quoted smile and you pay for it — and
**the fat tail is on the rates-UP side.** The rally side is bounded by the zero
lower bound and is the **thin** wing.

Pre-COVID confirmation: on 2020-02-19 the market already priced LR5y3m prDec at
**47.8%** with kurtosis +30.5. **Not a cheap lottery ticket — a crowded
consensus.**

## What actually happened in the three dislocations

| episode | outcome |
|---|---|
| **March 2020** | genuinely ~50–100× on 1y deep-OTM ED calls — driven by a **volatility** mispricing (50bp implied vs >150bp realised) at a **36-year return-period** event |
| **March 2023 (SVB)** | 15–20× mark-to-market in ~10 days, then **every one of those calls expired worthless** — the Fed did not cut until Sept 2024 |
| **2024** | nothing; the 100bp of cuts was pre-priced |

**One of three paid. One paid only if you sold within ~10 days. One didn't.**

Any backtest of "buy the wing, hold to expiry" scores March 2023 as **−100%**.

## Frequency: the 10× move basically doesn't happen

Non-overlapping 3-month windows, 2Y CMT, 1990–2026 (n=145):

| move | frequency | return period |
|---|---:|---|
| 2Y falls ≥50bp | 16.6% | ~1.5 yrs |
| 2Y falls ≥100bp | 6.9% | ~3.6 yrs |
| **2Y falls ≥150bp** | **0 of 145** | **never since 1990** |

The 10× at the optimal strike needs **~162bp** in 12 months. The top eight
3-month rallies ever are **all Volcker-era**; the post-1990 record is −186bp
(2007–08).

**A continuous ladder burns ~$18,000 to catch one ≥100bp event.** One shot is
structurally the correct way to play it — which happens to be the situation here.

## Untradeable at $5k in the wing

The **$6.25 tick is the floor on the bid-ask** — it cannot be tighter.

| option | one-tick spread | + commissions | **total friction** |
|---|---:|---:|---:|
| $12.50 (0.1Δ) | **50%** | 14–32% | **40–130%** |
| $124 (10Δ) | 5% | 1.4–3.2% | **6–13%** |

**Say it plainly: the specific trade the flag recommended is not available to a
$5,000 account.**

---

## What survives, and one genuine conditioning signal

**~10-delta SR3 or midcurve calls, 110–180bp OTM, 9–18 months, ~$120–180 each,
30–40 contracts.** P(10×) ≈ **3.6% model / ~1.4% friction-adjusted** — applying
the same 2.7× haircut that took the equity model's 3.81% down to a measured
1.39%.

**A tie, not a win.** Plus Section 1256 60/40, which is the largest *verifiable*
edge in the domain and improves the after-tax payoff without touching P(10×).

**The one conditioning signal with data behind it:**

| | |
|---|---|
| 2Y today | **4.70%** — genuine room to cut, unlike 2020's 1.58% ZLB cap |
| MPD rally wing | **3.01%** priced |
| MPD selloff wing | 6.12% priced |

**The wing we want is currently the cheap one.** Modest, but real and dated.

*Note the ZLB cap is load-bearing: in Feb 2020 the funds rate was 1.58%, so the
entire COVID rally was mechanically capped at ~155bp and every strike above
100.00 was worth zero regardless of how bad the world got.*

**Could not substantiate:** OIS-implied-vs-realised divergence, Fed dissent
counts, macro surprise indices as regime-break triggers. **Treat all three as
folklore.**

## Unverified

Live far-OTM SOFR bid/ask (Barchart login-gated) · CME settlement history for
exact realised multiples (CME IP-blocks scraping) · exact CME per-contract fees ·
whether IBKR lists midcurve options (product API returned 500 — **verify in TWS
before planning around it**). The March 2020/2023 multiples are reconstructions
from exact underlying moves plus modelled Bachelier premiums.
