# Predicting Large Price Moves in Single Stocks (1–6 Weeks)

**Question:** what predicts the MAGNITUDE of a stock's move over the next 1–6 weeks, and is any
of it not already in the option price?

**Date:** 2026-08-15
**Data used:** DoltHub single-stock option chains + earnings + stock DBs on disk
(`data/dolt/{options,earnings,stocks}`), 2019-02 → 2026-08.
**Method:** literature review (4 parallel sweeps) + GitHub code sweep + **original measurement on
123,107 real far-OTM option trades and a 1.55M-row stock/IV panel.**

---

## 0. BOTTOM LINE

**Nothing in the published literature, in open source, or in your own data beats implied
volatility as a forecast of single-stock move magnitude at a 1–6 week horizon.** Every screen in
the brief — squeeze/compression, IV rank, HV−IV, short interest, unusual options activity,
attention, vol-of-vol — is either already priced, disproven, or folklore.

But the honest answer is more textured than "it's a null," and the texture is where the only
remaining opportunity lives:

1. **Far-OTM single-stock calls are approximately FAIRLY priced, not overpriced — but only where
   you can't afford to trade them.** On your data, 0.10-delta / 35-DTE calls bought at the ask and
   held to expiry returned **−45.6% on average (n=123,107, NW t = −7.13)**. Restrict to contracts
   with a quoted spread ≤ 20% of mid and the mean goes to **+5.6% (t = +0.98)** — statistically
   indistinguishable from zero. **The entire negative expectancy is the bid-ask spread.** This
   replicates your SPY result (25.6% win, +0.81%, t = +0.3) on 2,200 single names.
   The strategy does not die from a volatility risk premium. It dies from friction.
   *(Caveat: the published benchmark is worse than yours. Ni (2007) measures 1-month
   single-stock calls at K/S > 1.15 at **−36.86%/month at MIDPOINT, t = −4.86**. Your tradeable
   subset comes in near zero because the spread filter selects large, liquid, stable names — which
   Cao-Han and Zhan et al. independently identify as the corner where option buyers lose least.
   Read your +5.6% as a ceiling produced by selection, not as an edge.)*

2. **The far tail of single-stock returns is genuinely fatter than a lognormal at IV.**
   P(|21-day move| > 3σ_implied) is **3.6× the normal benchmark**, and > 4σ is **64×**. This is
   the real reason the trade isn't obviously dead — and it is exactly what the skew already
   charges you for. Bollerslev-Todorov measure the markup directly: far-OTM **calls** are priced as
   if +10% jumps were **~41× more frequent** than they actually are (puts, ~330×). The tail is
   real, it is fat, and it is already in the price — with a large margin on top.

2b. **The single-stock *diffusive* variance risk premium is much weaker than you feared, and that
   turns out not to help.** Carr-Wu: only **7 of 35** individual names have a significantly
   negative dollar VRP and **12 of 35 are positive**; short-vol Sharpe is 0.00–0.05 in single names
   vs **0.98** for SPX. Bakshi-Kapadia even find the delta-hedged underperformance *"decreasing for
   options away from the money."* So the headwind you actually assumed away is small. The problem
   is that a far-OTM option is not priced off diffusive variance — it is priced off the jump tail
   in point 2, where the markup is 41×.

3. **The one screen with a pulse is scheduled earnings inside the option's life** (+17.0% vs
   −13.4%, win 10.8% vs 8.8%, t = +1.78). Not significant. And the literature says the effect
   you'd be capturing is a **pre-announcement vega ramp, not the jump** — Gao-Xing-Zhang's +1.37%
   is earned in window [−3,−1] and vanishes to zero in [−3,+1].

4. **Earnings raise the middle of the move distribution but NOT the far tail.** With an earnings
   date in the window: P(>2σ) rises 3.86% → 4.96%, but **P(>3σ) FALLS, 1.00% → 0.91%.** Far-OTM
   options need 3σ. Earnings deliver 2σ. This is, on its own, close to a disqualifying finding for
   "buy far-OTM into earnings."

5. **The volatility-compression / squeeze premise is backwards.** Confirmed twice: on a 223-name
   large-cap panel, compressed names went on to move **7.29% vs 9.32%** over 21 days, with
   P(>10% move) of **23.4% vs 29.6%**. On your survivorship-free 2,211-name panel the effect is a
   flat null (Q4−Q0 in P(>2.5σ) = −0.0004, t = −0.40). Vol-shock half-life is ~100 trading days —
   *far* longer than your holding period. Low vol predicts low vol.

**If you build this, build it as an earnings-term-structure trade with a hard spread filter, and
expect zero.** The specification is in §7.

---

## 1. WHAT WAS ACTUALLY MEASURED (provenance)

Everything in §5–§6 is my own computation on your disk. It is worth stating the data quality
findings first, because two of them are landmines.

### 1.1 The DoltHub option chain is genuinely point-in-time and survivorship-free

`options.option_chain`: 114M+ rows, 2019-02-09 → 2026-08, ~1,600–1,720 optionable symbols per
snapshot. Columns: `date, act_symbol, expiration, strike, call_put, bid, ask, vol (IV), delta,
gamma, theta, vega, rho`.

Delisted names terminate exactly when they should:

| Symbol | Last chain date | Real event |
|---|---|---|
| TWTR | 2022-10-26 | taken private 2022-10-27 |
| SIVB | 2023-03-08 | failed 2023-03-10 |
| FRC  | 2023-04-28 | failed 2023-05-01 |
| ATVI | 2023-10-11 | acquisition closed 2023-10-13 |

**This is a survivorship-free universe.** That is rare and it is the single most valuable property
of this dataset. Any study you run on it does not have the "delete the disasters" bias.

**Critical limitation: there is NO volume and NO open interest column.** Unusual-options-activity
screens (category C in the brief) are **not testable on this data at all**. Do not build one and
pretend otherwise.

**Snapshot cadence is not daily until 2025:**

| Year | Snapshot dates | Cadence |
|---|---|---|
| 2019 | 48 | weekly |
| 2020–2023 | 151–156 | ~3×/week (M/W/F) |
| 2024 | 183 | mixed |
| 2025–2026 | 259 / 153 | daily |

Consequence: for an earnings study, the "day before the print" snapshot is 1–3 calendar days
before in 2020–2024. Usable, but you must measure and report the gap, not assume D−1.

### 1.2 `volatility_history` is the hidden gem

`options.volatility_history` (~1,600 symbols/day, 2019–2026) gives, precomputed and point-in-time:
`iv_current, iv_week_ago, iv_month_ago, iv_year_high, iv_year_low, hv_current, hv_week_ago,
hv_month_ago, hv_year_high, hv_year_low`.

That is **IV rank and the Goyal-Saretto HV−IV spread handed to you directly**, with no
reconstruction and no look-ahead. It is what made §5.3 possible in one pass.

Caveat: `iv_current` is a ~30-day ATM IV. It is **not** the earnings-event implied move. Confusing
the two is the central methodological trap in §6.

### 1.3 LANDMINE 1 — `stocks.ohlcv` is UNADJUSTED

```
NVDA 2024-06-07 close 1208.88
NVDA 2024-06-10 close  121.79     <- 10:1 split, raw prices
```

A naive |return| screen on this table finds a **−90% "jump" in NVDA** on 2024-06-10 and every
other split. If you are hunting large moves, you will find corporate actions and nothing else.
You must join `stocks.split`.

**I got the direction of this adjustment wrong on my first pass** — multiplied by the cumulative
ratio instead of dividing — which *amplified* every split gap 10×. The tell was that mean forward
21-day realized vol came out at **0.876 against a mean IV of 0.405**, which is not a market
anyone has ever traded. Fixed: `px = close / adj` where `adj = Π ratios with ex_date > t`.

### 1.4 LANDMINE 2 — the split table has ~33% duplicate rows

This one is worse, because it survives a sanity check.

```
GOOG,2022-06-30,20:1
GOOG,2022-07-18,20:1      <- only this one is real
DXCM,2022-05-18,4:1
DXCM,2022-06-10,4:1
DXCM,2022-06-13,4:1       <- only this one is real
AMZN,2022-05-26,20:1
AMZN,2022-06-06,20:1      <- only this one is real
```

Taking the naive product gives GOOG a cumulative adjustment factor of **400** instead of 20. Every
option on a mega-cap that split became a fake lottery win. The audit that caught it:

```
=== top 25 returns (BEFORE fix) ===
GOOG 2022-06-15 K=2540 ask $8.80  ->  "payoff" $42,566   ret = +4836%
```
GOOG closed at 2255 on 2022-07-15. The strike was 2540. **That call expired worthless.** Every one
of the top 25 winners had `adj_entry ≠ adj_expiry`, and the **top 10 trades accounted for 95% of
the entire P&L sum**.

Effect of the bug on the headline result:

| | mean return, all | mean return, spread ≤ 20% |
|---|---|---|
| with duplicate splits | −21.7% | **+199.6%** |
| price-validated splits | **−45.6%** | **+5.6%** |

A bogus +200% strategy, from a data table, with no modelling error anywhere in the backtest.

**Fix (use this):** treat the split table as a *candidate list only* and confirm each one against
the actual price gap — apply the split only if `close_prev / close_ex` is within ±25% of the
claimed ratio in log space. This rejected 1,309 of 3,935 rows and produced correct factors
(GOOG {1,20}, NVDA {1,10,40}, APH {1,2,4}). Script: `scratchpad/adjust.py`.

Residual unexplained |1-day move| > 60%: **0.085% of rows**. Flag and drop these; they are
unhandled corporate actions (reverse splits, spinoffs, special dividends), and they are precisely
the rows a jump-hunting screen will select.

### 1.5 LANDMINE 3 — the spread on the contracts you want to buy

Measured directly, ~35 DTE calls, five sample dates:

**Full universe (~1,600 names):**

| \|delta\| | n | % zero bid | avg mid | avg (ask−bid)/mid |
|---|---|---|---|---|
| < 0.03 | 10,104 | **84.9%** | $0.73 | **1.26** |
| 0.03–0.06 | 3,727 | 50.3% | $0.70 | 1.13 |
| 0.06–0.10 | 5,053 | 33.0% | $0.81 | **1.08** |
| 0.10–0.16 | 7,224 | 31.9% | $1.04 | 1.00 |
| 0.16–0.25 | 8,510 | 29.8% | $1.50 | 0.84 |

A relative spread of 1.0 means bid $0.50 / ask $1.50. **Round-tripping that contract costs 100% of
mid.** And 33–85% of far-OTM contracts have no bid at all.

**Restricted to 20 mega-liquid names (AAPL, MSFT, NVDA, TSLA, AMD, …), mid ≥ $0.50:**

| \|delta\| | avg (ask−bid)/mid |
|---|---|
| 0.06–0.10 | **0.186** |
| 0.10–0.16 | **0.167** |
| 0.16–0.25 | 0.130 |

So: **~17–19% of premium round-trip on the best names, 100%+ on the median name.** Plus ~$0.65–1.30
commission per contract (another 1–2% on a $100 premium). These are EOD quotes and may be wider
than intraday, but you cannot *assume* they are — model at the touch.

**This number is the whole ballgame.** A screen must beat random by more than ~20% of premium on
the best names to break even. Nothing in this document beats random by anything.

---

## 2. VOLATILITY / JUMP FORECASTING VS IMPLIED VOL

### 2.1 The variance risk premium — genuinely weak in single stocks

**This is the one place where your intuition is right and the folklore is wrong.** The 85% figure
is an *index* number. In single names the premium largely evaporates.

Measured on your own data (1.55M stock-days, 2,211 symbols, ADV > $5M, 2020–2026):

```
mean IV (30d ATM)                0.4047
mean subsequent 21d realized RV  0.3969        <- gap under 1 vol point
median RV/IV ratio               0.877
P(IV > subsequent RV)            0.676          <- 67.6%, not 85%
```

The published cross-section says the same thing, harder. **Carr & Wu (2009, *RFS*)**, 35 individual
stocks + 5 indices, 30-day synthetic variance swaps, 1996–2003 — mean (RV − SW) per $100 notional
and the Sharpe of *shorting* variance:

| | (RV−SW)×100 | t | short-vol Sharpe |
|---|---|---|---|
| SPX | −2.74 | −8.39 | **0.98** |
| NDX | −2.43 | −2.54 | 0.55 |
| single names (INTC, MOT, TXN, EMC, NOK, CIEN…) | **positive for 12 of 35** | — | **0.00–0.05** |

Their own sentence: *"out of the 35 individual stocks, only seven generate variance risk premiums
that are significantly negative at the 95% confidence level."* Twelve of thirty-five had realized
variance **exceeding** the swap rate on average.

And they give the mechanism — regressing mean log VRP on variance beta across all 40 assets:

> LRP = 0.0061 − 0.3283·β_V,  R² = 18.4%, t(slope) = −2.96

**The premium is compensation for *systematic* variance risk.** Names with low variance beta —
small, idiosyncratic, high-specific-risk — have essentially no VRP.
**Driessen-Maenhout-Vilkov (2009, *JF*)** complete the argument: index options are expensive
because *correlation* risk is priced; single-name idiosyncratic variance is not. Their own verdict
on trading it: the correlation risk premium *"cannot be exploited with realistic trading
frictions."*

One further point in your favour: **Bakshi & Kapadia (2003, *RFS*)** find delta-hedged ATM index
calls lose 0.13% of the index (~8% of option value) per hedging period — but state that *"the
underperformance is decreasing for options away from the money."* The **diffusive** vol premium is
an ATM phenomenon and it shrinks as you go OTM.

**So the diffusive headwind is small and shrinking in exactly the direction you want to trade.**
That is genuinely encouraging, and §2.4 is where it falls apart — because a far-OTM option is not
priced off diffusive variance.

### 2.2 The tail is fat — and this is the real reason the trade isn't obviously dead

Distribution of |21-day return| / (IV × √(21/252)), vs a driftless normal at that same IV:

| threshold | actual | normal | lift |
|---|---|---|---|
| > 1.0σ | 26.7% | 31.7% | **0.84×** |
| > 1.5σ | 10.8% | 13.4% | 0.81× |
| > 2.0σ | 4.22% | 4.55% | 0.93× |
| > 2.5σ | 1.84% | 1.24% | **1.49×** |
| > 3.0σ | 0.97% | 0.27% | **3.59×** |
| > 4.0σ | 0.40% | 0.006% | **63.5×** |

Read this carefully, because it is the single most informative table here.

- **Below 2σ the market is overpriced** (0.81–0.93× the normal frequency). This is the variance
  risk premium, and it is why every credit structure you tested was a *seller's* edge in the body
  and still lost — because the body is where the premium lives and the spread eats it.
- **Above 2.5σ the market is underpriced relative to a lognormal**, dramatically so in the extreme
  tail.

The naive inference — "so buy 3σ options" — is wrong, and §5 shows why empirically. The option
market does not price OTM strikes at the ATM IV; it prices them with **skew**, which is exactly a
markup for this fat tail. The measured near-zero return on tradeable far-OTM calls (§5.2) is the
skew being approximately *correct*. The fat tail is real, and it is already in the price.

### 2.3 HAR-RV and jumps: the predictable part is the part that doesn't pay you

Corsi (2009) HAR-RV works — but it is benchmarked **against GARCH, not against IV.** Almost no
paper runs the race you need. The two that matter:

**Andersen-Bollerslev-Diebold (2007) "Roughing It Up"** — S&P 500 futures, 5-min, 1990–2002.
Decomposing RV into continuous (C) and jump (J) components, HAR-RV-CJ in log form at **h = 22**
(your horizon):

| component | coefficient (se) |
|---|---|
| C daily | 0.162 (0.020) ✓ |
| C weekly | 0.274 (0.049) ✓ |
| C monthly | 0.403 (0.056) ✓ |
| **J daily** | **0.018 (0.031)** ✗ |
| **J weekly** | **0.198 (0.176)** ✗ |
| **J monthly** | **0.246 (0.201)** ✗ |

R² = 0.722 vs 0.727 for the model without the decomposition — **zero incremental gain.** Their own
words: *"the predictability in the HAR-RV realized volatility regressions is almost exclusively due
to the continuous sample path components."*

**A far-OTM option pays off on the jump component. That is the component with no predictability.**

**Busch, Christensen & Nielsen (2011, *J. Econometrics*)** ran the horse race that everyone else
skipped — forecasting RV over the next 22 days, 155 **non-overlapping monthly** periods, S&P 500:

| model | adj R² | **out-of-sample MAFE** |
|---|---|---|
| HAR on RV | 53.0% | 3.2011 |
| HAR on C and J (ABD-style) | 61.9% | 2.8250 |
| **IV alone** | 62.1% | **1.9912** |
| IV + RV components | 64.0% | 2.5089 |
| IV + C + J components | 68.2% | 2.2582 |

**IV alone has the lowest out-of-sample error by a wide margin, and adding any realized-volatility
information raises in-sample R² while degrading out-of-sample accuracy.** The IV coefficient is
**1.0585 (se 0.0667)** — statistically indistinguishable from 1, i.e. an **unbiased** forecast.

And for the jump component specifically, at monthly horizon:

| model | adj R² | OOS MAFE |
|---|---|---|
| past J only | **4.0%** | 1.1983 |
| past C and J | 6.2% | 1.1494 |
| **IV alone** | **8.0%** | **1.0042** |

Against **67.2%** R² for the continuous component. So: the jump component is ~10–17× less
predictable than the continuous component, **and within that sliver, IV beats every realized
measure both in and out of sample.** Their sentence: *"Implied volatility turns out to be the
strongest predictor of future jumps… even when the C and J components at all frequencies are
included."*

Corroborating, all pointing the same way:
- **Jiang & Tian (2005, *RFS*):** model-free IV *"subsumes all information contained in the
  Black–Scholes implied volatility and past realized volatility."*
- **Christensen & Prabhala (1998, *JFE*):** IV *"subsumes the information content of past
  volatility."*
- **Taylor, Yadav & Zhang (2008)**, 149 US firms: option forecasts beat historical-return forecasts
  for **86% of firms** over the option's life.
- **Patton & Sheppard (2015, *REStat*)**, S&P 500 + 105 individual stocks: signed jumps and
  semivariance give *"significantly better out-of-sample forecast performance"* — **against HAR
  benchmarks. They do not race against IV.** This is the trap in one sentence.
- **Christensen, Siggaard & Veliyev (2023, *JFE*):** ML beats HAR, and the explanation is
  *"higher persistence in the ML models, which helps approximate the long memory of realized
  variance."* ML wins by being **stickier** — one more nail in the squeeze premise.
- Rough volatility (Gatheral-Jaisson-Rosenbaum, H ≈ 0.1) improves RV forecasts, but rough-Bergomi
  calibration is badly conditioned in **low-volatility periods specifically** — the exact regime a
  compression screen operates in.

**There is no horse race in this literature that IV loses at your horizon.**

### 2.4 The jump-tail premium — the decisive negative result

§2.1 showed the *diffusive* variance premium in single stocks is near zero. It does not matter,
because a far-OTM option is priced off the **jump tail**, and that premium is enormous.

**Bollerslev & Todorov (2011, *JF*) "Tails, Fears and Risk Premia"** compare risk-neutral (Q) and
physical (P) jump intensities on the S&P 500. Mean annualized intensities:

| jump size | Q (priced) | P (actual) | **Q/P** |
|---|---|---|---|
| **> +7.5%** | 0.5551 | 0.0098 | **~57×** |
| **> +10%** | 0.2026 | 0.0050 | **~41×** |
| > +20% | 0.0069 | 0.0010 | ~7× |
| < −7.5% | 0.9888 | 0.0036 | ~275× |
| < −10% | 0.5640 | 0.0017 | ~330× |
| < −20% | 0.0862 | 0.0002 | ~430× |

**This answers the question you asked directly: the overpricing is NOT puts-only.** Far-OTM
**calls** are priced as if large upside jumps were ~41–57× more frequent than they are. Lottery
demand does not make OTM calls cheap — it is the reason they are rich. (Caveats: P-measure standard
errors are wide, and this is index, not single-stock. The authors explicitly reject the peso-problem
objection.)

**Kelly, Pástor & Veronesi (2016, *JF*)** show the same shape for scheduled events: options
spanning elections/summits are more expensive by **5.1% ATM, 9.6% at 5% OTM, 16.0% at 10% OTM** —
**the event premium increases monotonically with moneyness.**

### 2.5 The realized returns, in single stocks, at your exact horizon

This is the part of the literature that maps one-to-one onto your trade, and it is uniformly bad.

**Ni (2007/2009) "Stock Option Returns: A Puzzle"** — individual-stock calls, 1-month, held to
maturity, **priced at bid-ask midpoints**, Jan 1996 – Jun 2005:

| strike group (K/S) | 1 | 2 | 3 | 4 | **5 (K/S > 1.15)** |
|---|---|---|---|---|---|
| mean 1-month return | +2.31% | +2.50% | +1.98% | −10.15% | **−36.86%** |
| t | (1.01) | (0.72) | (0.37) | (−1.52) | **(−4.86)** |

**−36.86% per month at MIDPOINT**, worse at the ask, in a *rising* market, in a window with an
above-average frequency of large stock moves. She tests and rejects the peso explanation. Sorting
by BS delta gives −29.78% (t = −3.87).

Ni's double-sort identifies the driver as skewness, not volatility: sorting on idiosyncratic
skewness, call returns run **+5.74%** (lowest) to **−21.53%** (highest) per month, and
*"call returns are no longer decreasing in volatility after controlling for idiosyncratic
skewness."*

**Boyer & Vorkink (2014, *JF*) "Stock Options as Lotteries":** differences in average returns for
option portfolios sorted on ex-ante skewness range from **10% to 50% per week**. Far-OTM
single-stock calls are the highest-ex-ante-skewness options in existence.

**Cao & Han (2013, *JFE*):** delta-hedged ATM equity call returns average **−0.81%/month**, and are
negative in **every** idiosyncratic-volatility quintile. Critically: *"the value-weighted portfolio
return differences are only about half the magnitude of the equal-weighted results… our results are
stronger among smaller stocks."*

**Zhan, Han, Cao & Tong (2022, *RFS*) "Option Return Predictability"** screen a large
characteristic set against delta-hedged equity option returns. Ten survive costs. **Every single
profitable strategy is *writing*.** The characteristics predicting the best returns for option
**buyers** are the mirror decile: high stock price, high profit margin, high profitability, low
cash-flow variance, low distress risk, **low analyst dispersion**. That is, buying options is least
bad on large, profitable, stable, boring companies — **the exact opposite of the high-uncertainty
names a big-move screen selects.**

**Constantinides, Czerwonko, Jackwerth & Perrakis (2011, *JF*)** apply formal stochastic-dominance
bounds net of transaction costs, 1983–2006: *"violations of the lower bounds by ask prices are
**infrequent**."* Over 23 years, options were routinely too expensive to hold and only rarely cheap
enough to buy once you pay the ask.

**Bryzgalova, Pavlova & Sikorskaya (2023, *JF*):** retail is now >60% of options volume, prefers
cheap short-dated contracts with an average bid-ask spread of **12.6%**, and **loses money on
average.** You would be joining that flow.

**Note the direct convergence with your own data.** §5.2 finds the full far-OTM universe at −45.6%
but the *liquid, tight-spread* subset at ≈ 0. That is exactly Cao-Han ("stronger among smaller
stocks") and Zhan et al. ("buying is least bad on large, stable names"), reproduced independently
on a survivorship-free 2020–2026 sample. **Your tradeable subset is ≈ 0 rather than Ni's −36.86%
precisely because the spread filter selects the corner of the cross-section where the published
literature says option buyers lose least.** Take that as the ceiling, not as encouragement.

---

## 3. EVENT CATALYSTS WITH KNOWN DATES

The pattern is uniform: **abnormal move size is real and enormous; abnormal move size *relative to
the option price* is not.**

### 3.1 Earnings — the only one worth any further work

*Move size:* settled since Beaver (1968); replicated on ~700,000 announcements by Beaver, McNichols
& Wang (2020). Frazzini-Lamont: ~60% of a typical stock's annual return arrives on four days.
**Confirmed locally:** mean earnings-day move **5.46%** vs mean implied 1-day move **2.78%** —
a ratio of **1.95× mean / 1.48× median**. The earnings day is a multi-sigma day. Everyone knows.

*Straddle P&L — the two papers and their reconciliation:*

- **Dubinsky, Johannes, Kaeck & Seeger (2019, *RFS*)**, 50 most liquid names 2000–2015:
  implied earnings-day vol **8.22%** vs realized **7.42%** (~80 bp premium). ATM straddle held
  through the print: **mean −8%, median −10%**, and stronger on medians, so not an outlier artifact.
- **Gao, Xing & Zhang (2018, *JFQA*)**, ~669 firms/qtr 1996–2013. Headline +3.34%. But the window
  decomposition is decisive:

| window | return | note |
|---|---|---|
| [−3, −1] exits **before** the print | **+1.37%** (t=3.81), positive 74% of the time | the real effect |
| [−3, +1] holds **through** the print | **not significant** | |
| [0, +1] the announcement itself | **−1.37%** (t=−3.07) | the crush |

**The documented earnings edge is a pre-announcement vega ramp, and it is destroyed by holding
through the event.** Your strategy is on the wrong side of both legs: you pay the ramp and then
eat the crush.

And GXZ's own cross-sectional sorts kill the harvestability: the effect is **+4.93% in the widest
option-spread quartile and +1.14% in the tightest**, **+5.82% in low option volume and +0.90% in
high**. It is largest exactly where you cannot trade it. All returns are at midpoint with no cost
deduction.

*Baseline for context:* GXZ measure delta-neutral single-stock straddles at **−17.09%/month
(t = −26.82)** unconditionally.

*Predicting earnings move SIZE:* genuinely predictable. GXZ find higher pre-announcement straddle
returns for smaller firms, higher vol, higher kurtosis, and **more volatile past earnings
surprises**. Gallo (2017) links changes in forecast dispersion to announcement volatility.
**But none of these papers demonstrates prediction of realized move in excess of the implied
move**, which is a different and much harder claim.

### 3.2 The finding that most damages the earnings idea

From your own panel — conditioning on an earnings date inside the forward 21 sessions:

| | n | mean IV | P(>2σ) | P(>2.5σ) | **P(>3σ)** |
|---|---|---|---|---|---|
| no earnings | 1,041,917 | 0.386 | 3.86% | 1.76% | **1.00%** |
| earnings in window | 504,221 | 0.443 | **4.96%** | 2.02% | **0.91%** |

**Earnings raise the probability of a 2σ move by 28% and LOWER the probability of a 3σ move.**

The mechanism is clear once you see it: an earnings announcement reliably produces a *moderate*
shock and simultaneously *resolves* uncertainty, capping the tail. A far-OTM option needs 3σ.
Scheduled earnings is a 2σ event generator with a 3σ price attached.

If you want to be long the 2σ region, that is a near-ATM or 0.25-delta trade, not a $1 lottery
ticket — and there the ~13% spread and the −8% Dubinsky result apply.

### 3.3 Everything else

| Catalyst | Abnormal move? | Priced? | Verdict |
|---|---|---|---|
| **FDA / PDUFA** | Yes, huge: biotech mean \|AR\| 2.92% (SD 4.59%); individual outcomes −100% to +485% (Singh-Rocafort-Cai-Siah-Lo 2022, 13,807 trials) | **No literature at all** on option P&L | **Untested**. Bohmann-Patel (2022, *JBFA*) find informed pre-announcement option flow — you'd be the counterparty. Dates slip constantly; readouts guided as "1H 2026". 10–30% spreads. Highest cost, lowest evidence. |
| **Index adds/deletes** | **Dead.** Greenwood-Sammon (*JF* 2025): S&P 500 addition effect 3.42% (1980s) → **0.799%, insignificant (2010–2020)**. Excluding Tesla, 2020 inclusions averaged **−3 bp**. Rebalance day is 26–30% of window volume with **zero** price response | n/a | **Disproven.** The one calendarable day is a *low*-vol day. Exception: adds >1% of index cap. |
| **Lockup expiry** | Field-Hanka (2001): −1.5% 3-day CAR, +40% permanent volume. But new IPOs run 60–80% vol ≈ 7% per 3 days, so −1.5% is **0.2 standard deviations** | Yes — date is computable from the S-1 on day one | **Disproven as a magnitude trade.** Cao-Field-Hanka (2004): spreads and depth *improve* at expiry. Modern cohorts have price/earnings early-release triggers, so the date isn't even fixed. |
| **FOMC / macro** | Documented **short**-vol: Hu-Pan-Wang-Zhu, Lucca-Moench — >80% of the equity premium accrues pre-FOMC "with no significant increase in return variance"; VIX systematically *falls* into announcements | Yes | **Wrong sign.** A directional overnight trade, not a long-vol trade. |
| **M&A / antitrust / vote** | Genuinely bimodal, date-anchored. Mitchell-Pulvino: risk arb ≈ writing an uncovered index put, ~4%/yr after costs | **Yes, explicitly.** Bester-Martinez-Roșu (2021): target IV has a **kink at the offer price proportional to deal success probability**, with predictive power beyond standard merger variables | Market makers already model the two-point distribution. Far-OTM puts on targets are expensive *for the right reason*. |
| **Spin-offs** | All action is at **announcement** (+3.02% 3-day CAR). Completion/when-issued dates: no documented abnormal move | — | Dead as a scheduled trade. (You already have `data/spinoffs/` — this is consistent with `RESEARCH_SPINOFFS.md`.) |
| **Court/regulatory** | Patent resolution ~1–1.5%; NPE suits "the market reacted little, if at all" | — | Dates usually unknowable anyway. |
| **Credit rating actions** | −10% to −14% over the **first year** post-downgrade — a drift, not an event move | — | Not an options trade. Agencies lag. |
| **Investor days, SSS, deliveries** | No academic literature. Lu-Xin (2023) find monthly sales *preempt* earnings, **shrinking** per-event moves | — | Folklore. |

### 3.4 The meta-answer on events

**No published long-premium event strategy survives costs.** And the strongest evidence is a
recantation: **Goyal & Saretto (2022)**, the authors of the original vol-spread anomaly, tested 44
option strategies under IPCA and concluded —

> "We conclude that the extant evidence on option trading strategies presents no significant
> challenges to market efficiency."

Their own 2009 HV−IV strategy fell from **3.6%/month raw to 1.0%/month alpha.**

---

## 4. CROSS-SECTIONAL SCREENS — VERDICTS

| Screen | Verdict | Evidence |
|---|---|---|
| **Volatility compression / squeeze / BB-width / NR7 / inside day / ATR pct** | **DISPROVEN — premise is backwards** | Vol-shock half-life ≈ **100 trading days** (regression of log fwd RV21 on log RV20: slope 0.864, corr 0.886). Compressed quintile forward \|ret21\| **7.29% vs 9.32%**; P(>10%) **23.4% vs 29.6%**. Standalone the signal loads with the **wrong sign** (+0.53). Added to a HAR-style baseline it buys **+0.005 R²**. NR7 (n=33,798): 8.49% vs 8.31% — nil. **Confirmed null on your survivorship-free panel** (§5.3). No peer-reviewed test of NR7/Crabel exists; Park-Irwin's survey of 95 TA studies flags data snooping throughout. |
| **IV rank / IV percentile** | **FOLKLORE** | **Zero peer-reviewed literature exists.** A tastytrade-era retail construct. Confirmed flat locally (§5.3). |
| **IV term-structure slope** | **REAL BUT PRICED — and points the other way** | Vasquez (2017, *JFQA*): lowest-slope decile straddles **−9.2%/mo**, highest **+7.3%/mo**, long-short **+16.5%/mo (t=10.02)**, **surviving 100% of quoted spread at +6.8% (t=3.72)**. Direction matters: the front month being *inverted* — the pre-earnings configuration — is the **worst** bucket. Largely absorbed by IPCA. |
| **HV − IV (Goyal-Saretto)** | **REAL, AND THE BEST LONG-VOL SIGNAL IN THE LITERATURE — but it is an ATM straddle trade on illiquid names** | 1996–2006, 75,627 option pairs. Straddle decile 10 (the long leg you'd trade): **+9.9%/month gross, monthly Sharpe 0.329**; 10−1 spread +22.7%, Sharpe 0.903. **Four caveats, all from the paper itself:** (1) at an effective spread equal to the quoted spread the 10−1 falls to **+3.9%/mo** — an 83% haircut; (2) these are **ATM straddles, not far-OTM** — the signal is about the IV *level*, and says nothing about tail pricing; (3) the mechanism is **transitory IV mean-reversion**, not superior forecasting — *"the deviations between HV and IV are transitory"*, and decile membership is driven by the prior month's stock return, i.e. it is substantially short-term reversal in IV; (4) *"the before-cost profits are higher for illiquid options than for liquid options"* — and **Christoffersen-Goyenko-Jacobs-Karoui (2018, *RFS*)** measure the equity-option illiquidity premium at **3.4% per day for ATM calls**, which plausibly *is* the anomaly. Goyal & Saretto (2022) IPCA cuts the whole thing to 1.0%/mo alpha. Locally: weak, right-signed, not significant (Q4−Q0 in P(>2.5σ) = +0.0054, **t = +1.92**) — the strongest of your five screens, still under 2. |
| **Execution timing (the one favourable finding)** | **REAL** | **Muravyev & Pearson (2020, *RFS*)** "Options Trading Costs Are Lower than You Think": effective spreads for traders who time executions are **under 40% of conventional measures**; the overall average is ~25% smaller. This genuinely alters after-cost conclusions — but it applies to **liquid** options and requires real execution skill. Far-OTM single-stock contracts are the least liquid instruments in the equity option universe. |
| **Short interest / borrow fee** | **REAL for direction, PRICED for magnitude** | Boehmer-Jones-Zhang: 1.16% over 20 days. Asquith-Pathak-Ritter: 215 bp/mo equal-weighted but **39 bp insignificant value-weighted** — a microcap effect. Drechsler²: "anomalies effectively disappear within the 80% of stocks with low short fees." |
| ⚠ **The borrow-fee trap** | **Calls on hard-to-borrow names look cheap and are not** | Put-call parity with a lending fee *f* is `C − P = S·e^(−(q+f)T) − K·e^(−rT)`. The market prices off a **forward depressed by the PV of the lending fee**. Back out IV using raw spot and a plain risk-free rate — what every retail scanner does — and *f* is missing from your forward, so the model attributes the low call price to low vol. **The discount is exactly the lending income you forgo by holding a call instead of the stock.** Ofek-Richardson-Whitelaw (2004): PCP "violations" track rebate rates and are not arbitrageable. Evans-Geczy-Musto-Reed (2008): MMs often **fail to deliver rather than borrow**, so part of the fee never reaches option prices as cheapness at all. |
| **Unusual options activity** | **REAL BUT DIRECTIONAL, DECAYING; products are FOLKLORE** | Pan-Poteshman: 40 bp/day — **on proprietary CBOE open/close-flagged buyer-initiated volume you do not have.** Cremers-Weinbaum state plainly the predictability "decreases over the sample period." Ge-Lin-Pearson: the mechanism is **embedded leverage, not information**. **Zero independent validation of any commercial flow product.** And your chain data has no volume/OI, so this is untestable here regardless. |
| **Attention / social / meme** | **REAL BUT PRICED; directionally a fade** | Da-Engelberg-Gao (2011) SVI→vol is robust across 56 studies. But attention is the *most conspicuous public signal that exists* — the "beyond IV" bar is unclearable. Barber-Huang-Odean-Schwarz: **−4.7% 20-day abnormal return** on top Robinhood buys. Bollen-Mao-Zeng Twitter mood does not replicate. |
| **Fundamental vol predictors** (size, leverage, R&D, firm age, dispersion) | **REAL AND OBVIOUSLY PRICED** | These are the *inputs* to a market maker's vol surface. A pre-revenue biotech has 90% IV because it is a pre-revenue biotech. |
| **Vol-of-vol** | **REAL AND PRICED AGAINST YOU** | Baltussen-van Bekkum-van der Grient (2018, *JFQA*): high vol-of-IV stocks underperform by **8%/yr**. And the option-side result is explicit: investors "pay a **high premium** to hold options on high VOV stocks." Vol-of-vol flags *expensive* options. |
| **ML / rough vol** | **MARGINAL vs HAR; UNTESTED vs IV** | See §2.3. |

**Not one screen has published evidence of predicting realized magnitude in excess of what options
charge, at a 1–6 week horizon, cross-sectionally.**

---

## 5. ORIGINAL MEASUREMENT ON YOUR DATA

### 5.1 Setup

- Universe: every symbol in the DoltHub chain, ADV20 > $5M, **survivorship-free**.
- Entries: 158 dates, ~2 per month, 2020-01 → 2026-06.
- Contract: per (date, symbol), expiration closest to **35 DTE**, then delta closest to **0.10**.
- **Entry at the ASK** (mid reported alongside).
- **Held to EXPIRATION and settled at intrinsic** from split-validated closes.
- t-stats from **date-level means with Newey-West(3)**, never pooled trades.

> **The exit-side design is deliberate.** No exit quote is ever consulted, so the
> `bid > 0` filter that deletes worthless expiries — the bug that manufactures 90%+ win rates —
> is **structurally impossible** here. Every entry produces an outcome. **The observed median
> return is −100%, which is the signature of a backtest that is not lying to you.**

**n = 123,107 trades.** Mean delta 0.117, mean ask $1.36, mean strike 17.1% OTM.

### 5.2 The unconditional result

| Subset | n | win% | mean @ ask | median | mean @ mid | NW t |
|---|---|---|---|---|---|---|
| **ALL** | 123,107 | 8.1% | **−45.6%** | −100% | −24.5% | **−7.13** |
| ask $0.30–2.00 (the "$1 lotto") | 72,143 | 8.6% | −40.0% | −100% | −18.4% | −5.98 |
| **spread ≤ 20% of mid** | 6,440 | 10.0% | **+5.6%** | −100% | +12.3% | **+0.98** |
| spread ≤ 20% AND ask $0.30–2.00 | 4,344 | 10.7% | +9.4% | −100% | +16.2% | +0.99 |

By quoted spread at entry — this is the causal story:

| entry rel spread | n | mean @ ask | NW t |
|---|---|---|---|
| 0.00–0.10 | 1,764 | **+20.0%** | +0.27 |
| 0.10–0.20 | 4,647 | +0.6% | +1.15 |
| 0.20–0.35 | 11,359 | −20.0% | −0.79 |
| 0.35–0.60 | 19,732 | −18.9% | −1.65 |
| **0.60+** | **85,579** | **−59.0%** | **−11.48** |

**70% of the far-OTM single-stock universe sits in the 0.60+ spread bucket.** That is where the
−45.6% comes from. In the tradeable tenth of the universe, the trade is a coin flip with a
negative-skew payoff.

By year, at the ask: −28.1, −44.1, −51.8, −53.1, −54.5, −48.4, −33.8 (2020→2026).
**Negative every single year.** No regime rescues it.

### 5.3 Every screen, conditioned (spread ≤ 25%, n = 9,802)

| Screen | Q0 | Q1 | Q2 | Q3 | Q4 | Read |
|---|---|---|---|---|---|---|
| IV rank | +5.1% | +4.9% | −6.2% | −2.8% | −10.6% | mildly monotone the *right* way, all t < 1 |
| HV−IV (Goyal-Saretto) | −5.2% | −6.6% | +9.9% | −8.8% | −1.5% | no monotonicity |
| RV20 percentile (squeeze) | +6.3% | −14.0% | +2.1% | −0.9% | +8.9% | **U-shaped noise; the squeeze is a null** |
| HV / HV_year_high | −3.3% | +10.8% | +4.8% | −5.0% | −18.8% | no |
| IV 1-month change | −11.1% | −11.5% | −10.9% | −23.7% | −9.2% | uniformly negative |
| IV level tercile | −8.6% | −2.6% | +3.6% | — | — | flat |
| **Earnings in option life** | **+17.0% (t=+1.78, win 10.8%)** vs **−13.4% (t=+0.51, win 8.8%)** | | | | | **the only pulse** |

On the full 1.55M-row panel, using P(|21d move| > 2.5σ_implied) as the target and Fama-MacBeth
with Newey-West(21) on the Q4−Q0 spread:

| Screen | Q4−Q0 | t |
|---|---|---|
| Goyal-Saretto HV−IV | **+0.0054** | **+1.92** |
| HV / HV_year_high | +0.0025 | +1.39 |
| RV20 percentile (squeeze) | −0.0004 | −0.40 |
| IV rank | −0.0039 | −1.52 |
| IV 1-month change | −0.0070 | −1.93 |

**Nothing clears 2.** The best is the 100-year-old HV−IV spread at t = 1.92, and Goyal & Saretto
themselves published the paper that discounts it by two-thirds.

### 5.4 Earnings move magnitude — predictable, but against the wrong benchmark

30,004 events, 1,932 symbols, 2020–2026. Regression of log|earnings-day move| on
strictly-prior information, date-clustered SEs:

| model | R² | coefficients (t) |
|---|---|---|
| IV only | 0.1189 | iv_daily 1.056 (51.3) |
| IV + prior-4 earnings moves | 0.1394 | iv_daily 0.741 (29.0), prior4 0.309 (24.5) |
| **IV + prior4 + RV20** | **0.1895** | **iv_daily 0.028 (0.65)**, prior4 0.323 (24.4), rv20 0.798 (21.3) |

**The firm's own prior-4 earnings-move history and trailing RV20 completely subsume the vendor's
30-day ATM IV.** The IV coefficient collapses to zero.

And the practitioner screen — implied ÷ mean prior-4 actual earnings move — sorts beautifully:

| quintile | implied 1d | prior-4 actual | actual | P(actual > implied) | P(> 2× implied) |
|---|---|---|---|---|---|
| Q0 ("cheapest") | 0.0290 | 0.0920 | 0.0662 | **69.4%** | 45.1% |
| Q4 | 0.0274 | 0.0233 | 0.0430 | **56.6%** | 28.3% |

Q0−Q4 spread in P(beat implied) = **+9.45%, t = 7.22.**

**DO NOT TRADE THIS.** It is a benchmark artifact, and the tell is in the table: `implied 1d` is
**0.0290 vs 0.0274 across quintiles — essentially constant.** The entire sort is driven by the
numerator. `iv_current` is a 30-day ATM IV; it is *not* the earnings-event implied move, and the
real front-month event move absolutely does vary across these names — that is what the term
structure is for. What this result actually establishes is: **the 30-day ATM IV is a bad proxy for
the event price, and any study using it will find a spurious edge.**

It also tells you the correct experiment, which is §7.1.

---

## 6. GITHUB SWEEP

~40 repos surveyed, code read (not READMEs) on the 12 most relevant.

### The headline: the signal layer does not exist publicly

Several query families returned **literally zero repositories**:
- **No open-source FDA/PDUFA/catalyst-calendar infrastructure exists**, under any name.
- **No NR7 / inside-day / ATR-compression screener with a backtest exists.** The entire public
  squeeze corpus is essentially one 161★ tutorial.
- **No backtest of unusual options activity against real chains exists.** Everything is an API
  wrapper around Unusual Whales or Barchart.
- **Nobody backtests LONG far-OTM options against real bid/ask.** Not one repo. Every real-chain
  backtester found is oriented to premium *selling*.

### Reusable

| Repo | ★ | What it actually is |
|---|---|---|
| [bashtage/arch](https://github.com/bashtage/arch) | 1.6k | Kevin Sheppard. GARCH family **and a first-class HAR mean model**. Production-grade, tested. Use this instead of any thesis HAR repo. |
| [dynamiciterativeprocess/Lee-Mykland-Test-Statistic](https://github.com/dynamiciterativeprocess/Lee-Mykland-Test-Statistic) | **0** | Best code-quality-per-star found. 64 lines, verified line-by-line against Lee-Mykland (2008): `Cn` matches Lemma 1; `beta_star = −log(−log(1−α))` is the correct Gumbel quantile; K values reproduce the paper's table exactly (5min→270, 30min→110). **Crucially, no look-ahead** — the double shift means σ̂ at bar *i* uses only returns through *i−1*, which is the thing most implementations get wrong. Two fixes needed: **no session-boundary reset** (every overnight gap flags as a jump — the `24*60` constant betrays a crypto origin), and `movmean` is an O(n·k) Python loop. **Use it as a jump *labeler*; it does not predict.** |
| [vollib/py_vollib](https://github.com/vollib/py_vollib) | 424 | IV/Greeks via Jäckel's LetsBeRational. Correct primitive. |
| [YalDan/hf.econometrics](https://github.com/YalDan/hf.econometrics) | 17 | R. Only multi-test jump suite (Lee-Mykland + Aït-Sahalia/Jacod + pre-averaging). Author states it is **untested**. |

### Reusable with a named fix

| Repo | ★ | The flaw |
|---|---|---|
| [michaelchu/optopsy](https://github.com/michaelchu/optopsy) | 1.4k | `pricing.py` has a genuinely good slippage engine (long entries fill toward the ask, exits reverse, per-leg slippage) and — to its credit — `_remove_min_bid_ask()` is **opt-in**, not a hardcoded `bid > 0`. **But `evaluation.py` merges entries and exits with `how="inner"` and no intrinsic-value fallback at expiry.** Any contract without an exit-date quote is **silently dropped, with no logging** — this is the `bid > 0` bug wearing a different hat, and it truncates exactly the tail that decides the strategy. A 4-leg condor needs all four legs quoted or the whole trade vanishes. **Fix: left join from entries + intrinsic settlement.** |
| [erictao947/earnings-vol-study](https://github.com/erictao947/earnings-vol-study) | 0 | Most on-mission repo found, and on the same DoltHub data you have. **Steal the method:** a three-scenario cost ladder (`mid_mid` / `half_spread` / `full_spread` where exit = `q_pre.bid − q_post.ask`), HC1 + date-clustered SEs, explicit placebo phase. **Discount the 1.22× headline:** it carries `if min(c["bid"], p["bid"]) <= 0 ... return None` and skips events where the post chain lacks the contract — an exit-side filter that drops precisely the events where price ran far enough that the strike stopped being quoted, i.e. the short seller's worst losses. No train/test split anywhere. 54 large caps, 2023–2026. |
| [sirnfs/OptionSuite](https://github.com/sirnfs/OptionSuite) | 297 | Real iVolatility SPX chains **1990–2017** and **no row filtering at all** ✓. But entry is at `(bid+ask)/2` and exit at settlement — **zero bid-ask captured on either side of the round trip** — and there is no zero-DTE/intrinsic branch. |
| [jasonstrimpel/volatility-trading](https://github.com/jasonstrimpel/volatility-trading) | 1.9k | Garman-Klass, Parkinson, Rogers-Satchell are correct. **`YangZhang.py` is wrong in a 1.9k-star repo:** the middle term uses **close-to-close** where Yang-Zhang specifies **open-to-close**, so the overnight component is **counted twice**. The bias is largest on gappy single names — exactly your population. Do not use without fixing. |

### Junk

`hackingthemarkets/ttm-squeeze` (161★, the most-starred squeeze scanner): **`TR = abs(High − Low)`
is not True Range** — it discards gaps entirely, so ATR is understated on gapping names and the
scanner *under*-detects squeezes on the very population you care about. The fire condition checks
`iloc[-3]` and `iloc[-1]` and never `iloc[-2]`. Data is hardcoded to a 7.5-month window spanning
the COVID crash. **No backtest of any kind.**
· `deep-hedger-Peng/HAR-RV` (26★): fit-on-all, and **VIX enters contemporaneously** — the VIX close
of day *t+1* embeds that day's realized vol, i.e. straight look-ahead.
· `NavnoorBawa/Options-Flow-Predictor` (24★): README states **"Sharpe ratios above 2.0"** as a
target with zero backtest artifacts.
· `jakeeskanazy26-spec/vrp-options-backtest`: **Monte Carlo synthetic option prices presented as a
backtest.**
· The entire 0DTE-scanner and unusual-whales-wrapper clusters: data pipes, no evaluation.

---

## 7. RANKED SHORTLIST — WHAT TO ACTUALLY BACKTEST

Ordered by expected information per unit of work. **Honest prior on each is stated as a
probability that a properly-costed backtest shows positive expectancy.**

---

### #1 — Earnings term-structure mispricing: implied event move vs the firm's own earnings history
**Prior: 15%.** The highest of anything here, and still under a coin flip.

This is the one experiment in this document that has not been run correctly by anyone —
academically, in open source, or by you. §5.4 shows the naive version produces a **spurious
t = 7.22** because a 30-day ATM IV is not the event price.

**Spec:**
1. For each earnings event in `earnings.earnings_calendar` (117,594 events; use `when` to set the
   reaction day — BMO → event date, AMC/blank → next session), take the last `option_chain`
   snapshot **strictly before** the event. **Record and report the snapshot gap in calendar days**
   — it is 1–3 days in 2020–2024 and 1 day in 2025+. Run 2025-01→2026-08 as a clean daily-cadence
   subsample and check it separately.
2. Extract **two** ATM straddles: the front expiry that spans the event (`expiration > event_date`,
   nearest) and the next expiry after that. ATM = strike nearest the underlying close.
3. Back out the **event-day implied move** by the standard two-expiry decomposition:
   σ²_front·T_front = σ²_base·T_front + M², where σ_base is interpolated from the back expiry.
   `implied_event_move = M`. **This is the price you are actually paying.** Everything in §5.4
   collapses without it.
4. Compute `prior4 = mean |actual earnings move|` over that firm's **strictly prior** 4 events
   (`shift(1).rolling(4)` — never include the current event).
5. Screen variable: `cheap = implied_event_move / prior4`. Sort into quintiles **within each date**.
6. Outcome: `actual_move / implied_event_move`, and P(actual > implied), P(> 2× implied).
7. **Then the real test:** does `prior4` retain incremental predictive power for the actual move
   after controlling for `implied_event_move`? In §5.4 it did against the 30-day ATM IV
   (coefficient 0.32, t = 24). **If it survives against the true event move, that is the finding.
   I expect it will not, and I expect the coefficient to go to roughly zero.**
8. Only if step 7 survives, price the trade: buy the front straddle at the **ask**, sell at the
   **bid** on the session after the print. Report mid / half-spread / full-spread as three columns,
   per erictao947's method. Never report mid alone.

**Traps this must avoid:**
- Do not use `volatility_history.iv_current` as the event price. That is the §5.4 artifact.
- Do not filter the exit chain by `bid > 0`. For an ATM straddle one leg always retains intrinsic,
  so instead **settle both legs at intrinsic against the underlying close** if a quote is missing,
  and log how often that happens.
- Overlap: earnings cluster into 3 weeks per quarter. Cluster standard errors **by date**, and
  report the number of distinct dates alongside n.
- If a t-stat exceeds 5, check whether `implied_event_move` varies across your quintiles. If it
  doesn't, you have rebuilt the §5.4 bug.

**What would make me wrong:** the term-structure decomposition reveals that market makers set the
event move from a *short* lookback (last 1–2 prints) while the 4–8 print history is more
informative. That is a plausible behavioural story and it is cheap to test.

**One more control, learned from Goyal-Saretto's failure mode.** If the effect appears, immediately
sort it by **option liquidity**. Goyal-Saretto's gross profits were *"higher for illiquid options
than for liquid options"*, and Christoffersen et al. measure the equity-option illiquidity premium
at **3.4%/day for ATM calls** — i.e. the anomaly may simply *be* the illiquidity premium, which you
pay away on entry and exit. GXZ show the identical pattern in the earnings straddle: **+4.93% in
the widest-spread quartile vs +1.14% in the tightest.** If your effect is concentrated in the wide-
spread names, it is not an edge; it is a bill. **The result only counts if it is present in the
tightest-spread quartile.**

---

### #2 — Re-price the fat tail: is the SKEW correct at 3σ?
**Prior: 10% that you find mispricing in your favour; ~2% that it survives the spread.**
(Revised down from 20% after Bollerslev-Todorov: far-OTM **calls** are priced at ~41× the physical
+10%-jump intensity. The prior should be that you find the tail is *over*priced, not under.)

§2.2 established that P(|21d move| > 3σ_ATM-implied) is **3.59× lognormal** and > 4σ is **63×**.
§5.2 established that tradeable far-OTM calls return ≈ 0. Those two facts *should* imply the skew
is priced approximately right — but you have not measured the skew directly, only the outcome.
This test measures the mispricing surface itself and tells you **which delta bucket, if any, is
cheapest** rather than assuming 0.10.

**Spec:**
1. For each (date, symbol) with ADV > $50M (liquid only — this is a pricing question, not a
   universe question), extract the full ~35 DTE call and put chain.
2. Bucket by delta: 0.30 / 0.20 / 0.15 / 0.10 / 0.07 / 0.05, calls and puts separately.
3. For each bucket compute the **realized frequency** that the option finishes ITM, and compare to
   the risk-neutral probability implied by its own delta (dual-delta is exact; delta is a good
   approximation). `lift = P_realized_ITM / P_implied_ITM`.
4. Then compute the actual buy-at-ask / hold-to-expiry return per bucket, as in §5.2.
5. Split calls vs puts. **The lottery-demand literature predicts calls are relatively *more*
   overpriced than the tail alone justifies; the crash-premium literature predicts puts are.**
   Whichever direction the data goes, it tells you which side of the surface to be on.

**Why this is worth doing even though the answer is probably "priced":** it is one query and one
groupby on data you already have, it is diagnostic rather than a strategy, and it converts "the
tail is fat" from an interesting fact into a number you can act on or discard. It also directly
tests whether 0.10 delta was the wrong bucket — my §5.2 result is a single point on a curve.

---

### #3 — The tradeability filter as the strategy
**Prior: 25% that a spread-filtered universe is a genuine improvement; ~0% that it is profitable.**

This is the strongest empirical regularity in §5.2 and it is not a signal — it is a cost model.

| entry rel spread | mean @ ask |
|---|---|
| ≤ 0.10 | **+20.0%** |
| 0.60+ | **−59.0%** |

**Spec:** re-run §5.2 with a hard filter `(ask − bid)/mid ≤ 0.15` and `bid > 0` **at entry only**
(entry filtering is legitimate — you must be able to buy it; exit filtering is the bug), and
require ADV > $25M. Then re-run all five screens from §5.3 **inside that universe only**.

**What I expect:** n drops to roughly 4,000–6,000 trades, the unconditional mean sits within ±15%
of zero with t < 1, and no screen separates. **The value of running it is that it establishes the
honest ceiling.** If the tradeable-universe mean is genuinely ≈ 0 rather than negative, then this
strategy is a fair coin with a lottery payoff — which is a legitimate thing to know, and it means
the only remaining question is whether *any* screen can push a fair coin positive by more than
15% of premium. Nothing found in this document can.

---

### #4 — Jump labeling and jump prediction (diagnostic, not a strategy)
**Prior: 10% that jump arrival is predictable at all beyond vol level.**

Andersen-Bollerslev-Diebold's core finding is that the **jump component is essentially
unpredictable** while the continuous component is highly predictable. Lee (2012) is the main
dissent. You have the data to adjudicate this on your own universe.

**Spec:**
1. Label jumps on daily data via a Lee-Mykland-style test (or simply |r_t| > 4 × bipower-variation
   σ̂ estimated on t−1 and earlier — **the double shift is mandatory**, see the repo note in §6).
   Use `dynamiciterativeprocess/Lee-Mykland-Test-Statistic` as the reference implementation but
   **add a session-boundary reset**.
2. **First, before anything else: cross-check every labeled jump against `stocks.split` and
   `stocks.dividend`.** §1.3–1.4 guarantee that a naive jump detector on this table will find
   corporate actions. The 0.085% of rows with unexplained >60% moves are the ones to inspect.
3. Predict `P(jump in next 21 sessions)` from strictly prior features: RV20, RV252, IV, IV−HV,
   days-to-earnings, market cap, sector. **Train on 2020–2023, test on 2024–2026. No refitting.**
4. Success criterion is **not** AUC. It is: does the predicted-jump top decile show a higher
   `P(|move| > 2.5σ_implied)` than the bottom, with a Newey-West t > 2 on date-level spreads?

**Why bother if the prior is 10%:** because the same labeling pipeline is a prerequisite for any
future work here, and because a clean negative confirms the ABD result on your own universe and
lets you close the file.

---

### #5 — Small-cap biotech binaries
**Prior: 10%, and unmeasurable with your current data.**

The one genuine white space. Singh-Rocafort-Cai-Siah-Lo (13,807 trials) document individual
outcomes from **−100% to +485%**, and **nobody has published whether market makers price that tail
correctly**. No open-source PDUFA calendar exists.

**Do not build this.** Three blockers, any one of which is fatal:
- PDUFA dates slip and readouts are guided as "1H 2026" — you cannot time theta against a moving
  date, and you pay for every week of slippage.
- Bohmann-Patel (2022) document informed pre-announcement option flow. You would be the
  uninformed counterparty by construction.
- Spreads of 10–30% of premium on small-cap biotech options, against the ~17% you measured on
  mega-caps. §5.2 shows the spread bucket is the whole result.

Listed for completeness and to mark it as *knowingly* declined rather than overlooked.

---

### Explicitly NOT worth backtesting

| | Why |
|---|---|
| **Squeeze / BB-width / NR7 / inside day / ATR compression** | Disproven twice (§4, §5.3). Compressed names move **less**. Half-life 100 days. **If any of this is wired into a dashboard as a long-premium trigger, it is selecting the quietest names in the universe.** |
| **IV rank** | Zero literature; flat locally in both tests. |
| **Unusual options activity** | Your chain data has **no volume or open interest column**. Untestable. And the academic version needs proprietary open/close-flagged signed volume. |
| **Index rebalance / lockup expiry** | Effects are dead (−3 bp) or 0.2σ. |
| **Short interest** | You don't have the data, it's a direction signal, it's a microcap effect, and the borrow fee makes the calls look cheap for a reason that is not cheapness (§4). |
| **Attention / social sentiment** | Real, but it is the most publicly conspicuous signal that exists. |
| **Buying far-OTM into earnings** | §3.2: earnings **lower** P(>3σ). It is a 2σ generator with a 3σ price. |

---

## 8. RED FLAGS — INCLUDING THE TWO I HIT IN THIS SESSION

The brief listed five. I hit two of them plus two data-layer ones that are not on the list and
should be.

| Flag | Where it appeared |
|---|---|
| **Exit-chain `bid > 0` deletes losers** | Found in `erictao947/earnings-vol-study` (explicit) and in `optopsy` (disguised as `how="inner"` with no dropped-row logging). **Structurally avoided in §5** by settling at expiry intrinsic and never consulting an exit quote. The tell that §5 is honest: **median return −100%.** |
| **Mid-price fills on far-OTM** | The difference between mid and ask on your data is **−45.6% vs −24.5%** — the entire result. `sirnfs/OptionSuite` fills mid-in/settlement-out with zero spread captured. GXZ's published +3.34% is a midpoint number. |
| **Overlapping trades inflating t-stats** | Handled: all t-stats in §5 are date-level means with Newey-West, never pooled. Note the §5.4 t = 7.22 is a *benchmark* artifact, not an overlap artifact — a reminder that these fail independently. |
| **Look-ahead** | Avoided: all percentile ranks are **trailing 252-day** (`rolling(252).rank(pct=True)`), all cross-sectional sorts are **within-date**, `prior4` uses `shift(1).rolling(4)`. |
| **t > 10 is a bug report** | §5.4's **t = 7.22** was investigated and found to be a bad-benchmark artifact — the denominator was near-constant across quintiles. It would have been a publishable-looking result. |
| ⚠ **NEW: unadjusted OHLC** | §1.3. A raw price table makes every split a −90% "jump". My own first pass got the adjustment *direction* wrong and produced mean forward RV of 0.876 against mean IV of 0.405. |
| ⚠ **NEW: duplicate corporate-action rows** | §1.4. **33% of the DoltHub split table is duplicates.** It turned a −45.6% strategy into a +199.6% strategy through a data table alone, with the top 10 trades supplying 95% of the P&L. **Always validate a claimed split against the actual price gap.** |

**Add both new ones to `RESEARCH_*` methodology traps.** Neither is a modelling error; both are
data-layer errors that pass every statistical check you would think to run, and both produce
*spectacular* false positives specifically in a large-move study — because a corporate action **is**
a large move.

---

## 9. THE HONEST ANSWER

**Nothing beats implied volatility.**

At the 1–6 week horizon, for single stocks, for move magnitude: the option market's forecast is not
beatable by any screen in the literature, any repo in open source, or any of the five screens
tested on your own survivorship-free data. The best statistical screen (Goyal-Saretto HV−IV) reached
**t = 1.92** and its own authors published the paper that cuts it by two-thirds.

The strongest single sentence in the literature is Busch-Christensen-Nielsen's, at exactly your
horizon: **IV alone minimizes out-of-sample forecast error, IV is unbiased (β = 1.06, se 0.067),
and adding any realized-volatility information makes the out-of-sample forecast worse.** Every
other horse race — Jiang-Tian, Christensen-Prabhala, Taylor-Yadav-Zhang — agrees. The HAR
literature's "significantly better out-of-sample performance" is always against GARCH or against
another HAR, never against the option market.

Four things are worth carrying forward:

1. **The single-stock variance risk premium really is weak** — 67.6% not 85% locally, and
   Carr-Wu find 12 of 35 names with a *positive* premium and short-vol Sharpes of 0.00–0.05. The
   diffusive vol headwind is roughly 12%, not 40%. That part is survivable.
2. **But the trade is priced off the jump tail, not diffusive variance, and the jump tail is
   marked up ~41× on calls.** Compounding it, the jump component is the one part of realized
   variance with essentially no predictability (ABD: all jump coefficients insignificant at
   h = 22; incremental R² = 0.000), and even that sliver is better forecast by IV than by any
   realized measure.
3. **The spread is not survivable.** 17–19% round-trip on the best names, 100%+ on the median name,
   and 70% of the universe is untradeable. Your measured −45.6% is a spread result, not a
   forecasting result. **In the tradeable decile the trade is a fair coin.**
4. **A fair coin with a lottery payoff is not nothing, but it is not a strategy** — it is a
   negative-expectancy game once you add commissions, and it has no screen to make it positive.

Four independent literatures — variance risk premium, jump-tail premium, lottery demand, and the
option illiquidity premium — converge on the same conclusion, and it is unusually specific: the
proposed trade is aimed at **the exact corner of the option cross-section where the buyer loses
most.** Small, high-volatility, high-idiosyncratic-skewness names; far-OTM strikes; wide spreads.
Zhan et al. put the mirror image plainly: buying options is least bad on large, profitable, stable,
low-analyst-dispersion companies — i.e. the names that are least likely to make a big move.

The strongest version of this idea that survives everything above is: **buy the front-month ATM
straddle into earnings on liquid names where the term-structure-implied event move is low relative
to that firm's own last four prints, exit the day after the print, and pay the full spread in the
backtest.** That is experiment #1. My prior on it is **15%**, and the literature's best guess at
what you'd actually be harvesting is Gao-Xing-Zhang's pre-announcement vega ramp — which means the
correct exit is **before** the print, not after, and the correct instrument is ATM, not far-OTM.

Which is to say: the strategy that survives is not the strategy in the brief.

---

## Appendix — scripts

Copied to `scripts/move_prediction/`. They read CSV extracts from the dolt DBs; regenerate those
with the `dolt sql -r csv` commands noted at the top of each (`ohlcv.csv`, `splits.csv`, `vh.csv`,
`earn.csv`, `otm_calls.csv` via `chain_q.sql`).

| Script | Purpose |
|---|---|
| `adjust.py` | **Price-validated split adjustment. Use this one — it is the fix for §1.3–1.4.** |
| `study2.py` | 1.55M-row IV/return panel; base rates, tail table, five screens |
| `otm_bt.py` | 123,107-trade far-OTM call backtest (ask entry, expiry-intrinsic settlement) |
| `earn_move.py` | 30,004-event earnings-move predictability regressions |
| `audit.py` | Outlier audit — the script that caught the duplicate-split bug |
| `spread_q.sql`, `spread_q2.sql` | Far-OTM spread measurement by delta bucket |

Key intermediate artifacts: `px2.parquet` (validated adjusted prices, 17.7M rows),
`panel3.parquet` (1.55M-row screen panel), `otm_trades.parquet` (123k trades).
