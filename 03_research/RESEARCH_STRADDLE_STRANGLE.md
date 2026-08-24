# Straddles & Strangles as Tradeable Structures — Research Report

**Written:** 2026-08-06 · **Scope:** SPY / QQQ / IWM, SPX, single stocks · **Horizon:** days to ~6 weeks
**Companion docs:** `FINDINGS.md` (the 0DTE null), `RULES.md` (the 0DTE gamma rule set)

> **Read this first.** This report contains two kinds of evidence and they are labelled throughout:
> **[LIT]** = published literature, and **[OWN]** = original tests run for this report on **24.7M rows of
> real EOD NBBO option quotes** (`data/opt_eod/SPY_options.parquet` 2008-2025,
> `QQQ_options.parquet` 2011-2025). **No pricing model is used anywhere in the [OWN] results.**
> Every P&L number states its horizon, its fill assumption, and whether it came from quotes or a model.
>
> This is deliberate. The single most expensive error in this repo's history was the 0DTE iron condor
> that showed **+3.7%/trade under Black-Scholes with a linear skew approximation** and **−1.70%/trade on
> real SPXW bid/ask** (`FINDINGS.md` §1). Straddles and strangles are the purest expression of the
> realized-vs-implied bet, so they are exactly the structure where a model artefact would be most
> flattering and most fatal. Hence: real quotes only.

---

## 0. The one-paragraph answer

There is a real variance risk premium, it is smaller than folklore claims, and **almost all of the
statistically defensible part of it lives in the *delta-hedged* short ATM straddle — a structure retail
does not trade.** On 213 non-overlapping monthly SPY trades at real quotes (2008-2025), selling a
delta-hedged ATM straddle at the bid earned **+4.31% of premium per trade, t = +1.53**; selling the
*same trade naked* earned **+2.21%, t = +0.40**, with **double the standard deviation and a worst month
of −660% of credit instead of −190%**. Both are positive; neither is significant at 5%; both are beaten
on Sharpe by simply owning SPY over the identical windows (0.30 and 0.18 vs **0.64**). Buying straddles
or strangles loses money in every configuration tested and every configuration in the literature, and
the loss is *not* mainly a transaction-cost effect — on SPY the entire 2-leg round-trip spread is
**~1.1% of premium**, which is roughly one-fifth of the mean per-trade edge and cannot explain a
−5% expectancy. The earnings-crush trade is the one genuinely live question, and the best primary
evidence (Xing & Zhang, JFQA 2018) says the *opposite* of the retail folklore: straddle returns around
earnings are **significantly positive** (+2.3% one day before the announcement to the announcement),
concentrated in exactly the small, illiquid, wide-spread names where you cannot capture it.

---

## 1. THE STRUCTURAL BASELINE — what buying and selling index straddles is worth

### 1.1 What the literature establishes [LIT]

| Study | What was measured | Result | Fill basis |
|---|---|---|---|
| **Coval & Shumway 2001** (*JF* 56(3):983-1009) | Delta-neutral ATM S&P 500 index straddles, weekly | **≈ −3% per week** | model/quote midpoints |
| **Xing & Zhang** (JFQA 2018, working title *Anticipating Uncertainty*) | Volume-weighted delta-neutral ATM **individual stock** straddles | **−2.08%/week, t = −42.35**; daily −0.14%; **monthly −16.21%** | OptionMetrics midpoints |
| **Bakshi & Kapadia 2003** (*RFS*) | Delta-hedged index option gains | Significantly negative → negative market volatility risk premium | midpoints |
| **Broadie, Chernov & Johannes 2009** | Finite-sample-correct tests of index option returns | **ATM straddles significant** (−15.7%/month long side, p≈0.0% vs both BS and stochastic-vol nulls); **naked OTM puts NOT significant** (p = 8.1% BS, 24.1% SV) | midpoints |
| **VRP magnitude** (VIX vs subsequent 21d realized SPX vol, 1990-2026) | Variance-swap premium | mean spread **+4.09 vol points**, ratio 1.41, positive **85.8%** of the time, t = 12.99 non-overlapping | index calc |
| **Driessen, Maenhout & Vilkov** | Index vs single-stock VRP | index IV−RV **+3.77 pts**; single stock **−1.35 pts**; zero VRP unrejectable for **108 of 135** stocks | midpoints |
| **Dew-Becker & Giglio** (Chicago Fed WP 2025-17) | Option alphas, last 15 years | **Indistinguishable from zero**; zero cumulative return on traded puts Mar 2009 – Dec 2022 | traded prices |

**The single most important correction in this section:** the famous "+4 vol points" VRP is the
**variance-swap** premium, which is a strip across all strikes and is inflated by the OTM put skew.
**An ATM straddle seller does not collect it.** The ATM premium is roughly **2 vol points**
(Broadie-Chernov-Johannes: ATM implied ~17% vs realized ~15%). If you size a straddle program off the
4-point number you have double-counted your edge before you place a trade.

**The second correction:** Broadie-Chernov-Johannes is the result that matters most here and it is
almost always cited backwards. Under a correctly-specified finite-sample test, **ATM straddles are
significant and naked OTM puts are not.** The retail short-premium industry sells the OTM-put/OTM-
strangle structure. That is the structure with the *weakest* statistical support.

### 1.2 [OWN] Real-quote replication on SPY, 2008-2025

**Method.** Monthly (third-Friday) expiration cycle only, so trades are **non-overlapping** and a plain
t-stat on per-trade returns is valid. For each expiration, enter on the trading day closest to the
target DTE; ATM = strike nearest spot; N-delta strangle = call and put whose vendor delta is closest to
N. Held to expiry, settled at intrinsic on the underlying's close on the last trading day.
`long_ask` = bought at the offer. `short_bid` = sold at the bid. `*_mid` = midpoint, shown only to
isolate the cost drag. Script: `scripts/straddle_backtest.py`.

**ATM straddle, entry ~45 DTE, held to expiry, n = 213 (2008-01 → 2025-12):**

| leg | mean % of premium | median | t | win % | worst |
|---|---|---|---|---|---|
| LONG, bought at ASK | **−3.28%** | −19.4% | −0.59 | 40.9% | −99.5% |
| SHORT, sold at BID | **+2.21%** | +18.2% | +0.40 | 58.2% | **−660%** |

**ATM straddle, entry ~30 DTE, n = 213:**

| leg | mean | t | win % | worst |
|---|---|---|---|---|
| LONG at ask | −4.43% | −0.64 | 36.2% | −99.8% |
| SHORT at bid | +3.30% | +0.47 | 62.9% | −1051% |
| SHORT at bid, **on 20%-notional margin** | +1.43%/mo | +1.20 | 62.9% | −147% |

**By strike width, entry ~45 DTE, short side sold at the bid, n = 213:**

| structure | mean % of credit | t | win % | worst | mean % of margin | t |
|---|---|---|---|---|---|---|
| ATM straddle | +2.21% | 0.40 | 58% | −660% | +1.02% | 0.77 |
| 30-delta strangle | +9.27% | 0.95 | 62% | −1336% | +1.51% | 1.25 |
| 16-delta strangle | **+18.85%** | 1.22 | **76%** | **−2523%** | +1.49% | 1.49 |

**Read that table carefully — it is the whole strike-selection question answered on real quotes.**
As you go further OTM the *percentage of credit* rises fourfold and the win rate rises from 58% to 76%,
which is why 16-delta strangles are what gets marketed. But **return per unit of margin is flat at
~1.0-1.5% per month across all three**, and the worst single month gets **four times worse**. You are
not being paid for the extra tail. You are choosing a different point on the same line, with a more
flattering win rate and a longer fuse.

**Sub-period stability of the naked short ATM straddle [OWN]:**

| era | n | mean % of credit | t | win % | worst |
|---|---|---|---|---|---|
| 2008-11 | 48 | +8.20% | 0.63 | 65% | −378% |
| 2012-15 | 48 | +3.33% | 0.39 | 52% | −206% |
| 2016-19 | 47 | +2.28% | 0.26 | 57% | −164% |
| **2020-25** | 70 | **−2.72%** | −0.23 | 59% | **−660%** |

Monotone decay to negative. This is an independent, real-quote corroboration of **Dew-Becker & Giglio**:
whatever was there has been substantially arbitraged out of the naked index structure.

### 1.3 [OWN] The comparison that ends the discussion

Same 213 monthly windows, returns on a fully-collateralised 20%-of-notional Reg-T naked margin base
(no leverage), additive equity (compounding is invalid — single trades return worse than −100% of the
posted margin, which drives a geometric curve negative):

| program | mean %/mo | t | sd | **Sharpe (ann)** | skew | kurt | worst month |
|---|---|---|---|---|---|---|---|
| SHORT naked ATM straddle @bid | 1.02% | 0.77 | 19.5% | **0.18** | −2.44 | 14.4 | −132% |
| SHORT delta-hedged ATM straddle @bid | 1.25% | 1.25 | 14.6% | **0.30** | −4.48 | 41.8 | −139% |
| **SPY buy & hold, same windows** | **1.14%** | **2.68** | **6.2%** | **0.64** | −1.33 | 5.2 | −30% |

QQQ, 174 trades 2011-2025, same test: short naked **−0.76%/mo (t = −0.51, Sharpe −0.13)**, short
delta-hedged **+0.81%/mo (t = 1.32, Sharpe 0.35)**, **QQQ buy & hold +2.04%/mo (t = 4.04, Sharpe 1.06)**.

This reproduces `RULES.md` §4 by a completely different route and on real quotes rather than a model:
**every index option overlay tested is a worse way to own equity risk than owning equity.** Note also
the skew and kurtosis columns — Sharpe is the wrong statistic for these payoffs (Goetzmann, Ingersoll,
Spiegel & Welch on Sharpe-ratio manipulation: a short-option payoff mechanically inflates Sharpe by
trading a small, frequent gain for a rare enormous loss), and short vol still loses on it anyway.

---

## 2. DELTA-HEDGED vs NAKED — the widely-miscited gap, stated precisely

**This section answers research question 6 and it should change how you read every other number in
this report and in the literature.**

The academic VRP literature almost exclusively tests **delta-hedged** or **delta-neutral zero-beta**
straddles. Coval-Shumway's "−3%/week" is delta-neutral. Bakshi-Kapadia's gains are delta-hedged.
Xing & Zhang's "−2.08%/week" is delta-neutral. Broadie-Chernov-Johannes test both but their headline
straddle result is delta-neutralised. Retail trades **naked**. These are not the same trade, and the
difference is not a rounding error.

### [OWN] Both trades, same 213 SPY entries, real EOD NBBO, daily rehedge at the close, stock hedged at 1bp

`scripts/straddle_hedged.py`. Entry ~45 DTE, held to expiry.

| structure | mean % of premium | t | win % | **sd** | worst |
|---|---|---|---|---|---|
| LONG naked, bought at ask | −3.28% | −0.59 | 41% | 80.5% | −99.5% |
| **SHORT naked, sold at bid** | **+2.21%** | **+0.40** | 58% | **81.4%** | **−660%** |
| LONG delta-hedged, at mid | −4.85% | −1.72 | 30% | 41.1% | −89.9% |
| **SHORT delta-hedged, at mid** | **+4.85%** | **+1.72** | **70%** | **41.1%** | **−190%** |
| SHORT delta-hedged, **sold at the real bid** | **+4.31%** | **+1.53** | — | — | — |
| LONG delta-hedged, **bought at the real ask** | **−5.40%** | **−1.92** | — | — | — |

**The precise statement:**

1. **Delta-hedging roughly doubles the mean** (+2.21% → +4.85% of premium) and **halves the standard
   deviation** (81.4% → 41.1%). The t-statistic goes from **+0.40 to +1.72** — a **4.3× improvement in
   statistical quality on identical trades**. The improvement is real and it is large.
2. **It cuts the worst month from −660% of credit to −190%.**
3. Delta-hedging costs about **1.05% of premium** in stock spread at 1bp per rehedge — you are paying
   ~1% of premium to add ~2.6 percentage points of mean and remove half the variance. It is cheap.
4. **A naked straddle is not delta-neutral even at inception.** [OWN] median |net delta| at entry is
   **0.051** per share-equivalent (≈5 deltas per straddle), and it drifts hard as spot moves.
5. **The naked straddle is mostly a bet on the size of the move, not on volatility.** [OWN]
   `corr(short naked straddle return, |underlying move over the hold|) = −0.856` (SPY), **−0.902**
   (QQQ). That is r² ≈ 73-81%. For the delta-hedged version the correlation is only **+0.294**.

**Therefore: when someone cites Coval-Shumway or Bakshi-Kapadia to justify selling naked strangles,
they are citing a result about a trade they are not making.** The delta-hedged result is the one with
statistical support; the naked result on the same data is a coin flip with a catastrophic tail. If you
want the variance premium, you must hedge the delta — daily, mechanically, and at a cost of ~1% of
premium. If you will not hedge, you are not harvesting a variance premium; you are making a
low-conviction directional bet with an unbounded loss function.

**Caveat on my own hedge [OWN]:** deltas are vendor-supplied and rehedging is once daily at the close.
Discrete hedging error is real and unhedged intraday gamma remains. Intraday rehedging would reduce
variance further and cost more. The direction and rough magnitude of the effect are robust; the exact
+4.85% is not.

---

## 3. EARNINGS STRADDLES / STRANGLES — the IV-crush trade

**This is the least settled question in the report and the primary evidence points the opposite way to
the retail consensus.**

### 3.1 The baseline: single-stock options carry essentially no variance premium [LIT]

Driessen, Maenhout & Vilkov: index IV−RV is **+3.77 vol points**, single-stock IV−RV is **−1.35 vol
points**, and **zero VRP cannot be rejected for 108 of 135 stocks**. The index premium is compensation
for *correlation* risk, not for individual-name variance. **The structural tailwind that makes index
short-vol nearly break even does not exist on single names.** Anyone selling single-stock premium is
relying entirely on an event-specific mispricing, not on a background premium.

### 3.2 The primary evidence on earnings straddles [LIT]

**Gao, Xing & Zhang, "Anticipating Uncertainty: Straddles Around Earnings Announcements",
JFQA 53(6), Sept 2018, pp. 2587-2617.** (The 2013 working draft I read directly is authored Xing (Rice)
& Zhang (Purdue); Chao Gao is added on the published version.) Read directly from the authors' PDF
(`ruf.rice.edu/~yxing/straddle_201305_03.pdf`). Delta-neutral ATM straddles, OptionMetrics, midpoints.

> "On average, straddles on individual stocks earn significantly negative returns: daily holding period
> return is −0.19% and weekly holding period return is −2.09%. **In sharp contrast, straddle returns
> are significantly positive around earnings announcements: average at-the-money straddle returns from
> one day before earnings announcement to the earnings announcement date yields a highly significant
> 2.3% return.**"

Straddles are constructed **five, three, and one trading day before** the scheduled announcement and
held **until the announcement date or one day after**. All holding periods are significantly positive,
ranging **+0.31% to +2.30%**.

The authors' own interpretation: **"Positive straddle returns clearly indicate that the market
*underestimates* the uncertainties around earnings announcement days."**

Cross-section: returns are **stronger for smaller firms, less analyst coverage, higher historical
volatility, higher historical jump frequency, larger jump sizes, larger and more volatile past earnings
surprises**.

### 3.3 What this actually means for a trader — and the honest caveats

**1. The direction is the opposite of the retail folklore.** The documented effect is that **buying**
volatility into earnings pays. The "sell the IV crush" trade is the short side of a
statistically-positive long position. The pre-announcement IV run-up is *not* fully priced; the market
under-prices the coming uncertainty, and the option gets richer into the event faster than theta
decays it.

**2. It is a pre-announcement trade, not a through-the-announcement trade.** The strongest window is
1 day before → announcement date. The IV crush is what happens *after*; the paper is capturing the
run-up *before*. This distinction is where most retail discussion goes wrong in both directions.

**3. The cross-section is a transaction-cost warning label, not an opportunity.** "Smaller firms, less
analyst coverage, higher volatility, thin coverage" is a precise description of **the names with the
widest option bid/ask spreads**. A +2.3% mean return on a delta-neutral straddle constructed at
*midpoints* in small caps is very plausibly inside the spread. **[OWN] For scale: on SPY — the most
liquid option in the world — the 2-leg round-trip is ~1.1% of premium. On a small-cap single-stock
straddle it is routinely 5-15% of premium.** I was **unable to verify from the primary source that the
+2.3% survives realistic costs**, and the version I read (April 2013 draft) does not headline a
cost-adjusted number. **Treat the +2.3% as a gross, midpoint, small-cap-weighted figure.**

**4. The counterweight [LIT]: Muravyev & Pearson, "Options Trading Costs Are Lower Than You Think"
(*RFS* 33(11), 2020, 4973-5014).** Effective spreads for traders who **time their executions** are
**less than 40% of conventional quoted-spread measures**. This cuts both ways and must be stated
honestly: it means (a) my quoted-spread drag numbers are an **upper bound**, and (b) the standard
academic dismissal "costs kill it" is often overstated. It does **not** rescue a strategy whose gross
edge is 2.3% and whose quoted round trip is 10%+.

**5. Both sides are documented losers in the wrong hands.** Since single-stock straddles lose
**−0.19%/day and −2.08%/week** unconditionally [LIT: Xing & Zhang], a systematic long-straddle earnings
program that holds too long gives back the +2.3% and more. And a systematic *short* earnings straddle
is selling a structure whose measured mean return is positive, into a fat-tailed event, on names with
no background variance premium.

### 3.4 Verdict on earnings

**There is credible academic evidence of a positive expected return to BUYING delta-neutral ATM
straddles in the 1-5 days before an earnings announcement and closing at or immediately after the
announcement — gross of transaction costs, concentrated in illiquid small caps.** There is **no**
credible evidence for the retail short-IV-crush trade as a systematic edge; the best primary source
says the market **under**-prices earnings uncertainty, which makes the seller the wrong side.

**This cannot be tested on the local SPY/QQQ data** (index ETFs have no earnings). Testing it requires
single-stock option chains with real bid/ask plus a clean earnings-date calendar. **Until you have
that, do not trade earnings premium in either direction.** See §7 for what to acquire.

---

## 4. WHEN DOES LONG VOL PAY?

### 4.1 [OWN] Direct test: does low IV rank make buying volatility profitable?

Long **delta-hedged** ATM straddle bought at the real ask, SPY 45 DTE, sorted by the entry IV's
percentile rank over the trailing 24 monthly observations:

| IV rank quartile | n | mean % of premium | t | win % |
|---|---|---|---|---|
| Q1 lowest IV | 52 | **+0.56%** | +0.12 | 34.6% |
| Q2 | 49 | −20.28% | −4.63 | 18.4% |
| Q3 | 50 | −8.53% | −1.41 | 26.0% |
| Q4 highest IV | 51 | −3.39% | −0.76 | 33.3% |

QQQ, same test: Q1 lowest IV **−3.41% (t = −0.88)**.

**Interpretation.** Buying volatility at the lowest IV rank is the *only* long-vol configuration in
this entire report that is not significantly negative — and it is **zero**, not positive, and it does
not replicate on QQQ. Note also that the relationship is **not monotone**, which per this repo's own
methodology standard (`FINDINGS.md` §3) is the signature of noise rather than structure. The honest
reading: **low IV rank removes the negative carry; it does not create a positive expectancy.**
"Buy when IV rank is low" is a rule for *not losing*, marketed as a rule for winning.

### 4.2 [OWN] The one conditional signal with any life in it

Short delta-hedged straddle sold at the bid, sorted by **entry IV minus trailing 20-day realized vol**
(the Goyal-Saretto vol-spread signal):

| quartile | SPY mean / t | QQQ mean / t |
|---|---|---|
| Q1 low | +3.85% / 0.53 | +1.88% / 0.36 |
| Q2 | +2.38% / 0.42 | +0.05% / 0.01 |
| Q3 | +3.66% / 0.70 | −0.81% / −0.18 |
| **Q4 high** | **+7.35% / 1.81** | **+8.27% / 2.82** |

The top quartile is the best cell in **both** markets. This is the only conditional result in this
report that survives a second market. **But** SPY and QQQ are ~90% correlated, so this is not two
independent tests — it is closer to one test with a noisy replicate.

**Two decoys I am flagging so they do not get traded.** Sorting by the *absolute* entry IV level gives
Q3 = **+14.44% (t = 4.74)** on SPY and **+13.27% (t = 4.48)** on QQQ, and 2-yr IV rank gives Q2 =
+19.08% (t = 4.39) on SPY. Both are **non-monotone** — the effect sits in a middle bucket with nothing
either side. Per `FINDINGS.md` §3 ("adjacent-cell collapse is the signature of noise") these are
multiple-testing artefacts and I am recording them here specifically so nobody rediscovers them and
believes them. A t = 4.7 in a middle quartile of a 4-way sort, run across ~6 signals, is a bug report.

### 4.3 [LIT] What the literature offers on timing long vol

- **Goyal & Saretto (2009, *JFE*)** — the IV-minus-historical-vol spread predicts the cross-section of
  equity straddle returns; large reported long-minus-short monthly returns. The persistent critique is
  that the effect concentrates in small, illiquid, wide-spread names, i.e. the same cross-section as
  the earnings result. Same caveat, same Muravyev-Pearson counterweight.
- **Simon & Campasano (2014, *J. Derivatives)*** — the VIX futures basis predicts VIX futures returns;
  the tradeable version is short VIX futures in contango, i.e. **another short-vol trade**, not a
  long-vol timing rule.
- **Bollerslev, Tauchen & Zhou (2009, *RFS*)** — the variance risk premium **predicts equity returns**.
  Note what this is and is not: it is a signal for *equity* timing, not evidence that long vol pays.
  A high VRP means selling vol is *better* rewarded, not worse.
- **Dew-Becker & Giglio (2025)** — option alphas indistinguishable from zero over the last 15 years,
  **zero cumulative return on traded puts Mar 2009 – Dec 2022**. Long vol did not pay even across a
  window containing Feb 2018, Q4 2018, Mar 2020 and 2022.

**I could not find, and did not produce, any credible evidence of a conditional regime in which buying
index straddles or strangles has a positive expected return net of real costs.** Long vol is a hedge
with negative carry. Its justification is portfolio-level (it pays when everything else does not), not
standalone expectancy. The honest framing is Israelov's: you are buying insurance, and insurance has a
premium; the question is whether you need it, not whether it is profitable.

### 4.4 Pre-event accumulation on index products

The mechanism that makes the earnings result work (uncertainty under-priced *before* a scheduled
event) has an index analogue in FOMC/CPI. But note the asymmetry: the earnings result is about
**single-stock, firm-specific, poorly-covered** uncertainty. FOMC and CPI are the most-analysed
scheduled events in existence, covered by every desk on the street. The prior should be that index
event vol is efficiently priced or *over*-priced. This is testable on the local data — see §7, Test E.

---

## 5. SHORT STRANGLE RISK — quantified on real quotes

### 5.1 [OWN] The tail, in multiples of the credit collected

SPY, 45 DTE, sold at the bid, held to expiry, 213 monthly trades 2008-2025. `scripts/straddle_tails.py`.

**16-delta strangle — 8 worst months:**

| entry | expiry | SPY move | credit | payoff | **loss × credit** | loss × margin |
|---|---|---|---|---|---|---|
| 2020-02-04 | 2020-03-20 | **−30.5%** | $3.02 | $79.20 | **25.2×** | 1.16× |
| 2011-07-06 | 2011-08-20 | −15.9% | $1.22 | $13.36 | 9.9× | 0.45× |
| 2008-09-03 | 2008-10-18 | −27.1% | $3.43 | $24.79 | 6.2× | 0.84× |
| 2017-12-05 | 2018-01-19 | **+6.5%** | $1.51 | $10.41 | 5.9× | 0.17× |
| 2023-10-31 | 2023-12-15 | **+12.2%** | $4.31 | $28.33 | 5.6× | 0.29× |
| 2015-12-01 | 2016-01-15 | −10.9% | $1.75 | $10.19 | 4.8× | 0.20× |
| 2022-04-05 | 2022-05-20 | −13.6% | $5.18 | $25.37 | 3.9× | 0.22× |
| 2013-04-03 | 2013-05-18 | +7.5% | $1.22 | $5.94 | 3.9× | 0.15× |

**Note rows 4, 5 and 8: three of the eight worst months were caused by the market going UP.** The
short strangle is not a bearish-crash trade, it is a short-gamma trade, and a melt-up kills it too.

| structure | months losing >1× credit | >5× credit | worst | **3 worst months, as × mean monthly credit** |
|---|---|---|---|---|
| ATM straddle | 12 / 213 (5.6%) | 1 | 6.6× | **13.3×** |
| 30-delta strangle | 24 / 213 (11.3%) | 2 | 13.4× | **23.8×** |
| 16-delta strangle | 22 / 213 (10.3%) | **5** | **25.2×** | **41.4×** |

**The concentration statistic that matters most [OWN]:** total return of the 16-delta short strangle
program over the full 18 years is **+4016%** of credit summed across trades. **Excluding just the 3
worst months out of 213, it is +8156%.** *Three months out of 213 destroyed half of everything the
strategy ever earned.* For the ATM straddle it is worse: **+498% total vs +1831% ex-3-worst — the three
worst months consumed 73% of all profit ever made.**

This is the precise, real-quote version of "picking up nickels in front of a steamroller," and it is
why win rate is a meaningless statistic here. The 16-delta strangle **wins 76% of the time and its mean
is not statistically distinguishable from zero.**

### 5.2 [OWN] You get liquidated before you get to be right

This is the number that actually decides whether a small account survives. `scripts/straddle_mae.py`
computes the **maximum adverse excursion** — the worst daily mark-to-market during the life of the
trade, valued at the real cost to close (both legs at the ask) — against the terminal outcome.

SPY ATM short straddle, 45 DTE, n = 213:

| percentile | worst intra-trade mark (% of credit) | terminal outcome (% of credit) |
|---|---|---|
| mean | **−51.4%** | +2.2% |
| median | −31.6% | +18.2% |
| 5th pct | −170.3% | −118.1% |
| min | **−668.7%** | −660.2% |

- **26 of 213 trades (12.2%) were marked worse than −100% of credit at some point.**
- **6 of those ended profitable.** You had to sit through a loss exceeding the entire credit and come
  out the other side.
- 2 trades were marked worse than the *entire posted 20%-notional margin*.

**The Volmageddon case, specifically [OWN].** Short ATM straddle entered 2018-01-02, expiring
2018-02-16 — the cycle containing 5 Feb 2018:

| entry | expiry | credit | **worst mark** | **terminal** |
|---|---|---|---|---|
| 2018-01-02 | 2018-02-16 | $5.90 | **−211.8% of credit** | **+30.7% of credit** |

And March 2020, entered 2020-03-03: worst mark **−213.8% of credit / −90.1% of posted margin**,
terminal **+47.2%**.

**Both of those trades made money and both would have destroyed a small account**, because at −90% of
posted margin you are not sitting there thinking about theta — you are being liquidated by risk
management at the worst tick, in a market where the strangle you need to buy back is quoted at
whatever the market maker feels like. Terminal-outcome backtests of naked short premium — including
the ones in §1.2 of this document — **systematically overstate what a retail account would actually
have realised**, because they assume infinite margin tolerance and zero forced liquidation.

### 5.3 [LIT] The documented ruin cases

- **LJM Preservation & Growth Fund, Feb 2018.** A short-strangle mutual fund. NAV fell from $9.67 to
  $1.94 in **48 hours** (2018-02-05 → 2018-02-07) — **~80%**, roughly **$650M of $812M in assets**.
  Fund dissolved March 2018. SEC filed a civil complaint in 2021 against LJM Funds Management, LJM
  Partners, Anthony Caine and Anish Parvataneni, alleging the strategy was misrepresented
  ([SEC PR 2021-89](https://www.sec.gov/newsroom/press-releases/2021-89),
  [complaint](https://www.sec.gov/files/litigation/complaints/2021/comp-pr2021-89.pdf)). Note the
  fund's name contained both "Preservation" and "Growth" for a strategy with unlimited downside and
  capped upside.
- **OptionSellers.com / James Cordier, Nov 2018.** Naked short calls on natural gas futures. Gas +18%
  on 2018-11-14. ~**$150M lost across ~290 client accounts**, and — the point of the example —
  **accounts went to negative equity**: clients received margin calls and were left owing money to the
  clearing FCM (INTL FCStone) *after* full liquidation. **With undefined risk, "losing everything" is
  not the floor.**
- **Feb 2018 more broadly:** VIX +115% in a single session, XIV terminated. Note the mechanism
  carefully — Volmageddon destroyed **short-VIX-futures** products and **mark-to-market leveraged**
  short-vol books. As [OWN] §5.2 shows, a plain SPX/SPY short straddle held to the Feb expiry actually
  *made money*. **The lesson from Feb 2018 is about leverage, margin and forced liquidation, not about
  terminal payoffs.**

### 5.4 Margin, and why it is worse than the P&L suggests

Reg-T naked short option margin (CBOE/OCC): **20% of the underlying value, minus the out-of-the-money
amount, plus the option premium, with a floor of 10% of underlying** — computed on the greater side of
the strangle, plus the premium of the other side. Three things follow:

1. **The requirement is proportional to notional, not to the credit.** [OWN] a 16-delta SPY strangle
   collects ~1.0% of spot in credit against ~20% of spot in margin. Your gross yield is ~5% of margin
   per cycle before any losses.
2. **It expands exactly when you can least afford it.** As spot moves toward your strike the OTM offset
   shrinks and the premium leg grows; brokers additionally raise house requirements in a vol spike, and
   SPAN requirements for futures options multiplied in Feb 2018 and Mar 2020. Margin is
   **pro-cyclical**: it grows fastest at the exact moment your mark is worst.
3. **Small accounts get the worst of it.** Under $25k you will typically be denied naked-write
   permissions entirely; if granted, one 16-delta SPY strangle at spot 620 requires **~$12,400** of
   margin to collect **~$300**, so a $5,000 account **cannot hold even one contract**. Portfolio margin
   requires **$125,000 minimum equity** and is precisely the regime that lets you take enough size to
   be destroyed by the March-2020 tail in §5.1.

**Ruin probability, concretely [OWN].** With 1 of 213 monthly 16-delta strangles losing 25× the credit,
and the posted margin covering only ~1.2× the credit-multiple of that loss, a program sized to
**fully collateralise one contract** survives (barely — it lost 116% of margin in March 2020, i.e. it
went to negative equity on that trade). A program sized at **2× that** — still only 40% of notional,
which sounds conservative — **is bankrupt**. There is no position size at which a naked short strangle
program is both meaningfully profitable and safe, because the mean return per unit of margin
(~1.0-1.5%/month, t ≈ 1.2-1.5, i.e. **not statistically distinguishable from zero**) does not justify
any leverage at all.

---

## 6. STRIKE, DTE AND MANAGEMENT — evidence vs folklore

### 6.1 Who is telling you what, and who profits

| Source | Affiliation | Conflict |
|---|---|---|
| tastytrade / tastylive | **Owns tastytrade brokerage** | Revenue is per-contract and per-trade. Every rule it promotes — 45 DTE entry, 21 DTE management, 50% profit targets, rolling — **increases trade count**. Its research is in-house, not peer-reviewed, rarely publishes full methodology or fill assumptions. |
| CBOE benchmark indices (PUT, BXM, CNDR, BFLY) | **Exchange** | Profits directly from options volume. Indices are computed at **settlement/VWAP prices, not tradeable fills**, and assume perfect monthly rolls with no slippage. Useful as a shape reference, invalid as an achievable return. |
| OptionAlpha, Option Alpha backtester | Brokerage-integrated / subscription | Monetised on trade volume and subscriptions. |
| spintwig | Independent, affiliate-monetised | Uses real quotes and publishes methodology — the best of the practitioner sources, but not peer-reviewed and monetised via broker affiliate links. |
| ORATS | Commercial data vendor | Sells the data used to justify the trades. |
| Coval-Shumway, Bakshi-Kapadia, Broadie-Chernov-Johannes, Goyal-Saretto, Xing-Zhang, Muravyev-Pearson, Driessen-Maenhout-Vilkov, Dew-Becker-Giglio | Academic, peer-reviewed | No trade-volume conflict. **These almost all test delta-hedged positions** (see §2). |

**The 30-45 DTE folklore has no peer-reviewed support that I could find.** It originates in brokerage
marketing. The theoretical case for it is also weaker than presented: for an ATM option the **theta/
gamma ratio is approximately invariant in DTE** — per unit of gamma risk you are paid approximately the
same theta whether you sell 7-day or 60-day options. Short-dated options decay faster *and* carry more
gamma risk per dollar of premium, in roughly offsetting proportion. So "45 DTE is optimal" is not a
theorem; it is a preference, and it happens to be the preference that generates ~12 round trips a year
per position rather than 4.

### 6.2 [OWN] What the real quotes actually say about DTE

SPY ATM straddle short at bid, held to expiry, same 213-ish trades per row:

| entry DTE | mean % of credit | t | win % | on margin | t |
|---|---|---|---|---|---|
| 45 | +2.21% | 0.40 | 58% | +1.02%/cycle | 0.77 |
| 30 | +3.30% | 0.47 | 63% | +1.43%/cycle | 1.20 |
| 21 | +2.74% | 0.52 | 60% | +0.39%/cycle | 0.40 |

16-delta strangle, on margin: 45 DTE **+1.49% (t 1.49)**, 30 DTE **+1.38% (t 1.53)**, 21 DTE **+0.81%
(t 1.13)**. 30-delta strangle: 45 DTE +1.51% (t 1.25), 30 DTE **+1.80% (t 1.69)**, 21 DTE +0.63%.

**Verdict: there is no DTE optimum in this data.** It is a plateau from ~30 to ~45 with a mild sag at
21, all cells statistically indistinguishable from each other and from zero. Anyone reporting a sharp
optimum at "45 DTE" is reporting noise or selling something. Per `RULES.md` §0, a plateau is what a
real effect looks like; a spike is what a fitted one looks like — here we have a plateau *at
approximately zero*, which is the least useful kind.

### 6.3 [OWN] Does taking profit at 50% help? Does managing at 21 DTE?

SPY ATM straddle, 45 DTE entry, n = 213, real quotes (exit priced at the **ask**, as a short must pay):

| management rule | mean % of credit | t | win % | **sd** | worst |
|---|---|---|---|---|---|
| hold to expiry | **+2.21%** | 0.40 | 58% | 81.4% | **−660%** |
| close at 21 DTE | +1.78% | **0.68** | 66% | **38.3%** | **−212%** |
| take profit at 50% of credit, else hold to expiry | **−0.23%** | −0.04 | 61% | 77.3% | −660% |

QQQ: hold to expiry **−4.17%**, close at 21 DTE **+0.48%**, TP-50% **−3.61%**.

**Two clean results, both actionable:**

1. **The 50% profit target made the trade WORSE.** Mean fell from +2.21% to −0.23% on SPY and stayed
   negative on QQQ, while the standard deviation barely moved (81.4% → 77.3%) and the worst trade was
   **completely unchanged at −660%** — because the target only ever fires on winners. The take-profit
   hit **40.4%** of the time. You are capping your winners at half while leaving every loser fully
   intact, and paying a second round of spread on 2 legs to do it. **[OWN] that second crossing costs
   ~0.5% of premium on SPY** and far more on anything less liquid. This is folklore, and on real quotes
   it is negative-value folklore.
   *Caveat stated honestly:* my implementation does not redeploy the freed capital into a new position.
   A version that re-enters would earn additional cycles at the same ~zero expectancy, so the
   conclusion does not flip; it just adds turnover.
2. **"Manage at 21 DTE" has genuine support — but for risk, not for return.** Mean falls slightly
   (+2.21% → +1.78%) while the standard deviation **halves** (81.4% → 38.3%) and the worst trade
   improves from **−660% to −212%**. The t-statistic *improves* from 0.40 to 0.68. This is the one
   piece of tastytrade folklore that this data supports, and the reason is mechanical and sound:
   **you are exiting before the final three weeks, where gamma is highest and the payoff is most
   convex against you.** It is a real risk-management rule that happens to be promoted by a party that
   profits from the extra trade.

### 6.4 [OWN] Strike selection: 16 vs 30 delta

Restating §1.2 because it is the direct answer: **expectancy as a % of credit scales with how far OTM
you go (+2.2% ATM → +9.3% at 30-delta → +18.9% at 16-delta), win rate rises (58% → 62% → 76%), and
return per unit of margin is flat (~1.0-1.5%/month) while the worst month gets 4× worse (−660% →
−1336% → −2523% of credit).** Delta selection is a dial that trades win rate against tail severity at
constant, statistically-insignificant expected return. **The general practitioner claim that "risk-
adjusted return is roughly flat across delta" is confirmed here on real quotes.** Choose based on which
failure mode you can survive, not on which backtest looks best.

---

## 7. COST ACCOUNTING — the 2-leg spread drag, with real numbers

**[OWN] `scripts/straddle_costs.py`, real EOD NBBO, monthly expirations, SPY 2008-2025 (n = 11,251
structure-days). `spr_pct = (ask_total − bid_total) / mid_total` = the FULL round-trip cost of entering
at the far touch and exiting at the far touch, as a % of the mid premium. Half of it is one-way.**

| DTE bucket | ATM straddle | 30-delta strangle | 16-delta strangle |
|---|---|---|---|
| 0-7 | 2.63% (mean 6.24, p90 15.6) | 3.59% (mean 8.17) | **5.63% (mean 10.47, p90 25.8)** |
| 8-20 | 1.45% | 2.00% | 3.02% |
| **21-35** | **1.13%** | **1.52%** | **2.25%** |
| **36-50** | **1.05%** | **1.37%** | **2.08%** |
| 51-75 | 1.00% | 1.29% | 2.04% |

(medians; means and p90 in parentheses where informative)

**SPY ATM straddle, 21-50 DTE, round-trip spread as % of premium, by year — spreads have collapsed:**

| 2008 | 2010 | 2013 | 2016 | 2019 | 2021 | 2023 | 2025 |
|---|---|---|---|---|---|---|---|
| 2.46% | 1.36% | 1.29% | 1.12% | 0.64% | 0.36% | 0.31% | 0.46% |

Median dollar spread on a 30-45 DTE SPY ATM straddle is now **$0.05-0.10 on a ~$16-22 premium.**

**Full cost stack for one SPY ATM straddle at 45 DTE [OWN]:**

| cost item | as % of premium |
|---|---|
| one-way entry drag (cross both legs once) | **0.54%** (median 0.48%) |
| full round trip (cross both legs, both ways) | **1.09%** (median 0.95%) |
| daily stock delta-hedging @ 1bp | 1.05% |
| commissions, $0.65 × 2 legs on an $8.90 premium | 0.15% |
| **held-to-expiry short: total** | **~0.7%** (entry + commission; expiry costs nothing) |
| **round-tripped, delta-hedged: total** | **~2.3%** |

### The conclusions that follow, and they matter

1. **On SPY, transaction costs are NOT why long straddles lose.** The full round trip is ~1.1% of
   premium against a measured long-side expectancy of **−3% to −5%**. Costs explain roughly a fifth of
   it. **The rest is the variance premium — it is a real economic loss, not a friction.** This is the
   opposite of the 0DTE condor situation in `FINDINGS.md` §1, where the modelled edge was entirely a
   wing-mispricing artefact. Here the negative expectancy is genuine.
2. **The cost story is completely different at 0DTE.** The same ATM straddle at 0-7 DTE has a **2.63%
   median and 6.24% mean** round trip (16-delta strangle: **5.63% median, 10.47% mean, 25.8% at the
   90th percentile**), because the premium in the denominator has collapsed. **Short-dated structures
   are where spread drag actually kills strategies**, which is consistent with everything in
   `FINDINGS.md`.
3. **Scaling to other products.** These are SPY numbers — the most liquid option in the world, penny-
   quoted. SPX/SPXW is nickel- or dime-quoted on much larger premiums (broadly comparable in
   percentage terms, better on commission-per-notional, and cash-settled with 60/40 tax treatment).
   **Single-stock options are far worse: routinely 5-15% of premium round-trip on a mid-cap, worse into
   earnings when spreads widen.** This is the single biggest reason to distrust the earnings straddle
   literature's midpoint returns (§3.3).
4. **[LIT] Muravyev & Pearson (RFS 2020):** effective spreads for execution-timing traders are **<40%
   of quoted**. So all of the above are **upper bounds** for a patient trader using limit orders inside
   the spread. This strengthens conclusion 1 (costs matter even less than shown) and weakens the
   standard "costs kill everything" dismissal — but does not save a −5% gross expectancy.

---

## 8. WHAT YOU CAN TEST RIGHT NOW ON `data/opt_eod/` — precise specifications

Everything in §1.2, §2, §4.1, §4.2, §5.1, §5.2, §6.2, §6.3, §6.4 and §7 **has already been run** on
these files; the scripts are in `scripts/` and are re-runnable:

| script | what it produces |
|---|---|
| `scripts/straddle_extract.py {SPY,QQQ}` | compact monthly-expiration slice (delta-filtered) |
| `scripts/straddle_extract_full.py {SPY,QQQ}` | full monthly slice with paths, for managed exits & hedging |
| `scripts/straddle_costs.py {SPY,QQQ}` | the real NBBO spread census (§7) |
| `scripts/straddle_backtest.py {SPY,QQQ}` | hold-to-expiry expectancy by structure × DTE (§1.2, §6.2) |
| `scripts/straddle_hedged.py {SPY,QQQ} {DTE}` | delta-hedged vs naked, managed exits (§2, §6.3) |
| `scripts/straddle_program.py {SPY,QQQ} {DTE}` | program Sharpe/DD, cost stack, conditional sorts (§1.3, §4) |
| `scripts/straddle_tails.py` | worst-month tail table (§5.1) |
| `scripts/straddle_mae.py` | max adverse excursion / margin-call analysis (§5.2) |

**Note: `IWM` is listed as available in the lambdaclass source (2008-2025) but is not yet downloaded
locally.** Acquiring it is the highest-value cheap next step, because it is the only *genuinely
independent-ish* index replicate available (small-cap, different vol regime, ~0.8 correlation to SPY
rather than QQQ's ~0.9).

### The tests still worth running, with full specifications

**Test A — IWM replication of the delta-hedged short straddle. [priority: high, cost: low]**
- *Why:* §2's headline (+4.31% of premium, t = 1.53) needs a third market that is not 90% correlated
  with the first two. IWM is the best available.
- *Entry:* monthly third-Friday expirations; the trading day whose DTE is closest to 45 (tolerance ±5).
  Strike = nearest to spot close. Sell call + put **at the bid**.
- *Hedge:* short `delta_call + delta_put` shares at the close; rehedge daily at the close; charge 1bp
  of traded notional each rehedge.
- *Exit:* hold to expiry, settle at intrinsic on the last trading day's close.
- *Statistic:* mean per-trade return as % of mid premium; t-stat on ~215 non-overlapping trades;
  Sharpe on a 20%-notional margin base; compare against IWM buy & hold over the identical windows.
- *Decision rule:* if IWM's delta-hedged short is positive with t > 1 **and** the vol-spread Q4 sort
  (§4.2) also puts its best cell on top, the effect is worth a paper sleeve. If IWM is flat or
  negative, treat §2 as an SPY/QQQ-specific artefact and stop.

**Test B — does the vol-spread signal (§4.2) survive a proper 3-way split? [priority: high]**
- *Why:* Q4 of `IV − trailing 20d RV` is the only conditional cell that replicated across markets
  (SPY +7.35% t 1.81, QQQ +8.27% t 2.82). Per `FINDINGS.md` §3, two-way evidence is not enough after
  searching, and I sorted ~6 signals.
- *Spec:* discovery on 2008-2014, validate on 2015-2019, test on 2020-2025, **never re-tuned**. Signal
  computed with `expanding().mean()` / past-only data, never a whole-sample `transform` (the exact bug
  in `FINDINGS.md` §3). Structure: delta-hedged short ATM straddle sold at bid, 45 DTE.
- *Decision rule:* the top quartile must be positive on **all three** splits, and the sort must be
  approximately **monotone** — a middle-bucket spike is the §4.2 decoy pattern and must be rejected.

**Test C — the intra-trade margin-survival simulation. [priority: high, and it is the one that decides
whether any of this is tradeable for you]**
- *Why:* §5.2 shows 12.2% of trades marked worse than −100% of credit and 6 profitable trades that
  passed through that state. Every expectancy number in this report assumes you never get liquidated.
- *Spec:* for each trade, walk the daily path; at each close compute the Reg-T naked requirement
  (20% of underlying − OTM amount + premium, floored at 10%, greater side + other side's premium);
  simulate an account of $X; force liquidation at the ask when equity < maintenance; record the
  realised P&L **including forced exits**. Sweep X ∈ {$25k, $50k, $100k, $250k} for 1 contract.
- *Statistic:* the gap between terminal-outcome expectancy and liquidation-aware expectancy, and the
  account size at which that gap closes.
- *Prediction to falsify:* the liquidation-aware expectancy will be materially worse than +1.0%/month
  and the required account size for even one contract will be uncomfortable.

**Test D — is the 21-DTE management rule real or a 2-market coincidence? [priority: medium]**
- *Spec:* sweep the management DTE over {7, 14, 21, 28, 35} on SPY, QQQ and IWM, with the exit priced
  at the real ask. Report mean, sd, t and worst trade for each.
- *Decision rule:* per `RULES.md` §0, look for a **plateau**, not a spike. If the sd reduction is
  monotone in the exit DTE (it should be — it is mechanical gamma avoidance) and the mean is flat, the
  correct statement is "exit early to cut variance," not "21 is special."

**Test E — pre-event long vol on index products (FOMC / CPI). [priority: medium]**
- *Why:* the Xing-Zhang earnings mechanism (uncertainty under-priced *before* a scheduled event) has an
  index analogue that is directly testable here, and §4.4 argues the prior should be negative.
- *Spec:* buy a **delta-hedged** ATM straddle at the ask, 20-30 DTE, N trading days before a scheduled
  FOMC or CPI release (sweep N ∈ {1, 3, 5}); close at the **bid** on the day of / day after the
  release. Requires an FOMC/CPI date file — `fomc_research.py` and `intraday_macro.py` already exist in
  this repo and likely have the calendar.
- *Statistic:* mean return as % of premium, t-stat, and — critically — the same statistic on a
  **matched control** of non-event windows of identical length. The event result must beat the control,
  not zero. (This is the `RULES.md` §0 control discipline; without it you will rediscover the general
  negative carry and call it an event effect.)
- *Honest prior:* I expect this to be **negative or zero**. FOMC/CPI are the most-analysed scheduled
  events in existence; the reason earnings work for Xing-Zhang is *thin coverage*, which is the exact
  opposite condition.

**Test F — 0DTE / weekly straddle spread drag vs the gamma gate. [priority: low-medium]**
- *Why:* §7 shows the ATM straddle round trip explodes to 2.63% median / 6.24% mean at 0-7 DTE. Since
  `RULES.md` §1.1 established that realized/implied is **0.843× on high-gamma days**, the short-vol
  edge on those days is ~16% of implied — worth testing whether it clears a 6% mean round-trip cost.
- *Spec:* join prior-close GEX z-score to SPY weekly/0DTE ATM straddles; short at the bid on
  `gz > +0.5` days; compare against the unconditional control. **This is a direct extension of the one
  validated finding in this repo** and is the only place where a straddle has a *conditioning variable
  known not to be in the implied vol*.
- *Warning:* `FINDINGS.md` §1 already showed the condor version of this collapsed on real SPXW quotes.
  Expect the same. Run it to close the question, not because it will work.

### What CANNOT be tested on these files

- **The earnings crush trade (§3)** — SPY/QQQ/IWM have no earnings. This requires **single-stock option
  chains with real bid/ask** plus a clean earnings-date calendar with before/after-market flags. Given
  §3's conclusion that the effect concentrates in illiquid small caps, the dataset must include
  small-caps with their real (wide) spreads or the test is worthless. **Do not proxy this with a model.**
- **Intraday execution / the actual fill you would get.** These are EOD closing NBBO. Muravyev-Pearson
  says a patient trader does better; a market order at 15:59 does worse.
- **SPX-specific effects** — cash settlement, no early assignment, 60/40 tax treatment, and AM-settled
  monthly quirks. The repo does have `data/spxw/data_opt.parquet` (1.37M rows of real SPXW quotes,
  2016-2024, 30-min grid) but it is 0DTE-focused, not swing.

---

## 9. VERDICT

| structure | credible positive expectancy after real costs? | under exactly what conditions | honest risk profile |
|---|---|---|---|
| **LONG straddle** (index, swing) | **NO.** [OWN] −3.3% to −4.4% per trade at the real ask, SPY 2008-2025, n=213, t≈−0.6; delta-hedged −5.40%, t=−1.92. [LIT] Coval-Shumway −3%/wk; Xing-Zhang single-stock −2.08%/wk (t=−42); Broadie-Chernov-Johannes −15.7%/mo. Costs are only ~1.1% of premium, so **this is a genuine economic loss, not a friction.** | None found. Buying at the lowest IV-rank quartile takes the expectancy to **zero** (+0.56%, t=0.12) but not positive, and does not replicate on QQQ. | Defined risk, max loss 100% of premium. Loses ~60-80% of the time. Rational only as a **hedge with a known bleed**, sized as insurance, never as a return source. |
| **SHORT straddle, NAKED** (index, swing) | **NO — not statistically.** [OWN] +2.21% of credit at 45 DTE (t=+0.40), +3.30% at 30 DTE (t=+0.47); **+1.02%/month on margin, Sharpe 0.18**, vs SPY buy & hold Sharpe 0.64 over identical windows. **Negative in 2020-25** (−2.72%). QQQ: **−0.76%/mo, Sharpe −0.13.** | None that survived testing. The `IV − trailing RV` top quartile is the only live candidate (§4.2) and needs Test B. | **Undefined risk.** Worst month −660% of credit; 12/213 marked worse than −100% of credit intra-trade; 3 worst months consumed **73% of all profit ever made**. Skew −2.4, kurtosis 14.4. Sharpe is a lie for this payoff. |
| **LONG strangle** (index, swing) | **NO, and worse than the straddle.** [OWN] 16-delta at ask: **−20.5% per trade** at 45 DTE (t=−1.35), **−100% median** — the modal outcome is total loss. 30-delta: −10.7%. Round-trip spread is 2× the straddle's (2.08% vs 1.05% of premium). | None. | Defined risk; **loses 77-80% of the time**; the entire return distribution is a lottery ticket. The one honest use is a cheap convex hedge, and even then Dew-Becker & Giglio find **zero cumulative return on traded puts 2009-2022**. |
| **SHORT strangle, NAKED** (index, swing) | **NO — and this is the most dangerous "yes-looking" no in the report.** [OWN] 16-delta: **+18.85% of credit, 76% win rate** — and **t = 1.22, i.e. indistinguishable from zero**. On margin: +1.49%/month, t=1.49, the *same* as ATM. | None. The high win rate is not evidence; §1.2 shows it is purchased 1:1 with tail severity at constant expected return. | **The account-killer.** [OWN] worst month **−2523% of credit** (Mar 2020); 5 months lost >5× credit; **3 of 213 months destroyed half of all profits ever earned**; three of the eight worst months were caused by the market going **UP**. Margin is pro-cyclical and forced liquidation converts winning trades into ruin (§5.2: two trades marked at −211% and −214% of credit *ended profitable*). [LIT] LJM −80% in 48 hours; OptionSellers.com clients to **negative equity**. |
| **SHORT straddle, DELTA-HEDGED** (index, swing) | **CLOSEST TO A YES, AND STILL NOT SIGNIFICANT.** [OWN] **+4.31% of premium sold at the real bid, t = +1.53**, 70% win, n=213 SPY 2008-2025; QQQ **+2.38%, t=+1.08**. Positive in **all four sub-periods** but **monotonically decaying** (7.6 → 4.8 → 4.1 → 3.5). [LIT] this is the structure Broadie-Chernov-Johannes find significant against both nulls. | Requires **daily delta rehedging** (~1.05% of premium at 1bp), ATM strikes, ~30-45 DTE, and a margin buffer that survives a −140%-of-margin month. Best cell is the top `IV − trailing RV` quartile (§4.2), pending Test B. | Still short-gamma with a fat left tail (worst −190% of credit, skew −4.5, kurtosis 42) — but **3.5× less severe than naked**, and half the variance. **Sharpe 0.30 vs SPY buy & hold 0.64**: it is a diversifier at best, not an edge, and it should be labelled as such per `RULES.md` §4. |
| **EARNINGS crush trade** (single stock) | **NO evidence for SELLING; genuine [LIT] evidence for BUYING, unverified after costs.** Xing & Zhang (JFQA 2018): delta-neutral ATM straddles earn **+2.3% (highly significant) from 1 day before the announcement to the announcement date**, +0.31% to +2.30% across all windows — against **−2.08%/week unconditionally**. Their conclusion: **the market underestimates earnings uncertainty**, i.e. the premium *seller* is on the wrong side. | Effect concentrates in **small firms, low analyst coverage, high historical vol/jump frequency, volatile past surprises** — precisely the widest-spread options. Requires **delta-neutral** construction and a **pre-announcement exit**, not holding through. | **Unverified after costs and I could not verify it from the primary source.** Gross +2.3% vs single-stock round-trip spreads of 5-15% of premium is a losing arithmetic unless execution is exceptional. Compounding the problem: [LIT] single-stock VRP is **−1.35 vol points** with zero VRP unrejectable for **108 of 135 stocks** — there is no background premium to fall back on. **Do not trade this in either direction until tested on real single-stock quotes.** |

### The three sentences that matter

1. **If you want the variance premium, sell delta-hedged ATM straddles on an index, ~30-45 DTE, and
   rehedge daily** — that is the only structure with both academic support and a positive real-quote
   result here, and it is still only t = 1.53 over 18 years and still loses to buy-and-hold on Sharpe.
2. **Naked short strangles are the trade with the best-looking statistics and the worst actual
   properties in this entire report** — 76% win rate, zero expectancy, and a tail that took 25× the
   credit in a single month and would have margin-liquidated a small account twice.
3. **The earnings trade is the only genuinely open question, and the best evidence says retail has the
   sign backwards** — so the next data purchase should be single-stock chains with real bid/ask, not
   more index history.

---

## 10. Methodological notes carried forward

- **Win rate is not expectancy.** [OWN] the 16-delta strangle wins 76% of the time with t = 1.22. This
  is the same lesson as `FINDINGS.md` §2's call credit spread (57.9% win, exactly zero return), arrived
  at on a completely different structure.
- **A non-monotone quartile sort is noise.** §4.2 produced t = 4.74 and t = 4.48 in *middle* buckets on
  two markets. Recorded explicitly so they are not rediscovered and believed.
- **Compounding is invalid when single trades return worse than −100% of capital at risk.** Geometric
  equity curves on naked short premium go negative and produce meaningless CAGR/drawdown figures.
  Report additive equity in units of margin.
- **Terminal-outcome backtests overstate short-premium performance.** §5.2 quantifies the gap: mean
  worst intra-trade mark is **−51.4% of credit** against a mean terminal outcome of **+2.2%**. Any short
  premium backtest without a margin/liquidation simulation is optimistic by an unknown amount.
- **Always ask: real quotes or a model?** Restating `FINDINGS.md` §1 because it is the load-bearing
  lesson: the same structure showed +3.7%/trade modelled and −1.70%/trade on real SPXW bid/ask.
- **Always ask: delta-hedged or naked?** New, and it belongs next to the above. §2 shows the same
  trades give t = 1.72 hedged and t = 0.40 naked. Most published option-return results are hedged.
  Most retail trades are not.

---

*Sources: [Coval & Shumway, "Expected Option Returns", JF 2001](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00352) · [Xing & Zhang, "Anticipating Uncertainty: Straddles Around Earnings Announcements", JFQA 2018](https://www.ruf.rice.edu/~yxing/straddle_201305_03.pdf) · [Muravyev & Pearson, "Options Trading Costs Are Lower Than You Think", RFS 2020](https://academic.oup.com/rfs/article-abstract/33/11/4973/5732665) · [SEC v. LJM Funds Management et al. (PR 2021-89)](https://www.sec.gov/newsroom/press-releases/2021-89) · [SEC complaint](https://www.sec.gov/files/litigation/complaints/2021/comp-pr2021-89.pdf) · Bakshi & Kapadia RFS 2003 · Broadie, Chernov & Johannes 2009 · Bollerslev, Tauchen & Zhou RFS 2009 · Goyal & Saretto JFE 2009 · Driessen, Maenhout & Vilkov · Dew-Becker & Giglio, Chicago Fed WP 2025-17 · Simon & Campasano, J.Derivatives 2014*
