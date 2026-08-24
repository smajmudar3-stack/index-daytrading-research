# Weekly Iron Condors and 0DTE Iron Butterflies — What Is Actually Known

**Written:** 2026-08-06 · **Scope:** SPX/SPXW, XSP, SPY, QQQ
**Standing constraint:** every number below is labelled **REAL QUOTES** or **MODEL**. Nothing that came
out of a pricing model is quoted as evidence of profitability.

This report exists because of the failure documented in `FINDINGS.md` §1: a 0DTE iron condor gated on
prior-close dealer gamma showed **+3.7%/trade, 91% win, t=+7.4** when priced with Black-Scholes plus a
linear skew approximation, and **−1.70%/trade (t=−0.99)** when re-run on 1,919 sessions of real SPXW
bid/ask. The modelled credit was the entire edge. Every claim below has been held to that standard.

---

## 0. VERDICT

**Framing result (owner's own parallel run, real quotes, entries at ask / exits at bid, 147,350
de-duplicated structure-trades on SPY 2008–2025):** iron condor 30/16 → 48.6% win, **−15.83%/trade,
t=−17.5**; iron condor 16/05 → 63.6% win, **−10.54%/trade, t=−13.5**; iron butterfly ATM → 45.9% win,
**−13.83%/trade, t=−20.1**; and **1,001 regime-gated cells produced zero positives in all three
periods**. This report was produced independently and **replicates those results** on the same file
with separate code (§4.3): 30/16 condor 49.7% win / −8.14%/trade / t=−19.9; ATM butterfly 41.1% win /
−11.74%/trade / t=−20.4. The question this report answers is therefore not "do condors work" — the
answer is no — but **what, if anything, in the published record contradicts it, and under exactly what
conditions**.

### Weekly iron condors (5–10 DTE) on SPX/SPY/QQQ

**No credible evidence of positive expectancy after real costs.** The strongest cell found anywhere in
this study — SPY 10-delta shorts with 4%-wide wings, held to expiry — returns **+0.15% of capital at
risk per trade (t = +0.27)** on 662 *non-overlapping* weekly trades of real EOD bid/ask, 2008–2025.
At 5% of the account risked per trade that compounds to **CAGR +0.18%, Sharpe 0.07, max drawdown
−13.6%** over 17.7 years. It is a null, not an edge.

The same structure looks like an edge (+0.44%/trade, t=+2.64) if you allow overlapping entries — 7,977
trades on 4,514 dates. **The overlap *was* the t-statistic.** This is the same class of error as the
"conditional accuracy is not expected return" trap in `FINDINGS.md` §2.

Independent corroboration from the only listed benchmark: **Cboe's own iron condor index (CNDR) has
returned −1.28%/yr net of T-bills for 16.6 years (2010-01 → 2026-08), Sharpe −0.18**, with an alpha to
SPX of **−2.74%/yr**. Its entire positive 40-year record was earned before 2010.

### 0DTE iron butterflies on SPX

**No credible evidence of positive expectancy after real costs — and here the mechanism is fully
identified.** On 1,396 sessions of real SPXW quotes, the 0DTE ATM straddle is priced at **fair value**:
realised move / implied move = **0.978 to 1.007** across every entry time from 10:00 to 14:00, and the
short straddle earns **+0.3 to +0.9 bp of spot at the mid, t = 0.26 to 0.85**. There is no 0DTE
variance risk premium at the money to harvest. Adding wings makes it worse, because the wings are the
part of the surface you have to *pay* for.

Result: **all 36 (entry time × structure × wing width) cells are negative** once you cross the spread
once. Best cell: −0.48 bp of spot (t = −0.52). Not one positive cell anywhere.

The closest listed analogue confirms it: **Cboe's iron butterfly index (BFLY) returned −5.32%/yr net of
T-bills over 2010–2026, alpha to SPX −5.86%/yr, max drawdown −55%.**

### One-line summary

> The variance risk premium that makes short-vol famous lives in **naked/covered, monthly, out-of-the-money
> puts**. Buying a wing to define your risk gives away the exact part of the surface that carries the
> premium; compressing to 0DTE gives away the premium itself. An iron condor or butterfly is therefore
> a structure that pays away the premium twice and keeps only the transaction costs.

### The two failure modes are different, and conflating them causes bad fixes

This is the most useful analytical result in the report, and it reconciles two apparently competing
explanations ("there is no edge" vs "the spread eats it"). **Both are true, of different structures.**
Measured on real SPY EOD bid/ask (§4.3), mean % of capital at risk per trade:

| Structure | at the **mid** (zero cost) | after 8 **full**-spread crossings | Which failure? |
|---|---|---|---|
| Monthly condor 30Δ/16Δ | **−2.24%** | −8.14% | **Negative before costs.** Mispriced structure. |
| Monthly iron butterfly ATM/16Δ | **−4.86%** | −11.74% | **Negative before costs.** Mispriced structure. |
| Weekly iron butterfly ATM/16Δ | **−1.17%** | −8.40% | Negative before costs |
| Monthly condor 16Δ/5Δ | **+1.25%** | −1.20% | **Positive before costs, killed by the spread.** |
| Monthly condor 10Δ/5Δ | **+1.41%** | −1.22% | **Positive before costs, killed by the spread.** |
| Weekly condor 16Δ/5Δ | **+0.53%** | −1.48% | Positive before costs, killed by the spread |

**Near-the-money structures (30Δ shorts, ATM butterflies) lose money at mid prices.** No execution
improvement can save them; you are short the fat middle of the return distribution at a price that
does not compensate you. **Far-OTM structures (10–16Δ shorts) are mildly positive at mid and are
killed by the round trip.** Only those are worth arguing about, and the argument is entirely about
execution quality.

The practical consequence: "widen the wings / go further OTM / get better fills" is a coherent
research direction for the 10–16Δ condor and a **waste of time for the iron butterfly**, which is
broken before a single spread is crossed.

---

## 1. Methodology guarantees for the original work in this report

| Guarantee | What was done |
|---|---|
| **No pricing model** | Every P&L number produced here comes from quoted bid and ask. `mid = (bid+ask)/2`. No Black-Scholes anywhere. |
| **Slippage assumption** | The credit is taken at the mid and then **half the quoted bid-ask is charged on every leg** — 4 half-spreads to open. If the position is closed, 4 more. This is the standard "you cross half the spread" assumption and is *optimistic* relative to a retail marketable order on a 4-leg combo, and *pessimistic* relative to a patient limit order that gets mid-filled. Both directions are reported. |
| **Cash settlement** | SPX/SPXW 0DTE is cash-settled, so hold-to-expiry incurs **no exit cost**. This is a genuine structural advantage and it is credited in full. SPY is physically settled; exit cost is charged only when the structure finishes in the money. |
| **Fixed strikes, not fixed moneyness** | For path-dependent management, strikes are carried forward as fixed strikes (moneyness rescaled by S_entry/S_now), per the `FINDINGS.md` §3 warning. |
| **Independence** | Overlapping and non-overlapping versions are reported separately. The non-overlapping version is the one that counts. |
| **Degenerate rows guarded** | Condor short strikes forced non-inverted; trades where credit ≈ width (risk < 25% of width) dropped, since "% of capital at risk" explodes there. |
| **Win rate ≠ expectancy** | Both are reported in every table. Several rules below *raise the win rate and lower the money*. |

**Data used**

| File | Contents | Verified in this session |
|---|---|---|
| `data/spxw/data_opt.parquet` | 1.37M rows, 1,919 sessions 2016-09→2024-05, 30-min grid 10:00–16:00, moneyness grid 0.980–1.020 in 0.001 steps, mid/bid-ask/IV/greeks/OI. All prices are **fractions of spot at that quote time**. | **Confirmed genuinely 0DTE.** Tue/Thu session counts are 7/2 per year before 2022, jump to 38/34 in 2022 and 51/51 in 2023 — exactly matching Cboe's SPXW Tue (Apr 2022) and Thu (Sep 2022) expiry rollout. ~1,396 sessions have a full grid at any given time. |
| `data/opt_eod/SPY_options.parquet` | 24.7M rows, 2008-01→2025-12, real EOD `bid`/`ask`/`delta`/`IV`/`OI` per contract. | 6.24M usable rows at DTE 3–45 across 4,514 dates. |
| `data/opt_eod/QQQ_options.parquet` | same schema | not yet exercised — see §8 test spec T4 |
| Cboe daily index CSVs | CNDR, BFLY, PUT, WPUT, BXM, CMBO, SPX, downloaded live from `cdn.cboe.com/api/global/us_indices/daily_prices/` | 10,105 rows CNDR back to 1986-06-20 |

**Grid limitation to be aware of:** the SPXW moneyness grid spans only ±2% of spot. Structures whose
wings sit beyond 2% OTM cannot be tested on it, and on a >2% intraday move the legs are valued by
intrinsic. Roughly 2–3% of sessions are affected; they are all max-loss days for any structure with
wings inside 2%, so the approximation is conservative in the right direction.

---

## 2. WEEKLY IRON CONDORS (5–10 DTE)

### 2.1 The listed benchmark: Cboe's CNDR index — REAL, and it has been a 16-year loser

CNDR is Cboe's rules-based S&P 500 iron condor benchmark: it sells a monthly OTM SPX put spread and
OTM call spread and holds the collateral in one-month Treasury bills. **Because the T-bill yield is
inside the index return, the headline CAGR is not the strategy's return** — the option overlay's
contribution is the *excess* over T-bills. Computed from the daily index CSV against FRED DTB3:

| Window | CAGR | Vol | **Excess over T-bills** | **Sharpe** | Max DD |
|---|---|---|---|---|---|
| Full, 1986-06 → 2026-08 (40.1y) | 5.31% | 8.04% | **+2.10%** | **0.26** | −20.1% |
| 1986–2009 (23.5y) | 9.08% | 8.52% | **+4.48%** | **0.53** | −19.8% |
| **2010–2019 (10y)** | **−0.78%** | 7.18% | **−1.34%** | **−0.19** | −15.5% |
| **2020–2026 (6.6y)** | **+1.66%** | 7.45% | **−1.18%** | **−0.16** | −12.7% |
| **2010–2026 (16.6y)** | **+0.19%** | 7.29% | **−1.28%** | **−0.18** | −20.1% |

This **confirms and sharpens** the claim that condor selling on SPX has been a 15-year loser. The
sharpening is the T-bill decomposition: CNDR's apparently-positive +1.66%/yr in 2020–2026 is *entirely*
T-bill interest. The option strategy itself lost money in **both** sub-periods, not just the first.

Regressing daily excess returns on SPX excess returns:

| Era | CNDR beta to SPX | CNDR alpha | BFLY beta | BFLY alpha |
|---|---|---|---|---|
| 1986–2009 | 0.18 | **+4.07%/yr** | 0.16 | **+3.97%/yr** |
| 2010–2026 | 0.14 | **−2.74%/yr** | 0.05 | **−5.86%/yr** |

There genuinely *was* a harvestable premium in defined-risk index premium selling. It died around 2010
and has been negative for sixteen years.

**The same regression on the naked put-write indices is the most important control in this report:**

| 2010–2026 | Excess over T-bills | Beta to SPX | **Alpha** |
|---|---|---|---|
| PUT (monthly put-write) | **+6.42%/yr** (Sharpe 0.53) | 0.63 | **+0.01%/yr** |
| WPUT (weekly put-write) | +3.24%/yr (Sharpe 0.29) | 0.58 | **−2.84%/yr** |
| BXM (buy-write) | +5.85%/yr (Sharpe 0.47) | — | — |
| CNDR (iron condor) | **−1.28%/yr** | 0.14 | **−2.74%/yr** |
| BFLY (iron butterfly) | **−5.32%/yr** | 0.05 | **−5.86%/yr** |

Read that carefully. **PUT's excellent-looking +6.4%/yr excess return is 100% equity beta — its alpha is
exactly zero.** Since 2010 there has been no alpha in *any* of these index option-selling programmes.
The put-write versions are at least honest levered-down equity. The wing-buying versions are levered-down
equity *minus* the cost of the wings, which is why they are 2.7 to 5.9 percentage points a year negative.

*Caveat:* Cboe's published methodology PDF was not retrievable in this session (cdn.cboe.com returned
403 to every documented URL). The exact leg deltas and the roll pricing convention (mid vs VWAP vs
settlement) are therefore **not verified from primary source here**. What is verified is the daily index
level series itself, which is Cboe's own and is the basis for every number in this section. If the roll
is priced at the mid, real-world CNDR would be *worse* than shown, not better.

### 2.2 Weekly vs monthly: the WPUT/PUT mechanism, and why it transfers to condors

WPUT collects roughly 37%/yr of gross premium against PUT's ~22%, and has nonetheless earned **less**
for 20.5 years. On the excess-over-T-bills basis computed here, the gap is:

| Window | PUT excess | WPUT excess | Gap |
|---|---|---|---|
| 2010–2019 | +6.52% | +4.86% | −1.66pp |
| 2020–2026 | +6.26% | +0.79% | **−5.47pp** |
| 2010–2026 | +6.42% | +3.24% | −3.18pp |

Rolling 5-year gap (WPUT − PUT) ends the sample at **−4.7 to −5.8pp/yr**. The gap is real and widening.

Two mechanisms, and only one of them is an edge question:

1. **√T is an accounting identity, not an edge.** Option premium scales as √T, so 52 weekly rolls
   collect √52 ≈ 7.2× one annual premium while 12 monthly rolls collect √12 ≈ 3.5×. Collecting more
   gross premium at shorter tenor is arithmetic. It says nothing about expectancy.
2. **Re-striking at the market 52 times a year is the actual cost.** Each roll resets the short strike
   to the *current* spot. In a rising market the weekly seller repeatedly re-strikes upward into
   strength and gets caught by the next mean-reverting dip; a monthly seller rides through it. Plus
   4.3× the transaction events.

Both mechanisms apply *at least as strongly* to a 4-leg condor as to a 1-leg put-write, because the
condor has 4× the legs and therefore 4× the re-striking friction. **The WPUT/PUT result is the closest
available real evidence on the weekly-vs-monthly condor question, and it points the wrong way for
weeklies.**

### 2.3 Own test: SPY weekly vs monthly condors on REAL EOD bid/ask, 2008–2025

Entry at the EOD quote; credit at the mid, then 4 half-spreads charged; short strikes selected by
quoted `delta`; wings a fixed % of spot away; settled against the SPY close on the expiration date.

**Pass 1 — all valid (entry date × expiry) pairs. Overlapping, so t-stats are inflated.**
Returns are % of capital at risk (= width − credit).

| Structure | n | credit as % of width | 4 half-spreads as % of credit | 8 half-spreads as % of credit | win | at mid | **net of entry** | t(net) | net of round trip | worst |
|---|---|---|---|---|---|---|---|---|---|---|
| weekly 10Δ wing 2% | 7,977 | 7.5 | 4.3 | 8.5 | 84.3% | +0.65 | **+0.09** | 0.38 | −0.47 | −139% |
| **weekly 10Δ wing 4%** | 6,974 | 4.9 | 3.5 | 7.0 | 84.5% | +0.71 | **+0.44** | **2.64** | +0.16 | −118% |
| weekly 16Δ wing 2% | 8,006 | 13.4 | 2.6 | 5.3 | 75.6% | +0.21 | **−0.50** | −1.42 | −1.21 | −143% |
| weekly 16Δ wing 4% | 7,331 | 8.5 | 2.2 | 4.3 | 76.4% | +0.62 | **+0.29** | 1.29 | −0.03 | −121% |
| weekly 30Δ wing 2% | 8,015 | 29.7 | 1.5 | 3.0 | 59.4% | −1.29 | **−2.48** | −4.15 | −3.66 | −155% |
| weekly 30Δ wing 4% | 7,671 | 18.7 | 1.2 | 2.4 | 62.5% | +0.05 | **−0.43** | −1.17 | −0.90 | −121% |
| **weekly IRON BUTTERFLY wing 4%** | 7,851 | 38.2 | 0.7 | 1.5 | 53.7% | −1.27 | **−2.20** | −3.78 | −3.14 | −140% |
| monthly 10Δ wing 2% | 11,749 | 10.4 | 6.8 | 13.7 | 83.6% | +1.26 | **+0.10** | 0.37 | −1.06 | −220% |
| **monthly 10Δ wing 4%** | 11,743 | 7.8 | 4.5 | 8.9 | 84.6% | +1.67 | **+1.12** | **5.62** | +0.58 | −157% |
| monthly 16Δ wing 2% | 12,120 | 18.4 | 4.8 | 9.7 | 71.9% | −0.98 | **−2.54** | −6.47 | −4.10 | −220% |
| monthly 16Δ wing 4% | 12,104 | 13.5 | 3.1 | 6.3 | 74.0% | +0.92 | **+0.22** | 0.79 | −0.48 | −148% |
| monthly 30Δ wing 2% | 12,298 | 40.3 | 3.0 | 6.0 | 49.3% | −9.03 | **−12.01** | −18.03 | −14.99 | −264% |
| monthly 30Δ wing 4% | 12,295 | 29.9 | 1.9 | 3.8 | 55.9% | −3.62 | **−4.79** | −10.17 | −5.97 | −170% |
| **monthly IRON BUTTERFLY wing 4%** | 11,579 | 61.1 | 1.3 | 2.5 | 39.6% | −11.37 | **−14.47** | −17.09 | −17.56 | −275% |

**Pass 2 — one Wednesday entry per week. Non-overlapping. This is the honest test.**

| Structure | n | win | mean % of risk | **t** | median | worst |
|---|---|---|---|---|---|---|
| weekly 10Δ wing 4%, hold | 662 | 83.2% | **+0.15** | **+0.27** | +3.5 | −136% |
| weekly 16Δ wing 4%, hold | 665 | 75.2% | −0.26 | −0.34 | +5.9 | −136% |
| weekly 16Δ wing 2%, hold | 665 | 73.7% | −1.89 | −1.46 | +10.8 | −172% |
| weekly 30Δ wing 4%, hold | 665 | 62.4% | −0.79 | −0.64 | +8.9 | −136% |
| monthly 10Δ wing 4%, hold | 642 | 83.8% | **+1.17** | **+1.17** | +6.4 | −145% |
| monthly 16Δ wing 4%, hold | 654 | 72.6% | −0.15 | −0.11 | +11.1 | −161% |

**t = 2.64 becomes t = 0.27.** The weekly 10-delta condor's apparent significance was entirely an
artefact of counting ~1.8 overlapping trades per calendar day as independent observations. Compounded
at 5% of the account risked per trade over 17.7 years: **final ×1.032, CAGR +0.18%, Sharpe 0.07, max
drawdown −13.6%.** Eight of eighteen calendar years are negative.

**Answers to the RQ1 sub-questions, from this table:**

- **Short-strike delta.** Monotone and unambiguous: **further OTM is better, and 30-delta is a
  disaster.** 10Δ > 16Δ > 30Δ at both tenors, and the monthly 30Δ condor loses 4.8–12.0% of risk per
  trade. This is *not* an edge — it is the cost structure. The closer to the money you sell, the more of
  the payoff distribution's fat middle you are short, and the 30Δ condor is effectively a bet against
  ordinary market movement.
- **Wing width.** 4% wings beat 2% wings in every single pairing. The mechanism is arithmetic: a
  narrower wing collects less credit for the same number of legs, so the fixed 4-half-spread cost
  becomes a bigger fraction of it (2%-wing monthly 10Δ pays 6.8% of credit to open vs 4.5% for the
  4%-wing). **Narrow wings are a transaction-cost amplifier.** They also do not reduce risk — the loss
  is capped at a smaller number but the *probability* of hitting the cap rises faster.
- **Entry day of week.** Nothing survivable. On the overlapping 16Δ/4% sample: Mon +0.28 (t 0.45),
  Tue +0.66 (t 1.38), Wed −0.41 (t −0.83), **Thu +1.14 (t 2.38)**, Fri −0.11 (t −0.23). One cell out of
  five at t=2.4 with no adjacent-cell support is the exact signature of noise flagged in
  `FINDINGS.md` §3. Do not trade Thursdays because of this.
- **VIX level / IV rank.** By entry-IV quintile on the 16Δ/4% weekly condor:
  Q1 (IV 0.092) +0.94 (t 2.55) · Q2 +0.58 · Q3 +0.40 · Q4 −0.56 · Q5 (IV 0.284) +0.09 (t 0.12).
  If anything the relationship runs **backwards** from folklore — low-IV entries did marginally better,
  not high-IV ones. High IV brings a bigger credit (6.0% → 13.2% of width) and a *lower* win rate
  (80.7% → 73.2%), and the two cancel. **"Sell condors when IV rank is high" is not supported.**

### 2.4 Commissions, which the tables above exclude

A 4-leg condor is 4 contracts to open and up to 4 to close. At a typical $0.65/contract retail options
commission:

| Product | Credit per contract on a 10Δ/4%-wing weekly | Commission to open (4 legs) | as % of credit |
|---|---|---|---|
| SPY @ $500, 4% wing = $20 width | ~$0.98 → **$98** | $2.60 | **2.7%** |
| SPX @ 5000, 4% wing = 200pt width | ~9.8 pts → **$980** | ~$5.20 | **0.53%** |

Adding commissions therefore roughly **doubles** the total frictional drag on SPY and leaves SPX
almost unaffected. Combined with cash settlement (no exit cost when it expires inside the wings),
no assignment risk, and §1256 60/40 tax treatment, **there is no good reason to trade a multi-leg
index condor in SPY rather than SPX or XSP.** This does not rescue the strategy; it just means the
SPY numbers in §2.3 are optimistic by roughly another 2–3% of credit.

---

## 3. 0DTE IRON BUTTERFLIES

### 3.1 How the butterfly differs from the condor

| | Iron condor (OTM shorts) | Iron butterfly (ATM shorts) |
|---|---|---|
| Short strikes | both OTM, separated | both at the money, coincident |
| Credit as % of width (0DTE, 1% wings, 11:00, real) | 3.9% (10Δ) – 19.3% (30Δ) | **39.8%** |
| Win rate (0DTE, real, hold) | 85% (10Δ) / 79% (16Δ) / 64% (30Δ) | **54%** |
| Payoff | flat-topped plateau between the shorts | single point of maximum profit; you are paid for a *pin* |
| Gamma | modest until a short is approached | **maximum possible** — you are short the ATM straddle, the highest-gamma position that exists |
| Theta | modest | maximum |
| Practical consequence | wins often, loses rarely, loses big | roughly a coin flip, with the entire P&L determined by how far spot travels from the entry print |

The butterfly is the *cleanest possible* bet that realised intraday movement will be smaller than
implied. That makes it the correct instrument to test the volatility question — and it is why the
result below is decisive rather than merely discouraging.

### 3.2 The decisive measurement: there is no 0DTE ATM variance risk premium — REAL QUOTES

The ATM straddle mid price at time *t*, against the realised |close − spot(t)|, on 1,376–1,396 sessions:

| Entry | n | ATM straddle (bp of spot) | realised \|move\| (bp) | **realised / implied** | short straddle @ mid (bp) | **t** | 2 half-spreads (bp) | short straddle net (bp) | t |
|---|---|---|---|---|---|---|---|---|---|
| 10:00 | 1,393 | 55.1 | 54.7 | **0.994** | +0.3 | 0.26 | 1.82 | −1.5 | −1.12 |
| 10:30 | 1,395 | 50.8 | 50.8 | **1.000** | −0.0 | −0.01 | 1.18 | −1.2 | −0.94 |
| 11:00 | 1,396 | 47.5 | 47.8 | **1.007** | −0.4 | −0.27 | 1.03 | −1.4 | −1.07 |
| 11:30 | 1,396 | 44.8 | 44.4 | **0.991** | +0.4 | 0.33 | 1.00 | −0.6 | −0.52 |
| 12:00 | 1,396 | 42.2 | 41.3 | **0.978** | +0.9 | 0.85 | 0.95 | −0.0 | −0.01 |
| 13:00 | 1,391 | 37.7 | 37.0 | **0.980** | +0.7 | 0.77 | 0.94 | −0.2 | −0.20 |
| 14:00 | 1,376 | 33.5 | 32.9 | **0.982** | +0.6 | 0.68 | 1.35 | −0.8 | −0.86 |

**The 0DTE ATM straddle is priced within 2% of fair value at every hour of the day.** The gross short-vol
edge is between −0.4 and +0.9 basis points of spot per session, never exceeding t = 0.85 on ~1,400
observations covering 2016–2024 including COVID and 2022.

This is the single most important number in the report, and it is worth stating plainly against the
rest of the repo: `RULES.md` §1.1 established that realised/implied range is **0.843×** on high-gamma
days vs **1.139×** on low-gamma days, t = −13.2 over 15 years, normalised by **VIX9D** — a 9-day
implied. That finding is real and is not contradicted here. What §3.2 shows is that the *0DTE* surface
does not carry the same slack: at the actual tenor you would trade, implied and realised are equal.
The gamma effect that VIX9D fails to price is already in the same-day option price. That is the
`AWARE = 1` column of the `RULES.md` §1.2 assumption matrix, measured directly rather than assumed —
and `RULES.md` itself notes that at `AWARE = 1, vrp = 1.00` the strategy returns **−0.37%**.

### 3.3 Full sweep: every 0DTE structure, real quotes, net of entry spread only

Held to cash settlement, so **no exit cost is charged**. P&L in basis points of spot per trade.

| Entry | Structure | n | credit (bp) | cost (bp) | cost as % of credit | win | **bp/trade** | **t** | % of risk | worst (bp) |
|---|---|---|---|---|---|---|---|---|---|---|
| 10:00 | fly w=0.5% | 993 | 28.7 | 2.09 | 5.2 | 46.7% | −1.88 | −3.40 | −10.79 | −185.8 |
| 10:00 | fly w=1.0% | 1,348 | 43.1 | 2.02 | 3.7 | 53.5% | −2.24 | −2.80 | −4.97 | −78.6 |
| 10:00 | fly w=2.0% | 1,382 | 51.1 | 2.06 | 3.0 | 57.0% | −2.79 | −2.46 | −2.60 | −165.1 |
| 10:00 | condor 10Δ w=1% | 883 | 4.2 | 0.56 | 12.6 | 84.3% | −1.03 | −2.09 | −1.06 | −98.0 |
| 10:00 | condor 16Δ w=1% | 1,132 | 8.5 | 0.72 | 7.9 | 76.9% | −1.03 | −1.75 | −1.12 | −95.5 |
| 10:00 | condor 30Δ w=1% | 1,371 | 21.6 | 1.30 | 5.1 | 63.3% | −1.89 | −2.37 | −2.66 | −93.0 |
| 10:30 | fly w=1.0% | 1,355 | 40.7 | 1.42 | 2.9 | 54.3% | −1.43 | −1.89 | −2.59 | −87.5 |
| 10:30 | condor 16Δ w=1% | 1,182 | 8.1 | 0.60 | 7.1 | 77.8% | −0.66 | −1.16 | −0.70 | −96.3 |
| 11:00 | fly w=0.5% | 1,115 | 27.3 | 1.24 | 4.2 | 48.8% | −0.95 | −1.98 | −4.58 | −50.6 |
| 11:00 | fly w=1.0% | 1,365 | 38.8 | 1.25 | 3.0 | 54.4% | −1.26 | −1.67 | −2.38 | −83.1 |
| 11:00 | fly w=2.0% | 1,386 | 44.7 | 1.22 | 2.5 | 57.4% | −2.08 | −1.98 | −1.72 | −168.0 |
| 11:00 | condor 10Δ w=1% | 1,009 | 3.9 | 0.47 | 12.1 | 85.3% | −0.75 | −1.69 | −0.77 | −97.9 |
| 11:00 | condor 16Δ w=1% | 1,222 | 7.8 | 0.56 | 7.2 | 78.9% | −0.68 | −1.24 | −0.74 | −96.1 |
| 11:00 | condor 30Δ w=1% | 1,380 | 19.3 | 0.88 | 4.5 | 63.8% | −1.56 | −2.10 | −2.23 | −91.6 |
| **12:00** | **fly w=2.0%** | 1,388 | 40.1 | 1.13 | 2.6 | 59.7% | **−0.48** | **−0.52** | −0.39 | −177.1 |
| 12:00 | fly w=1.0% | 1,371 | 35.4 | 1.17 | 3.0 | 56.5% | −0.57 | −0.83 | −1.13 | −86.5 |
| **12:00** | **condor 16Δ w=1%** | 1,274 | 7.2 | 0.53 | 7.4 | 80.4% | **−0.18** | **−0.38** | −0.19 | −96.5 |
| 12:00 | condor 30Δ w=1% | 1,382 | 17.4 | 0.81 | 4.6 | 65.6% | −0.25 | −0.37 | −0.41 | −88.1 |
| 13:00 | fly w=1.0% | 1,368 | 32.2 | 1.15 | 3.2 | 56.8% | −0.70 | −1.04 | −1.31 | −82.4 |
| 13:00 | condor 16Δ w=1% | 1,312 | 6.7 | 0.54 | 7.9 | 78.4% | −0.52 | −1.13 | −0.56 | −96.1 |
| 14:00 | fly w=1.0% | 1,359 | 29.0 | 1.59 | 3.8 | 56.9% | −1.34 | −2.16 | −2.91 | −87.6 |
| 14:00 | condor 16Δ w=1% | 1,322 | 6.0 | 0.63 | 9.0 | 81.0% | −0.23 | −0.55 | −0.23 | −96.5 |

*(36 cells were computed; the table above is the full set for the entry times shown plus the extremes.)*

**Not one cell is positive.** The best is −0.18 bp (t = −0.38).

**Entry time of day.** There is a genuine, mechanically-explained U-shape and it is about **liquidity,
not edge**. The ATM half-spread in basis points of spot: 0.96 at 10:00 → 0.53 at 11:00 → **0.50 at
12:00–13:00** → 0.71 at 14:00. Midday is the cheapest hour to open a 0DTE structure, by roughly 2×
versus the open. That is why the "best" cells sit at 12:00, and it corroborates the `FINDINGS.md` §1
observation that 12:00 was the only non-negative cell (+0.95%, t=+0.82) in the prior real-quote run —
**that cell was a transaction-cost artefact, not an edge.** It is now measured directly.

**Wing width.** Wider is better, again for pure cost reasons: cost as % of credit falls from 6.1%
(0.3% wings) to 2.5% (2.0% wings) at 11:00. Narrow-wing butterflies are catastrophic — the 0.3%-wing
fly loses 10.8% *of capital at risk* per trade at 10:00 because the risk denominator (width − credit)
is only ~24% of width while the cost is unchanged.

**Liquidity has improved enormously and it still is not enough.** ATM half-spread as % of mid, by year:
9.11% (2016) → 4.84% (2018) → 2.50% (2021) → **1.16% (2024)**. An eight-fold improvement in 0DTE
transaction costs across the sample, and the strategy is still not profitable, because §3.2 shows the
gross edge is zero.

---

## 4. THE VOLATILITY RISK PREMIUM AT THESE HORIZONS, AND THE 4-LEG DRAG

### 4.1 Is there a premium?

| Horizon | Structure | Evidence | Premium present? |
|---|---|---|---|
| ~30 days, naked OTM put | PUT index 2010–2026 | +6.42%/yr over T-bills, **but alpha to SPX = +0.01%** | **Beta, not premium** |
| ~7 days, naked OTM put | WPUT index 2010–2026 | +3.24%/yr over T-bills, alpha **−2.84%** | **No** |
| ~30 days, defined-risk condor | CNDR 2010–2026 | −1.28%/yr, alpha **−2.74%** | **No** |
| ~30 days, defined-risk ATM fly | BFLY 2010–2026 | −5.32%/yr, alpha **−5.86%** | **No** |
| 5–10 days, SPY condor, real quotes | this report, 662 non-overlapping | +0.15% of risk, t=0.27 | **No** |
| 0DTE, SPX ATM straddle, real quotes | this report, ~1,390 sessions | realised/implied 0.978–1.007, t ≤ 0.85 | **No** |

The premium that made short-vol famous in 1990–2009 is not present in listed index option structures
since 2010, at any of these tenors, in any of these forms. What remains and still pays is **equity
beta obtained through short puts** — which you can get more cheaply and with better tax treatment by
owning the index, exactly as `RULES.md` §4 concluded for the swing sleeve.

### 4.2 The 4-leg drag, quantified — this is the number

A condor crosses the spread **4 times on entry**. If it is closed rather than expiring worthless, it
crosses **4 more times**. Charging half the quoted bid-ask per leg:

**SPX 0DTE (real SPXW quotes, median across sessions, 11:00 entry unless noted)**

| Structure | Mid credit (bp of spot) | **4 half-spreads = % of credit** | **8 half-spreads = % of credit** |
|---|---|---|---|
| Iron fly, 0.3% wings | 21.9 | **6.1%** | **12.2%** |
| Iron fly, 0.5% wings | 30.0 | 4.2% | 8.5% |
| Iron fly, 1.0% wings | 39.8 | **3.0%** | **6.0%** |
| Iron fly, 2.0% wings | 45.2 | 2.5% | 5.0% |
| Condor 30Δ, 1.0% wings | 19.3 | 4.5% | 8.9% |
| Condor 16Δ, 0.5% wings | 6.9 | 9.3% | 18.7% |
| Condor 16Δ, 1.0% wings | 7.8 | **7.2%** | **14.3%** |
| Condor 10Δ, 1.0% wings | 3.9 | **12.1%** | **24.2%** |
| Condor 10Δ, 0.5% wings | 3.8 | **14.5%** | **28.9%** |
| *same at the 10:00 open (10Δ, 1.0% wings)* | 4.2 | *12.6%* | *25.2%* |
| *same at 14:00 (10Δ, 1.0% wings)* | 3.1 | *14.4%* | *28.7%* |

**SPY weekly/monthly (real EOD bid/ask, median)**

| Structure | Credit as % of width | 4 half-spreads = % of credit | 8 half-spreads = % of credit |
|---|---|---|---|
| Weekly 10Δ, 4% wings | 4.9% | 3.5% | 7.0% |
| Weekly 16Δ, 4% wings | 8.5% | 2.2% | 4.3% |
| Weekly 16Δ, 2% wings | 13.4% | 2.6% | 5.3% |
| Weekly iron fly, 4% wings | 38.2% | 0.7% | 1.5% |
| Monthly 10Δ, 2% wings | 10.4% | **6.8%** | **13.7%** |
| Monthly 10Δ, 4% wings | 7.8% | 4.5% | 8.9% |
| Monthly 16Δ, 2% wings | 18.4% | 4.8% | 9.7% |

**The answer, in one sentence: the round-trip bid-ask on a 4-leg index condor costs between 1.5% and
29% of the mid credit, and it scales inversely with the credit — the further OTM you sell, the larger
the fraction of your premium the spread takes.** At the popular retail configuration (10-delta shorts,
narrow wings) it is **24–29% of the credit at 0DTE** and **~14% at monthly tenor on SPY**.

**The same drag expressed as % of capital at risk** — the denominator you actually compound, and the
one the owner's parallel run uses. Both fill conventions shown; `FULL` = enter at ask, exit at bid
(`scripts/cb_drag_crosscheck.py`, medians):

| SPX 0DTE, 11:00 entry | credit % of width | 8 half-spreads, % of risk | **8 full spreads, % of risk** |
|---|---|---|---|
| Iron fly, 0.5% wings | 55.5 | 9.20 | **18.39** |
| Iron fly, 1.0% wings | 36.3 | 3.26 | **6.51** |
| Iron fly, 2.0% wings | 19.3 | 1.23 | 2.45 |
| Condor 30Δ, 1.0% wings | 17.7 | 1.82 | 3.64 |
| Condor 16Δ, 1.0% wings | 7.9 | 1.20 | 2.40 |
| Condor 10Δ, 1.0% wings | 4.4 | 1.02 | 2.04 |
| *Iron fly 0.5% wings @ 10:00 (worst hour)* | 59.1 | 12.87 | **25.73** |

| SPY | credit % of width | 8 half-spreads, % of risk | **8 full spreads, % of risk** |
|---|---|---|---|
| Weekly 16Δ, 2% wings | 12.7 | 0.81 | 1.63 |
| Weekly iron fly, 4% wings | 35.9 | 0.96 | 1.92 |
| Monthly 16Δ, 2% wings | 18.1 | 2.05 | 4.11 |
| Monthly iron fly, 4% wings | 61.3 | 3.91 | **7.82** |

**The single variable that determines the drag in risk units is wing width.** A 0.5%-wing 0DTE
butterfly burns 18–26% of its capital at risk on execution alone; a 2%-wing version burns 2.5%. This
is why "narrow wings for a bigger credit" is the most expensive mistake in the structure — the credit
rises, but the *risk denominator* shrinks faster, and the spread is unchanged.

### 4.3 Independent replication of the owner's own SPY result, and the drag in *risk* units

The owner's parallel run (SPY 2008–2025, entries at ask, exits at bid, 147,350 de-duplicated
structure-trades) produced: **iron condor 30/16 → 48.6% win, −15.83%/trade, t=−17.5; iron condor
16/05 → 63.6% win, −10.54%/trade, t=−13.5; iron butterfly ATM → 45.9% win, −13.83%/trade, t=−20.1**,
with the 8 spread crossings ≈ 10% of capital at risk.

Re-measured here with independent code on the same file (`scripts/cb_drag_deltawing.py`), using
delta-defined wings to match those structures exactly. `FULL_r` is the owner's convention — enter at
the ask, exit at the bid — so it is the directly comparable column:

| Tenor | Structure | n | credit % of width | 8 half-spreads % of **risk** | **8 full spreads % of risk** | win | at mid | half | **FULL** | t(FULL) |
|---|---|---|---|---|---|---|---|---|---|---|
| weekly | condor 30Δ/16Δ | 7,966 | 33.6 | 2.42 | **4.84** | 52.5% | −0.71 | −4.27 | **−7.83** | −12.3 |
| weekly | condor 16Δ/5Δ | 7,959 | 10.9 | 0.72 | 1.44 | 74.7% | +0.53 | −0.47 | **−1.48** | −5.2 |
| weekly | condor 10Δ/5Δ | 7,850 | 7.5 | 1.07 | 2.15 | 80.3% | +0.66 | −0.75 | **−2.16** | −8.6 |
| weekly | iron fly ATM/16Δ | 7,987 | 53.9 | 2.33 | **4.67** | 44.2% | −1.17 | −4.78 | **−8.40** | −10.5 |
| weekly | iron fly ATM/5Δ | 8,012 | 32.4 | 0.73 | 1.45 | 53.4% | +0.06 | −1.82 | −3.70 | −6.2 |
| monthly | condor 30Δ/16Δ | 14,056 | 29.2 | 2.09 | **4.19** | **49.7%** | −2.24 | −5.19 | **−8.14** | −19.9 |
| monthly | condor 16Δ/5Δ | 13,980 | 9.5 | 0.57 | 1.15 | 73.7% | +1.25 | +0.03 | −1.20 | −4.0 |
| monthly | condor 10Δ/5Δ | 13,203 | 6.7 | 0.75 | 1.50 | 81.7% | +1.41 | +0.10 | −1.22 | −4.6 |
| monthly | iron fly ATM/16Δ | 14,388 | 49.0 | 2.15 | **4.29** | **41.1%** | −4.86 | −8.30 | **−11.74** | −20.4 |
| monthly | iron fly ATM/5Δ | 14,438 | 28.6 | 0.64 | 1.28 | 51.3% | −0.60 | −2.28 | −3.95 | −11.4 |

**The replication holds.** Win rates match closely (owner 48.6% vs 49.7% for the 30/16 condor; 45.9%
vs 41.1% for the ATM butterfly), signs match everywhere, t-statistics are the same order of magnitude
and sign, and the monthly ATM butterfly reproduces at −11.74% against the owner's −13.83%. The
residual differences are consistent with expiry-selection and de-duplication choices; the conclusion is
identical and now rests on two independent implementations.

**On the ~10%-of-capital figure:** measured as a *median* here it is **4.2–4.8% of capital at risk**
for the 30/16 condor and the ATM/16 butterfly, and **1.2–2.2%** for far-OTM condors. The distribution
is strongly right-skewed, so the *mean* is materially higher than the median and ~10% is a reasonable
mean-based figure for the near-the-money structures. **The two studies agree on the order of magnitude;
the honest range to quote is "single-digit percent of capital at risk for delta-defined wings, rising
to 13–26% for very narrow wings" (§4.2).** Note that the drag alone (4–5%) does *not* account for a
−8% to −16% per-trade loss on the near-the-money structures — §0 shows those are negative at the mid
too. Costs are the dominant cause only for the far-OTM condors.

Three corollaries that matter more than the headline:

1. **The denominator that matters is capital at risk, not credit.** A 0DTE 11:00 iron fly with 1% wings
   pays 1.25 bp of spot to open against 61 bp of risk = **2.0% of risk consumed per trade**, against a
   gross mid edge of approximately **zero**. The cost does not have to be large relative to the credit;
   it only has to be large relative to the (nonexistent) edge.
2. **Max loss is bigger than "defined risk."** The entry (and exit) spread sits *outside* the
   width − credit envelope. Observed worst trades run to **−136% to −172% of nominal capital at risk**
   on the weekly SPY condor and **−157%** on the 0DTE fly. If you size at 5% "risk" per trade, your
   true worst case is closer to 7%.
3. **Cash settlement is worth roughly half the total drag.** SPX/SPXW/XSP structures that expire inside
   the wings pay 4 half-spreads, not 8. That is a genuine, quantified reason to prefer index products —
   it just isn't worth enough to flip the sign.

---

## 5. MANAGEMENT RULES: what the evidence supports

Tested on **real quotes**, path-dependent, with the exit spread charged. This is the section where the
folklore is most directly contradicted.

### 5.1 0DTE SPX, 11:00 entry, exits evaluated on the real 30-minute quote grid

| Structure | Rule | n | win | **bp/trade** | **t** | worst (bp) | % closed early |
|---|---|---|---|---|---|---|---|
| Iron fly 1.0% wings | hold to expiry | 1,365 | 54.4% | **−1.26** | −1.67 | −83.1 | 0% |
| | PT 25% | 1,365 | **69.4%** | **−2.14** | −3.56 | −83.1 | 61% |
| | PT 50% | 1,365 | 56.0% | −1.35 | −1.84 | −83.1 | 19% |
| | stop at 2× credit | 1,365 | 54.1% | −1.34 | −1.81 | **−76.3** | 7% |
| | PT 25% + stop 2× | 1,365 | 69.0% | **−2.23** | −3.80 | −76.3 | 67% |
| Iron fly 2.0% wings | hold | 1,386 | 57.4% | −2.08 | −1.98 | −168.0 | 0% |
| | PT 25% | 1,386 | **72.4%** | **−2.97** | −3.39 | −168.0 | 65% |
| | stop at 2× credit | 1,386 | 56.9% | **−1.72** | −1.75 | **−126.6** | 11% |
| Condor 16Δ 1% wings | hold | 1,222 | 78.9% | −0.68 | −1.24 | −96.1 | 0% |
| | PT 25% | 1,222 | **84.5%** | **−1.27** | −3.33 | −96.1 | 88% |
| | PT 50% | 1,222 | **85.4%** | **−1.30** | −2.74 | −96.1 | 78% |
| | **stop at 2× credit** | 1,222 | 69.1% | **−0.14** | −0.40 | **−76.9** | 24% |
| Condor 30Δ 1% wings | hold | 1,380 | 63.8% | −1.56 | −2.10 | −91.6 | 0% |
| | PT 25% | 1,380 | 81.9% | −2.23 | −4.13 | −91.6 | 78% |
| | stop at 2× credit | 1,380 | 60.5% | −0.90 | −1.39 | −165.6 | 21% |

**Every profit target makes 0DTE expectancy worse, in every structure, without exception — while
raising the win rate substantially.** The 16Δ condor goes from 78.9% win / −0.68 bp to **85.4% win /
−1.30 bp** under "manage winners at 50%". That is the tastytrade result reproduced *exactly* — the win
rate improves as advertised — and the money goes the other way, on real quotes, because you pay four
more half-spreads to buy back a position that a cash-settled index would have retired for free.

**"Manage winners at 50%" is a win-rate optimisation, not a return optimisation.** On a cash-settled
0DTE index structure it is strictly value-destroying. The reason it is nonetheless the single most
promoted rule in retail options education deserves stating: **tastytrade/tastylive is the research arm
of a brokerage whose revenue is a function of round-trip contract volume, and a 50% profit target
roughly doubles the number of contracts traded per unit of exposure.** Every study on this question
that I can identify originates from a firm that either operates a brokerage, sells trade-management
software, or sells education. That does not make the studies wrong, but it means the finding has never
been independently replicated by a party with nothing to sell, and the mechanism by which it fails here
(the exit spread) is exactly the cost such a party would be least motivated to model.

**Stops are the one rule with a defensible case at 0DTE**, and the case is about risk, not return: the
2× credit stop is the only rule that improves the mean in any structure (16Δ condor −0.68 → −0.14 bp)
and it cuts the worst observed loss by 20% (−96.1 → −76.9 bp). It still does not produce a positive
expectancy.

### 5.2 Weekly SPY, non-overlapping, exits priced from the real EOD chain each day

| Structure | Rule | n | win | mean % of risk | t | closed early |
|---|---|---|---|---|---|---|
| Weekly 10Δ 4% | hold | 662 | 83.2% | +0.15 | 0.27 | 0% |
| | PT 50% | 680 | 84.1% | **+0.58** | 1.05 | 10% |
| | PT 25% | 702 | 87.2% | +0.49 | 0.96 | 27% |
| | stop 2× | 667 | 78.0% | **−0.16** | −0.31 | 9% |
| Weekly 16Δ 4% | hold | 665 | 75.2% | −0.26 | −0.34 | 0% |
| | PT 50% | 687 | 76.7% | +0.21 | 0.28 | 11% |
| | stop 2× | 670 | 71.2% | **−0.66** | −0.93 | 9% |
| Weekly 16Δ 2% | hold | 665 | 73.7% | −1.89 | −1.46 | 0% |
| | PT 50% | 702 | 78.3% | −0.81 | −0.68 | 29% |
| | stop 2× | 674 | 68.2% | −1.97 | −1.70 | 14% |
| Weekly 30Δ 4% | hold | 665 | 62.4% | −0.79 | −0.64 | 0% |
| | PT 50% | 681 | 64.2% | −0.21 | −0.18 | 7% |
| | stop 2× | 668 | 61.1% | −0.92 | −0.77 | 6% |

**At the weekly horizon the signs flip and the honest reading is "both effects are within noise."**
PT 50% helps every structure (+0.43pp on the 10Δ, +0.47pp on the 16Δ) — but the best resulting t-stat
is 1.05. Stops hurt every structure (−0.31 to −0.40pp), which is the direction the practitioner
literature reports and the direction theory predicts: a stop on short premium converts a temporary
mark-to-market excursion into a realised loss on positions that would have recovered by expiry.

**The defensible synthesis, stated at the confidence the evidence supports:**

| Rule | 0DTE cash-settled index | Weekly SPY | Confidence |
|---|---|---|---|
| Take profit at 25% | **Strictly harmful** (−0.6 to −0.9 bp, t up to −4.1) | Mildly helpful, insignificant | High for 0DTE |
| Take profit at 50% | **Harmful** | Mildly helpful, insignificant | Moderate |
| Stop at 2× credit | Mildly helpful to expectancy, clearly helpful to worst-case | **Harmful to expectancy** (all 4 structures) | Moderate |
| Hold to expiry | Best for 0DTE (free exit) | Neutral | High for 0DTE |

The one durable, mechanism-backed conclusion: **for cash-settled 0DTE index structures, holding to
settlement is free and closing early is not, so any profit-taking rule must overcome a ~3–14%-of-credit
handicap before it adds anything. It does not.**

---

## 6. TAIL RISK AND RUIN

### 6.1 What actually happened in the named events

Cboe index cumulative drawdown through each stress window (real index levels):

| Window | CNDR | BFLY | PUT | WPUT | BXM | SPX |
|---|---|---|---|---|---|---|
| Feb 2018 (2018-02-01→02-12) | **−3.45%** | −4.79% | −4.52% | −6.31% | −4.51% | −5.94% |
| Mar 2020 (2020-02-19→03-23) | **−9.30%** | −3.80% | **−28.87%** | −25.07% | −30.16% | −33.61% |
| Aug 2024 (2024-07-31→08-07) | **−2.80%** | −3.16% | −3.68% | −2.73% | −3.72% | −4.36% |
| Dec 2018 | −5.60% | −4.99% | −8.78% | −6.33% | −7.87% | −10.60% |
| Apr 2025 (tariff shock) | −0.47% | +0.54% | −2.43% | −6.26% | −2.32% | −4.15% |

**This is the one place where the defined-risk structure genuinely delivers, and it deserves to be said
clearly.** In March 2020 the naked put-write lost 28.9% and the index lost 33.6% while the iron condor
lost 9.3% and the iron butterfly 3.8%. The wings work. Feb 2018 cost CNDR 3.5%. Aug 2024 cost it 2.8%.

The honest framing of a listed index iron condor is therefore **not** "picking up pennies in front of a
steamroller." It is: **you buy real, effective crash insurance, and the insurance costs more than the
premium you collect.** The historical worst single day for CNDR in the modern era is −4.6% (2010–2019)
and −4.1% (2020–2026); the two worse days in the entire 40-year series are 1987-10-19/22. The
catastrophic tail lives in the *naked* short-vol trade, which is the one that actually pays.

*Note: `data/spxw/data_opt.parquet` ends 2024-05, so the Aug 2024 event cannot be tested on the local
0DTE quote data. The SPY EOD chains run to 2025-12 and do cover it.*

### 6.2 Worst-case magnitude relative to typical credit

**0DTE SPX iron fly, 1.0% wings, 11:00 entry, real quotes — the 15 worst sessions:**

| Date | SPX move | credit (bp) | risk (bp) | **P&L as % of risk** |
|---|---|---|---|---|
| 2019-08-23 | −2.42% | 53.1 | 46.9 | **−157.0%** |
| 2018-02-09 | +1.25% | 74.5 | 25.5 | −140.4% |
| 2020-04-08 | +2.01% | 73.1 | 26.9 | −123.7% |
| 2020-04-06 | +2.46% | 73.5 | 26.5 | −123.4% |
| 2018-12-24 | −1.81% | 66.8 | 33.2 | −116.8% |
| 2016-11-09 | +1.21% | 58.6 | 41.4 | −113.9% |
| 2018-10-29 | −2.02% | 60.6 | 39.4 | −113.3% |
| 2018-12-21 | −2.56% | 66.2 | 33.8 | −112.0% |
| 2022-01-24 | +2.54% | 74.1 | 25.9 | −110.4% |

Three things to take from this:

1. **The worst 0DTE day is only ~1.5× the defined risk, not a wipeout** — the wings hold. −157% of
   nominal risk, where the excess over 100% is the entry spread on a wide-spread day.
2. **It does not take a crash.** A +1.21% day (2016-11-09) or +1.25% day (2018-02-09) is a full max
   loss on a 1%-wing butterfly. The butterfly reaches its worst case on ordinary days; that is the
   whole reason its win rate is only 54%.
3. **Loss-to-credit ratio.** A typical 1%-wing fly collects 38.8 bp and risks 61 bp — so one max loss
   erases **1.6 winners**. A 10Δ condor collects 3.9 bp and risks 96 bp — one max loss erases
   **24.6 winners**. That is the payoff asymmetry: 85% win rate at 1:24.6 needs a 96.1% win rate to
   break even before costs. It has 85%.

**SPY weekly 16Δ condor, trades open into each event (overlapping entries, real quotes):**

| Window | open trades | win | mean % of risk | worst | total risk-units lost |
|---|---|---|---|---|---|
| Feb 2018 | 22 | 31.8% | **−33.7%** | −100.5% | −7.42R |
| Mar 2020 | 61 | 45.9% | **−31.7%** | −104.6% | −19.34R |
| Aug 2024 | 39 | 41.0% | **−21.2%** | −100.2% | −8.27R |
| Apr 2025 | 55 | 54.5% | **−24.2%** | −100.6% | −13.34R |

### 6.3 What this implies for sizing a small account

The R-units column above is the ruin calculation, and **the binding variable is concurrency, not the
structure.** In March 2020 there were roughly 5 weekly cycles in the drawdown window. Then:

| Concurrency | Risk per trade | March 2020 outcome |
|---|---|---|
| 1 position at a time | 5% | ~5 trades × −32% × 5% ≈ **−8% of account** |
| 1 position at a time | 20% | ≈ **−32%** |
| ~12 overlapping (one per trading day) | 5% | 61 × −32% × 5% ≈ **−97% — terminal** |
| ~12 overlapping | 2% | ≈ **−39%** |

**Sizing rules that follow from the data, if this were traded at all:**

- Risk per trade ≤ 5% of account, where "risk" is computed as **width − credit + 2× the entry spread**,
  not width − credit. The observed worst cases exceed nominal risk by 10–72%.
- **Cap total simultaneous risk, not per-trade risk.** One weekly condor at a time, or an explicit cap
  of ~15% of account at risk across all open condors. This is the `RULES.md` §7 "correlated tail" point,
  and the numbers above show it is the dominant risk by an order of magnitude.
- A 5-consecutive-max-loss streak is entirely normal for a 54%-win butterfly and costs 5 × 1.05 × risk.
- Never size off the win rate. **85% win at 1:24.6 is a losing bet; 54% win at 1:1.6 is a losing bet.**
  Both are in this data.

---

## 7. REGIME CONDITIONING — is there any state variable that flips the sign?

This is the section where the local prior work has the strongest claim, and the answer has to be
consistent with it.

**The exhaustive answer, from the owner's parallel run: 1,001 regime-gated cells — including GEX and
DIX z-scores, VIX percentile, VIX term structure, and IV-minus-RV — produced ZERO cells positive in
all three periods. The best cell reached t = +3.49, below the multiple-testing bar of 3.72.** That is
a far more complete search than anything below and it should be treated as the primary result; the
tables in this section are consistent with it and are retained because they show the *mechanism*
(credit and win rate moving in exactly offsetting directions) rather than just the outcome.

**IV level / IV rank — REJECTED on both datasets.**

0DTE SPX, 11:00, by entry ATM-IV quintile (real quotes):

| Quintile | ATM IV | Iron fly credit (bp) | fly win | fly bp/trade | t | Condor 16Δ bp/trade | t |
|---|---|---|---|---|---|---|---|
| Q1 | 0.101 | 19.5 | 58.2% | −1.38 | −1.36 | −0.43 | −0.54 |
| Q2 | 0.150 | 28.3 | 58.2% | −0.66 | −0.48 | −0.29 | −0.33 |
| Q3 | 0.200 | 36.8 | 59.7% | −0.14 | −0.08 | −1.29 | −1.06 |
| Q4 | 0.277 | 47.9 | 49.5% | −2.07 | −1.05 | −1.28 | −0.89 |
| Q5 | 0.418 | 61.5 | 46.5% | −2.04 | −0.96 | −0.14 | −0.08 |

No monotone relationship, nothing significant, and the direction is if anything *unfavourable* to
high-IV entries (win rate falls 58% → 47% as the credit rises 19.5 → 61.5 bp — precisely offsetting).
Same result on SPY weeklies (§2.3): Q1 +0.94 (t 2.55), Q5 +0.09 (t 0.12), no monotonicity.

**Dealer gamma — the prior finding stands, and §3.2 explains why it does not monetise.**

`RULES.md` §1.1 is not overturned. Realised/implied range 0.843× on high-gamma days vs 1.139× on low,
t = −13.2 over 15 years, normalised by VIX9D, is a real and well-identified result. What §3.2 adds is
the missing link: **at the 0DTE tenor, implied and realised are equal on average (ratio 0.978–1.007).**
VIX9D — a 9-day implied — is slow to price the same-day gamma state; the same-day option is not. The
gamma effect is real in the underlying and priced in the instrument. This is precisely the
`FINDINGS.md` §1 conclusion ("it simply does not convert to profit at market prices, which is itself
informative: the market has it priced") now measured directly rather than inferred from a failed
backtest.

**Not tested here, and honestly open:** VIX term-structure slope (VIX9D/VIX, VIX/VX2) and
realised-vs-implied ratio measured on a *trailing* window. Neither is in the SPXW parquet. See test
specs T5 and T6 in §8 — but the prior should be strongly negative given that (a) every other
conditioning variable tested has failed, (b) the unconditional gross edge at the ATM is zero rather
than merely small, so a conditioner would have to do more than tilt the mean, it would have to create
one, and (c) `RULES.md` §3.8 already found that regime and VIX-term-structure gates *hurt* the 35-DTE
put-credit-spread programme.

**The general principle this study keeps re-confirming:** conditioning variables tested on modelled
option prices produce large, significant, entirely fictitious edges, because a conditioner that
predicts *realised* volatility will look profitable against any implied vol the model holds fixed.
Against real quotes the same conditioner produces nothing, because the market moved the implied.

---

## 7b. EXTERNAL EVIDENCE: repositories audited at code level, and what could not be verified

### 7b.1 `lambdaclass/options_portfolio_backtester` — VERIFIED, and it is the source of `data/opt_eod/`

256 stars, MIT, last updated 2026-08-01, cloned and read.

**The data claim is true.** `data/DATA_NOTICE.md` documents six parquet files — **SPY 2008–2025,
QQQ 2011–2025, IWM 2008–2025** — EOD chains plus underlying, distributed via GitHub Releases
(`lambdaclass/options_backtester/releases/download/data-v1`) and pinned by SHA-256 in
`scripts/fetch_data.py`. **These are the same files now in `data/opt_eod/`** (identical filenames and
schema), so everything in §2.3, §4.3 and §5.2 of this report runs on that dataset.

**Quality of the engine — better than the category average:**

| Check | Finding |
|---|---|
| Fill convention | `execution/fill_model.py:22` — default is **`MarketAtBidAsk`**: sell at bid, buy at ask. The honest convention, and the same one the owner used. `MidPrice` exists at line 32 as an opt-in footgun. `VolumeAwareFill` (line 44) pushes low-volume fills further against you. |
| Commissions | `execution/cost_model.py:26` — **default is `NoCosts`**, and `engine.py:124` confirms `self.cost_model = cost_model or NoCosts()`. **This is a real defect**: any result run with defaults excludes commissions entirely. `PerContractCommission` ($0.65) must be passed explicitly. On SPY that is 2.7–5.3% of credit (§2.4). |
| Exit-chain `bid > 0` filtering | **Not present.** No `bid > 0` filter anywhere in the engine or portfolio modules. |
| Expiry settlement | `engine.py:63` `_intrinsic_value()` settles expiring contracts at intrinsic rather than requiring a quote row, which is the correct handling and structurally immunises it against the "deleting worthless legs manufactures a 100% win rate" bug. |
| Missing-strike honesty | The engine exposes `engine.option_fill_rate` and the docstring at `engine.py:55` explicitly warns that unavailable strikes silently degrade an overlay "into partial buy-and-hold and can produce misleading conclusions." Very few retail backtesters acknowledge this. |

**The one serious caveat is provenance, and it applies to every SPY/QQQ number in this report.**
`DATA_NOTICE.md` states the files were "originally mirrored from a publicly distributed dataset
(philippdubach/options-data)", that this upstream "disappeared in 2026", and — critically — that
**"the upstream's own sourcing was not documented."** So the bid/ask fields are of unknown origin: it
is not established whether they are consolidated NBBO at the close, a single exchange's quote, or a
vendor reconstruction, nor whether `delta`/`implied_volatility` are exchange-published or
vendor-computed. The notice also documents known gaps (IWM `adjClose` all-NaN; QQQ chain starts
2011-03-23). **Treat SPY/QQQ EOD results as directionally reliable and quantitatively approximate.**
The SPXW intraday panel is independent of this dataset, and the two agree — which is the best
available cross-validation.

### 7b.2 Repos that are worthless, with the defect named

| Repo | Verdict | Defect, with citation |
|---|---|---|
| `isaaclee2/Iron_Condor_Backtest` | **Textbook instance of the exit-chain bug** | `iron_condor/iron_condor_backtest.py:169-172` filters the mark-to-market chain with `short_calls[short_calls['ask'] > 0]`, `long_calls[long_calls['bid'] > 0]`, etc. — **this deletes exactly the worthless legs**, i.e. the ones that make a condor lose or win. Line 174 then *skips the mark entirely* if any filtered series is empty. Compounding it, lines 178–179 take `short_call_asks.min()` and `long_call_bids.max()` — the **best available price across the whole filtered set**, a second, independent cherry-picking bug. Entry (lines 66–69) is correct (short at bid, long at ask), which makes the exit bug easy to miss. |
| `ahmadsufiyan9889/Iron-Condor-Backtest-Strategy` | Not applicable | Indian index options (NIFTY/BANKNIFTY/FINNIFTY/SENSEX), single file, no bid/ask handling found. |
| `sanjaykeyan/ShortIronCondor-Backtester` | Trivial | Single `backtester.py`, no quote handling. |

The general lesson, stated so it can be reused: **the entry side of a retail condor backtest is
usually right and the exit side is usually wrong**, because worthless options are the natural thing to
filter out and are also the entire economics of the trade. Any repo claiming a >90% win rate on
condors should be grepped for `bid > 0` before anything else.

### 7b.3 What could NOT be verified in this session — stated rather than guessed

The primary academic sources requested (**Bandi–Fusari–Renò, SSRN 4503344**; **Freire et al., 0DTE
Asset Pricing**; Dew-Becker–Giglio–Le–Rodriguez on the term structure of the variance risk premium;
Muravyev–Pearson on effective vs quoted option spreads) **could not be retrieved.** SSRN returned
HTTP 403 to direct abstract-page fetches, cdn.cboe.com returned 403 to every documented methodology
URL, the OpenAlex API returned HTTP 429 (daily budget exhausted), and the session's WebSearch budget
was exhausted at 200/200 calls.

**I am not going to summarise papers I could not open.** What can be said honestly:

- No paper was located in this session that contradicts the empirical results above. That is a
  statement about a failed search, not about the literature.
- The finding that most directly constrains the verdict is §3.2 — 0DTE realised/implied = 0.978–1.007
  on ~1,390 sessions of real quotes — and it is a direct measurement that does not depend on any
  paper.
- The one published claim that could *materially* change the cost assumptions is Muravyev–Pearson's
  (RFS 2020) argument that **effective** option spreads are substantially tighter than **quoted**
  spreads for a patient trader. If that holds at 0DTE, the true drag sits between the `mid` and
  `half` columns of §4.3 rather than at `FULL`. **Test T7 in §8 measures this directly on local data
  and makes the paper unnecessary** — which is the right way to resolve it given that the local
  dataset has `bid_size`/`ask_size` and the paper does not cover 0DTE SPXW anyway.

**Recommended follow-up when search budget is available:** fetch SSRN 4503344 and the Freire et al.
0DTE paper, and check one thing in each — whether their P&L is computed from **quoted bid/ask or from
model/mid prices**. Given the failure documented in `FINDINGS.md` §1, that single question determines
whether either paper is evidence at all.

---

## 8. TEST SPECIFICATIONS AGAINST THE LOCAL DATA

Everything below is executable today on files already on disk. The scripts written for this report are
in `scripts/` and are the starting point for each.

Existing scripts: `scripts/cb_spxw_costs.py` (0DTE cost + straddle VRP), `scripts/cb_spxw_manage.py`
(0DTE management + regime + tail), `scripts/cb_weekly_condor.py` (SPY weekly/monthly sweep),
`scripts/cb_weekly_manage.py` (non-overlapping + path management), `scripts/cb_cboe_idx.py` (Cboe
index forensics), `scripts/cb_cndr_decay.py` (beta/alpha decomposition),
`scripts/cb_drag_crosscheck.py` (drag in credit and risk units, both fill conventions),
`scripts/cb_drag_deltawing.py` (delta-defined-wing replication).

---

### T1 — **The one test that could still overturn the 0DTE verdict: gamma-gated, on real quotes**
*Priority: highest. This is the direct successor to `RULES.md` §1.2 and it has never been run properly.*

- **Data:** `data/spxw/data_opt.parquet` joined on `quote_date` to the SqueezeMetrics GEX series already
  used by `backtest_0dte_rules.py` (prior-close GEX z-score, 252-day past-only window).
- **Entry rule:** sessions where prior-close `gz > +0.5`. Enter at 12:00 (cheapest spread hour, §3.3).
- **Structure:** iron condor, short strikes at ±1.25 SD of the remaining-session implied move where
  SD = ATM IV × √(minutes left / 390); wings 1.0% of spot beyond each short. Snap to the 0.001
  moneyness grid.
- **Pricing:** credit at mid; charge `0.5 × bas` on all four legs at entry; **no exit cost** (cash
  settled); settle with `payoff = max(0, sret − k_c) + max(0, k_p − sret) − max(0, sret − k_cl) − max(0, k_pl − sret)`.
- **Exit rule:** hold to settlement. Secondary run with stop at 2× credit evaluated on the 30-min grid.
- **Statistic to compute:** mean P&L **in basis points of spot** (not % of risk — the denominator
  explodes on narrow structures), its t-statistic, **and the difference vs the `gz ≤ +0.5` complement
  with a two-sample t-test.** The gate must beat its own complement, not zero.
- **Pass bar:** gated mean > 0 at t > 2.0 **and** gate-minus-complement > 0 at t > 2.0 **and**
  positive in ≥ 6 of the 8 calendar years. Anything less is noise.
- **Prediction from this report:** it will fail, because §3.2 shows the *unconditional* gross edge at
  the ATM is zero, so the gate would have to generate the entire edge rather than amplify one. But this
  is the highest-information remaining test and it settles the question the repo has been circling
  since `RULES.md` was written.

### T2 — **Does the gamma effect show up in the 0DTE implied vol itself? (the `AWARE` parameter, measured)**
*Priority: high. Cheap. Directly resolves the largest free parameter in `RULES.md`.*

- **Data:** `data/spxw/data_opt.parquet`, ATM (`mnes_rel == 1.000`) `implied_volatility` at 10:00, plus
  prior-close GEX z and VIX/VIX9D.
- **Test:** regress 0DTE ATM IV on prior-close GEX z-score, controlling for VIX9D (and for
  day-of-week and a year fixed effect). Then regress the *residual* realised move on the same.
- **Statistic:** β(gz) and its t-stat in each regression.
- **Interpretation:** `RULES.md` §1.1 found β(gz) = −0.074, t = −9.9 with **VIX9D** as the normaliser,
  i.e. the 9-day surface prices only part of the gamma effect. If β(gz) on **0DTE** ATM IV is strongly
  negative, `AWARE ≈ 1` and the entire `RULES.md` §1.2 assumption matrix collapses to its rightmost
  column (−0.37%/trade). §3.2 of this report already implies that answer indirectly; T2 measures it.

### T3 — **Weekly condor, delta × wing × DTE grid, non-overlapping, with a walk-forward**
*Priority: high. Extends `scripts/cb_weekly_manage.py`.*

- **Data:** `data/opt_eod/SPY_options.parquet`.
- **Entry rule:** one entry per calendar week (sweep entry weekday Mon–Fri as a robustness check, not
  as a parameter to select). Nearest expiry with DTE in the target band.
- **Grid:** short-strike |delta| ∈ {0.05, 0.08, 0.10, 0.13, 0.16, 0.20, 0.30} × wing width ∈ {2%, 3%,
  4%, 6% of spot} × DTE band ∈ {5–10, 10–17, 25–40}.
- **Pricing:** mid credit; `0.5 × (ask − bid)` per leg at entry; exit cost charged **only if the
  structure finishes in the money**; settle against the SPY close on the expiry date. Add
  **$0.65/contract × 4 (or 8) commission** as a separate column — on SPY this is 2.7–5.3% of credit and
  it is not optional.
- **Statistic:** mean % of capital at risk, t-stat, **plus a deflated Sharpe with `n_trials` = 84**
  (7 × 4 × 3), plus year-by-year means.
- **Pass bar:** the `RULES.md` §0 bar — anchored walk-forward (parameters chosen on data before Jan 1
  of each OOS year), positive in the OOS years, DSR ≥ 0.95.
- **Prediction:** the 10Δ/4%/monthly cell will be the best and will still not clear t = 2 on
  non-overlapping trades. Confirming that the *plateau* is centred on far-OTM + wide-wing (i.e. it is a
  cost gradient, not an edge) is itself the useful output.

### T4 — **QQQ replication, no re-tuning** *(the `FINDINGS.md` §2 cross-symbol discipline)*
- **Data:** `data/opt_eod/QQQ_options.parquet`, untouched so far.
- **Rule:** take the single best cell from T3 **frozen**, apply to QQQ, change nothing.
- **Statistic:** mean % of risk and t-stat; compare to the SPY point estimate.
- **Interpretation:** `FINDINGS.md` §2 already burned one signal that "works on QQQ only (1 of 3) —
  fitted." A weekly condor edge that is real should replicate on QQQ with a similar sign and magnitude,
  since it would be a claim about index variance pricing generally. If SPY works and QQQ does not, it is
  fitted. Note QQQ's higher realised vol makes a fixed %-of-spot wing a different structure — hold the
  wing at a constant *delta distance* instead, or at a constant multiple of ATM IV × √T.

### T5 — **VIX term-structure conditioning on the weekly condor**
- **Data:** SPY chains + a VIX/VIX3M (or VIX9D/VIX) series — **not currently in `data/opt_eod/`; must be
  fetched.** `backtest_0dte_rules.py` already loads VIX and VIX9D for the 15-year daily panel.
- **Rule:** condition T3's best cell on term-structure slope quintile measured at the **prior close**.
- **Statistic:** mean by quintile plus a monotonicity test (rank correlation of quintile → mean), not
  just the top-vs-bottom difference. `FINDINGS.md` §3 flags top-vs-bottom-only comparisons as fragile.
- **Prior:** negative. `RULES.md` §3.8 found term-structure gates *hurt* at 35 DTE.

### T6 — **Trailing realised-vs-implied as a conditioner**
- **Data:** SPXW parquet (0DTE version) or SPY chains (weekly version).
- **Rule:** compute, on an **expanding, shifted** window (`expanding().mean().shift(1)` — the
  `FINDINGS.md` §3 rule, no `groupby.transform`), the trailing 20-session ratio of realised daily move
  to the ATM straddle price. Condition entries on that ratio's quintile.
- **Statistic:** mean bp/trade by quintile, monotonicity, and OOS split.
- **Why it is worth one run:** it is the only conditioner that is *directly* about the quantity being
  traded (is the market currently over- or under-charging for movement?) rather than a proxy for it.
  §3.2 says the long-run ratio is 1.00; the question is whether it is autocorrelated enough to trade.

### T7 — **Direct measurement of realistic fill quality**
*Priority: medium, but it bounds everything else.*

- **Data:** `data/spxw/data_opt.parquet` `bid_size` / `ask_size` (present, unused so far).
- **Test:** for the 4 legs of the standard structure at each entry time, tabulate quoted size at the
  bid and ask, and compute the P&L under three fill assumptions: **mid**, **mid + 25% of the spread**,
  and **full half-spread**. §3.3 uses the third.
- **Why:** the academic claim (Muravyev–Pearson) is that effective option spreads are materially
  *tighter* than quoted for a patient trader. If a realistic 0DTE fill is mid + 25% rather than
  mid + 50%, the 12:00 16Δ condor moves from −0.18 bp to roughly −0.05 bp — still not positive, but it
  changes the shape of the answer, and it is the only assumption in this report that could be
  meaningfully wrong in the favourable direction.
- **Pass bar:** none — this is a sensitivity, not a strategy. Report the three columns side by side.

### T8 — **The only live thread: far-OTM condors under improved execution**
*Priority: medium-high. This is the single remaining structure that is positive before costs.*

- **Rationale:** §0 and §4.3 show that 16Δ/5Δ and 10Δ/5Δ condors are **positive at the mid**
  (+0.53% to +1.41% of capital at risk) and negative only after the round trip. Every other structure
  tested is negative before costs and is therefore dead regardless of execution. So this is the only
  configuration where "get better fills" is a coherent research programme rather than wishful thinking.
- **Data:** `data/opt_eod/SPY_options.parquet`, plus `data/spxw/data_opt.parquet` for the 0DTE analogue.
- **Test:** for the monthly 10Δ/5Δ condor, sweep the fill assumption from mid to full spread in
  increments (mid, mid+15%, mid+25%, mid+35%, half, full) and find the **break-even fill quality** —
  the fraction of the spread you must beat for expectancy to reach zero and then to reach a target.
  Report it as "you need to fill inside X% of the mid–ask distance."
- **Then:** compare that requirement against the actual `bid_size`/`ask_size` and against real
  observed fills once any live orders exist.
- **Statistic:** break-even spread fraction, and mean % of risk at each fill assumption, with
  non-overlapping weekly/monthly entries only.
- **Honest prior:** at mid the monthly 10Δ/5Δ makes +1.41% of risk and the full round trip costs
  ~1.5–2.6% of risk, so break-even sits at roughly **50–60% of the quoted spread**. That is a
  demanding but not absurd target for a patient limit order on a 4-leg combo. **It is also, at
  +1.4% of risk per monthly trade at best, worth about 1% a year on a 5%-risk sizing** — which is the
  real reason to deprioritise it, and that judgement should be made explicitly rather than by
  discovering it after building the system.

### T9 — **Re-run the §3.2 straddle test on data after 2024-05**
- **Data:** `data/spxw/data_opt.parquet` ends 2024-05 and therefore **excludes Aug 2024 and Apr 2025**,
  the two most recent short-vol stress events, and excludes the period of heaviest 0DTE volume growth.
- **Test:** extend the SPXW quote panel (ThetaData / CBOE DataShop / Polygon options) to present and
  re-run the realised/implied ratio by year.
- **Why:** the whole verdict rests on ratio ≈ 1.00. If 0DTE flow growth has pushed it below 1.00 in
  2024–2026, a premium has appeared; if above, the trade is worse than reported. This is the single
  most decision-relevant data gap.

---

## 9. What would change the verdict

1. **T1 passing.** A gamma-gated 0DTE condor that beats its own complement at t > 2 on real quotes.
   Nothing else in the repo would matter more. Note the owner's 1,001-cell regime sweep already found
   zero positives, so the prior on this is now low.
2. **§3.2 ratio moving decisively below 1.00 in recent data (T9).** The verdict is a measurement of a
   ratio, and the ratio can change.
3. **Fill quality materially better than half-spread (T7 + T8).** This is the only lever with a live
   mechanism, and it applies **only to far-OTM condors**, which are positive at mid. Break-even is
   roughly 50–60% of the quoted spread. Even if achieved it is worth ~1%/yr at 5% risk sizing.
4. **A structural product change** — e.g. a genuinely tighter 4-leg combo book, or XSP liquidity
   reaching SPX levels, cutting the 3–29%-of-credit drag by half.

Explicitly **not** on this list: better strike selection, better wing width, profit targets, stops,
IV-rank filters, VIX term-structure filters, or day-of-week. All were tested; all failed.

## 10. What this report does *not* establish

- It does not test **naked or 2-leg** short premium at 0DTE (short straddle without wings). §3.2 tests
  the ATM straddle at the mid and finds it fair, so the answer is very likely the same, but the margin
  requirements make it untradeable in a small account anyway.
- It does not test **skewed / broken-wing / ratio** structures, which have a directional component and
  are a different question.
- The Cboe **index methodologies were not verified from primary source** (cdn.cboe.com 403'd every
  documented methodology URL in this session). The daily index level series *are* Cboe's own.
- **No primary academic source was successfully retrieved** (SSRN 403, OpenAlex 429, WebSearch budget
  exhausted). §7b.3 states exactly what this does and does not imply. Nothing in this report is
  attributed to a paper I did not open.
- **The SPY/QQQ EOD chain provenance is undocumented upstream** (§7b.1). The bid/ask fields' origin —
  consolidated NBBO vs single-venue vs vendor reconstruction — is unknown. This affects every SPY
  number here at the margin, though not the sign of any result, and the independent SPXW intraday
  panel agrees.
- The SPXW panel is a **41-point moneyness grid**, not a raw strike-by-strike chain, and it spans only
  ±2% of spot. Wings beyond 2% cannot be tested.
- The weekly SPY tests use **EOD quotes only**. They cannot speak to intraday entry timing at the
  weekly tenor.
- **`data/spxw/data_opt.parquet` ends 2024-05.** Nothing here observes Aug 2024, Apr 2025, or the last
  two years of 0DTE volume growth on the 0DTE side.
- Formal multiple-testing correction (deflated Sharpe) was **not** applied to the sweeps in §2.3 and
  §3.3. It would only make the results worse — every cell of interest is already negative or
  insignificant — but the positive-looking overlapping cells in §2.3 should not be quoted without it.

---

## Appendix — the numbers most likely to be misquoted later

| Claim | Correct number | Source |
|---|---|---|
| "Cboe's iron condor index returns 5.3%/yr" | True for **1986–2026**, and it is **+2.10%/yr over T-bills at Sharpe 0.26**. Since 2010 it is **−1.28%/yr over T-bills, Sharpe −0.18, alpha −2.74%**. | Cboe CNDR daily CSV + FRED DTB3 |
| "Put-writing beats the market risk-adjusted" | PUT's 2010–2026 excess return is +6.42%/yr — with **beta 0.63 and alpha +0.01%**. It is levered-down equity. | same |
| "Weekly condors: +0.44%/trade, t=2.6" | That is the **overlapping** sample. Non-overlapping: **+0.15%/trade, t=0.27**. | `scripts/cb_weekly_manage.py` |
| "0DTE condors win 85% of the time" | True and irrelevant — the loss-to-credit ratio is **1:24.6**, so break-even needs **96.1%**. | §6.2 |
| "Managing winners at 50% improves results" | On real quotes it raises the 0DTE condor win rate 78.9% → 85.4% **and lowers the mean from −0.68 to −1.30 bp**. | §5.1 |
| "There's a big variance risk premium at 0DTE" | Realised/implied on the ATM straddle is **0.978–1.007**, t ≤ 0.85, ~1,390 sessions of real quotes. | §3.2 |
| "Defined risk means max loss = width − credit" | Observed worst trades are **−136% to −172% of that**, because the spread sits outside the envelope. | §6.2 |
| "The spread is what kills condors" | True **only for far-OTM structures**. The 30Δ condor and the ATM butterfly are **negative at mid prices** (−2.24% and −4.86% of risk per trade, monthly). Better fills cannot save them. | §0, §4.3 |
| "The 8 crossings cost ~10% of capital at risk" | Median is **4.2–4.8%** for delta-defined wings, **1.2–2.2%** for far-OTM, and **18–26%** for 0.5%-wing 0DTE butterflies. ~10% is a fair *mean* for near-the-money structures. **Wing width, not delta, determines this number.** | §4.2, §4.3 |
| "That backtest shows 95% win rate on condors" | Grep it for `bid > 0` on the **exit** chain first. `isaaclee2/Iron_Condor_Backtest:169-172` is the canonical example. | §7b.2 |
