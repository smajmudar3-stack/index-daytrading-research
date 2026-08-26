# 17 — Prediction markets: the closest approach to the theoretical ceiling

**Status:** complete · **Evidence quality:** high — Kalshi public API pulled
directly (2,059 series), fee schedule retrieved from the actual PDF · **Relevance:**
**the best P(10×) route found in the entire project** — and it corrects two of my
own claims

---

## The headline

| route | **P(10×)** | vs fair bound |
|---|---:|---|
| **fair-bet theoretical bound** | **10.00%** | — |
| **Kalshi single bet, INX/NDX** (half fee) | **9.67%** | −0.33pp |
| **Kalshi single bet, general** | **9.40%** | −0.60pp |
| Kalshi two-leg parlay | 9.09% | −0.91pp |
| warrant basket | ~5% | −5pp |
| **equity options, MEASURED** | **1.39%** | **−8.6pp** |

> **Kalshi's fee drag on this specific objective is only 0.3–0.6 percentage
> points.** That is remarkably cheap, and it puts this route within a third of a
> point of the theoretical maximum — against **1.39%** for the equity-option
> route we measured.
>
> **A 7× improvement in P(10×) over buying calls.**

**This is not an edge.** It is the cheapest available way to take a *fair* bet.
Which is precisely what this project has been converging on: the entire
contribution has been moving from 1.39% toward the 10% ceiling. This gets to 9.67%.

---

## ⚠️ Two things I told you that were wrong

### 1. The p(1−P) fee does NOT favour cheap contracts — it is inverted

Verified formula (Kalshi fee schedule, effective 2026-02-05):

```
taker fee = ceil(0.07 × C × P × (1−P))
S&P 500 (INX*) and NASDAQ-100:  ceil(0.035 × C × P × (1−P))   ← half price
settlement fee: ZERO
```

The absolute fee *is* tiny at 3¢. But the quantity that matters is fee **as a
fraction of capital staked**: `k·P(1−P)/P = k(1−P)` — **monotonically decreasing
in P.**

| price | fee % of stake | INX/NDX |
|---|---:|---:|
| 3¢ | **6.79%** | 3.40% |
| 10¢ | 6.30% | 3.15% |
| 50¢ | **3.50%** | 1.75% |

**Cheap contracts are ~2× MORE expensive per dollar staked, not less.** I stated
the opposite.

Also new: **index markets are half price (0.035)** — not previously accounted for
anywhere in this bank.

*(Round-up-to-next-cent is brutal below ~100 contracts — a 1-lot at 3¢ pays a 33%
fee.)*

### 2. The optimal contract is ~9.5¢, NOT 3¢

This is Föllmer–Leukert applied **correctly**, and I applied it wrong.

The theorem says buy the digital that pays **exactly the target**. A 3¢ contract
returns **31×** when you only need 10× — so to hit exactly $50k you deploy only
**$1,602 and leave $3,398 idle.**

> **P(10×) at 3¢ ≈ 3.2% — three times worse than the 9.4% at the optimal price.**

**The "cheap convexity" instinct is wrong on its own theory** — the same instinct
the far-OTM data already killed, reappearing in a new venue. Fewer legs also
strictly beats more, consistent with everything else in the bank.

---

## What's actually there

**2,059 series** pulled live. Financial underlyings confirmed: `KXINXU/INXU`
(S&P above/below, hourly and daily), `KXINX*` ladders, `KXNASDAQ100*`,
`KXBTCD`/`KXBTC15M`, `KXCPI`, `KXFEDDECISION`, `KXPAYROLLS`, FX, and Treasury
spreads (`KX10Y2Y`).

**Liquidity is the binding constraint, and it splits sharply:**

- **`KXFEDDECISION` is genuinely deep** — 2.77M contracts offered at 1¢, ~$47k of
  depth, OI 678k. **$5,000 deploys easily.**
- **Index hourly ladders are thin** — ~1,000 contracts at 1¢ ($10), then 20,000 at
  3¢ ($600).
- **Exit is largely impossible on the wings: 65% (`KXINXU`) and 81%
  (`KXNASDAQ100U`) of sampled wing contracts had NO BID AT ALL** 30 minutes before
  close. **You are locked to settlement.** For a one-shot goal that is tolerable —
  but you cannot cut.

## Is it beatable? No evidence that it is

The agent measured Kalshi directly rather than citing racetrack literature: 125
far-OTM contracts bought at ~1.4¢ produced **zero payoffs** against ~1.9 expected.
P(0 wins | fair) ≈ 0.15 — **directionally consistent with longshots being
overpriced, not statistically significant.** Classic favourite-longshot runs
−5% on favourites vs **−40% on longshots**, and nothing reverses that for
financial contracts.

**No documented gap versus option-implied probabilities was established.** The
Breeden–Litzenberger arithmetic is sound, but risk-neutral tail probabilities
legitimately exceed physical ones and the agent could not quantify how much of
any gap that explains. **Unresolved, not favourable.**

The agent also flagged its own deep-ITM calibration bucket as implausible
(realised 0.32–0.52 where it should be ~0.95) — stale hourly candles on
short-lived markets. **Treat the calibration as suggestive, not established.**

## Tax: genuinely contested

**For:** §1256 covers a "nonequity option" = "any listed option which is not an
equity option," and Kalshi is a CFTC-designated contract market.
**Against:** these are fully collateralised and **not** marked to market with
variation margin, so they may fail the regulated-futures-contract definition.

**Unresolved, and worth 38–108% of stake if it goes the right way.** Resolve
before committing capital — but note it only matters if you win.

---

## The honest verdict

**The instrument is right and the fee is cheap. There is no evidence the prices
are beatable.**

Every number here is conditional on *"if pricing is fair"* — in which case this is
a fair coin, no better than any other fair 10× route and strictly worse than the
10% bound. The one weak empirical signal points the **wrong** way.

**But that is exactly the point.** Nothing in this project was ever going to beat
a fair coin. The question has been how close you can get to one, and the answer is
now:

| | P(10×) |
|---|---:|
| buying equity calls | **1.39%** |
| **Kalshi at ~9.5¢, INX/NDX** | **9.67%** |

**If this route is taken, it is a single all-in bet at ~9.5¢ in a deep book**
(`KXFEDDECISION`-style macro, or an INX/NDX contract for the half fee) — **not a
portfolio of 3¢ lottery tickets.**

## Unresolved

Whether §1256 applies · whether a properly aligned calibration study (minute
candles, per-market) finds real longshot mispricing · Polymarket's state-level
position (federally legal today; Nevada and Massachusetts suits live, Minnesota
ban effective 2026-08-01).
