# Black Swan / far-OTM lottery strategy — what the testing found

Tested on **real SPY option quotes 2008–2025**: bought at the **ask**, held to expiry,
settled at intrinsic. Options that expired worthless count as **−100%** and are never
dropped — filtering the exit chain by `bid > 0` deletes exactly the losers and is the
single most dangerous bug in this domain.

**10,535,928 option purchases** in the unconditional test.

---

## 1. The core result — the mean gets WORSE the further OTM you go

| Bucket | Kind | n | win% | **MEAN** | median | best single |
|---|---|---|---|---|---|---|
| ultra <2 delta | call | 10,082 | 0.4% | **−90.0%** | −100% | +16,350% |
| 2–5 delta | call | 9,216 | 2.5% | **−48.5%** | −100% | +10,125% |
| 5–10 delta | call | 8,442 | 8.1% | **−12.1%** | −100% | +11,480% |
| 10–16 delta | call | 7,051 | 17.3% | **+4.7%** | −100% | +4,281% |
| 16–30 delta | call | 12,989 | 30.7% | **+26.1%** | −100% | +3,420% |
| ultra <2 delta | put | 28,312 | 0.3% | **−75.4%** | −100% | +33,358% |
| 2–5 delta | put | 18,087 | 0.8% | **−46.6%** | −100% | +26,162% |
| 16–30 delta | put | 24,036 | 10.8% | **−33.1%** | −100% | +6,199% |

**The mean improves monotonically as you move CLOSER to the money.** The "buy the
cheapest contracts" instinct is precisely backwards. And the huge winners are real —
+16,350% exists — they are simply not frequent enough to cover the rest.

**Calls beat puts at every delta.** Puts are negative in every bucket; the market's
upward drift plus the put skew (crash insurance is permanently bid) means you pay a
premium to be short the market that never gets refunded.

### As a $100 portfolio spread over 20 contracts

| Bucket | median outcome | mean | P(basket > 1.0) | P(> 2x) |
|---|---|---|---|---|
| ultra <2 delta | **0.00x** | 0.10x | **2.9%** | 1.2% |
| 2–5 delta | **0.00x** | 0.52x | 21.2% | 7.0% |
| 5–10 delta | 0.65x | 0.91x | 34.8% | 10.8% |
| 10–16 delta | 0.95x | 1.04x | 46.5% | 8.2% |
| 16–30 delta | **1.22x** | 1.27x | **66.5%** | 8.1% |

At the strikes described (~$1 contracts, ultra-far OTM), **$100 becomes $0 in the median
case and the basket beats break-even 2.9% of the time.**

---

## 2. Why: the spread is worst exactly where the contracts are cheapest

Measured on real SPY quotes, 20–60 DTE, OI > 10:

| Delta | Median price | **Round-trip spread** |
|---|---|---|
| <0.02 | $0.06 | **22.2%** |
| 0.02–0.05 | $0.16 | 8.7% |
| 0.05–0.10 | $0.43 | 4.3% |
| 0.10–0.16 | $0.94 | 2.8% |
| 0.16–0.30 | $2.00 | 1.8% |

A cheap contract is not cheap exposure — it is expensive exposure in small units. And
this is **SPY, the most liquid options market on earth**; single-stock far-OTM spreads
run several times wider (measured earlier: single-stock median 4.51%, worst 13.7% ATM).

---

## 3. Selection does NOT rescue it — the central hypothesis, falsified

The claim worth testing was not "far-OTM is bad" but "far-OTM plus good selection is
good": find names about to move where IV hasn't priced it. Four conditions, all knowable
at entry, each compared against the SAME delta bucket unconditionally:

| Bucket | Condition | n | MEAN | baseline | **EDGE** |
|---|---|---|---|---|---|
| 2–5d call | IVRANK_LOW | 10,294 | −52.2% | −57.1% | +4.8% |
| 2–5d call | SQUEEZE | 3,067 | −62.4% | −57.1% | **−5.4%** |
| 2–5d call | IV_UNDER_RV | 7,890 | −57.0% | −57.1% | +0.0% |
| 10–16d call | IVRANK_LOW | 12,505 | +17.1% | +30.1% | **−13.0%** |
| 10–16d call | SQUEEZE | 3,195 | +17.8% | +30.1% | **−12.3%** |
| **2–5d put** | **IVRANK_LOW** | 669 | **−95.4%** | −41.8% | **−53.6%** |
| **2–5d put** | **IV_UNDER_RV** | 231 | **−100.0%** | −41.8% | **−58.2%** |
| 5–10d put | IV_UNDER_RV | 660 | −85.3% | −42.4% | −42.9% |
| 10–16d put | SQUEEZE | 8,627 | −74.3% | −40.2% | −34.1% |

**Every meaningful selection made it worse.** The one bucket with a positive
unconditional mean (10–16 delta calls, +30.1%) got *worse* under every single condition.

**The mechanism is the important part.** "IV is cheap" is not an opportunity — it is
information. The option market is cheap precisely when nothing is about to happen, and
it is right often enough that buying cheapness is buying a correct forecast of quiet.
Selecting for low IV on puts is catastrophic: −95.4% and −100.0% mean.

---

## 4. Taleb does not support this strategy — his own work argues against it

From primary text (`RESEARCH_TALEB.md`):

- **He never claims far-OTM options are underpriced.** *Tail Option Pricing Under Power
  Laws* (arXiv:1908.02347), co-authored with Spitznagel, explicitly disclaims it: *"our
  approach isn't about absolute mispricing of tail options, but relative to a given
  strike closer to the money."* It is a **relative-value spread**, not an outright buy.
  The Fourth Quadrant claim is that tail probabilities are **unknowable** — which cannot
  ground an edge in either direction.
- **The barbell's work is done by the SAFE sleeve**, not the convex one. Taleb: *"if
  someone has 80% of his portfolio in numéraire securities, the risk of losing more than
  20% is zero."* Spitznagel concedes the tail sleeve is *"sort of like paying an
  insurance premium"* and is justified only by raising the **geometric** return of a
  portfolio you already own.
- **The geometric-mean argument is mathematically sound but the window is narrow** —
  it breaks past roughly −0.4%/yr of drag, and measured real-world index put-buying drag
  is **−2.3%/yr** (Hoffstein, 2005–2020, a window containing both 2008 and March 2020).
  Six times too expensive in the most favourable sample obtainable.
- **The value comes from correlation with your own catastrophe, not from convexity.**
  Same sleeve, same cost: crash-timed +0.08% CAGR (helps), idiosyncratic −0.33% (hurts).
  **Scattered single names structurally cannot have that property.**
- **Taleb's own tail trade is entered for a NET CREDIT** (*Dynamic Hedging* pp. 264–65):
  buy OTM in size, financed by selling smaller amounts of ATM, *"making sure the trade
  satisfies the 'credit' rule."* The plan inverts the cash flow of the trade it copies.
- **Empirica Capital — Taleb and Spitznagel's own fund running this — closed in 2004**
  after a quiet market bled it out. That is the base rate, and it happened to the
  inventors with institutional backing.
- Taleb's option work is **entirely index-level (SPX)**, never scattered single names.
  Spitznagel's own words on strategies like Universa's: *"but please don't try any of
  this at home, folks."*

**Ilmanen (FAJ 2012), citing Boyer & Vorkink:** the most positively-skewed **single-stock**
options — the exact instrument proposed — returned **−30% to −60% per WEEK** at
midmarket. Not per year. Before spreads.

**Denominator flag:** Universa's famous "4,144% in Q1 2020" is a return on *invested
capital* (premium deployed), not committed capital. There is **no public audited return
series for Universa at all.**

---

## 5. The least-bad version, if the idea is pursued anyway

The data does point somewhere, just not where the strategy aimed:

1. **10–16 delta CALLS, not 2–5 delta, and not puts.** It is the only bucket with a
   positive mean (+4.7% at 10–16d, +26.1% at 16–30d) and the basket beats break-even
   46–67% of the time rather than 2.9%.
2. **Do not select on cheap IV.** Every cheapness filter reduced the mean. If anything,
   the unconditional version is the best version.
3. **Index, not scattered single names** — that is where Taleb's argument actually lives
   and where spreads are 3–6× tighter.
4. **Enter as a spread for a credit**, per Taleb's own rule, rather than paying premium
   out of pocket.
5. **Size it as an overlay on a portfolio you own**, not as the portfolio. The geometric
   -mean benefit only exists relative to something being protected.

---

## 6. THE SPREAD *IS* THE STRATEGY — the most useful refinement

Measured independently on 123,107 real far-OTM trades from the DoltHub single-stock
chains (0.10 delta, 35 DTE, bought at ask, settled at intrinsic):

| Universe | Mean | t |
|---|---|---|
| All far-OTM | **−45.6%** | −7.13 |
| **Spread <= 20% of mid** | **+5.6%** | **+0.98** |

**The entire negative expectancy is the bid-ask spread.** Filtered to genuinely
tradeable contracts it becomes a coin flip rather than a bleed. But **70% of the
far-OTM universe sits above 60% relative spread**, so the filter throws away most of
the candidates — which is exactly why the strategy fails in practice rather than in
theory.

All five cheapness screens (IV rank, HV-IV, compression, HV/HV-high, IV momentum) came
back flat; the best was Goyal-Saretto at t = 1.92.

## 7. WHY EARNINGS SPECIFICALLY FAILED — the cleanest explanation found

Earnings raise **P(move > 2 sigma) from 3.86% -> 4.96%**, but **LOWER P(move > 3 sigma)
from 1.00% -> 0.91%**.

**Earnings are a 2-sigma generator carrying a 3-sigma price. Far-OTM needs 3 sigma.**
That single line explains the measured −35.03% (t = −95.7) better than anything else:
the move does arrive, it is simply smaller than what the option charged for, and the
7.1-point IV crush collects the difference.

## 8. TWO DATA LANDMINES IN THE DOLTHUB SET — read before building on it

1. **`stocks.ohlcv` is UNADJUSTED.** NVDA runs 1208 -> 121 across its split. Any return
   computed naively across a split date is fiction.
2. **33% of the split table is DUPLICATE ROWS.** GOOG's 20:1 appears twice, compounding
   to an adjustment factor of 400. Applied naively this turned a −45.6% strategy into
   **+199.6%**, with the top 10 trades supplying 95% of P&L — and the "best trade" was
   +4,836% on a GOOG call that in reality expired worthless.
   **Fix: validate every claimed split against the actual price gap before applying it.**

Confirmed good news on the same dataset: **the chain is survivorship-free** — ATVI, SIVB,
FRC and TWTR all terminate on their real delisting dates rather than being back-filled
out of existence.

## 9. Still open

Two agents running at time of writing: lottery-option academic literature
(`RESEARCH_BLACKSWAN.md`) and move-prediction / repo sweep
(`RESEARCH_MOVE_PREDICTION.md`). The one genuinely untested angle is
**event-conditioned convexity** — buying cheap options *before a known catalyst with a
date* (earnings, FDA, index rebalance) rather than screening for "quiet stocks". Gao,
Xing & Zhang (JFQA 2018) find delta-neutral straddles earn **+2.3% from one day before
an earnings announcement to the announcement**. The DoltHub single-stock chains plus the
117k-event earnings calendar make that directly testable, and it is the version of this
idea with actual literature behind it.
