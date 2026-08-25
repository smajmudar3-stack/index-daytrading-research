# Intraday direction: the ceiling, the hurdle, and the one thing that works

Five independent research sweeps plus in-house measurement on 1,919 days of real
SPXW quotes and 500 days of minute bars. This is the complete answer to "can
intraday direction be predicted, and can it be traded."

**Short version:** direction is weakly predictable — about 53% at the documented
ceiling. That is not enough to pay for an at-the-money 0DTE option on a typical
day, because time decay costs five times more than the spread does. One signal
does clear the bar, it has a published mechanism, and it must be traded
delta-1 rather than with ATM options.

---

## 1. The ceiling: how much accuracy is available at all

Signal-return correlation converts to hit rate as `p = 0.5 + arcsin(rho)/pi`.
This makes every claim in the field commensurable.

| source | rho | R² | implied hit rate |
|---|---:|---:|---:|
| our SPY first-half-hour vs last-half-hour | 0.033 | 0.11% | **51.0%** |
| our QQQ, same | 0.038 | 0.15% | 51.2% |
| our best SPXW bucket pair, out of sample | 0.023 | 0.05% | 50.7% |
| Gu-Kelly-Xiu, best monthly OOS | 0.063 | 0.40% | 52.0% |
| **Jane Street Kaggle 2025, top 1%** | 0.080 | 0.64% | **52.5%** |
| Jane Street 2025 + online learning | 0.092 | 0.84% | **52.9%** |
| a "55% win rate" claim implies | 0.160 | 2.56% | 55.1% |
| a "60% win rate" claim implies | 0.300 | 9.00% | 59.7% |

The Jane Street figure is the most informative number in this document: real
production data, 47M rows, 79 features, **3,757 competing teams**, enforced
chronology. The best anyone achieved was R² ≈ 0.0064.

**Treat 52.9% as the ceiling.** A claimed 60% intraday hit rate on liquid index
products is a claim of 9% out-of-sample R² — roughly fourteen times the best
result on Jane Street's own data using their own features.

### The decisive negative result

Cont, Cucuringu & Zhang, on full depth-of-book NASDAQ ITCH, 100 most liquid US
stocks, 3 years: integrated multi-level order flow imbalance gives

- **83.8% contemporaneous** out-of-sample R²
- **−0.10% to −0.37%** one-minute-ahead out-of-sample R² — *negative*

and the OFI models score **identically to models using lagged returns alone**.
With better data than we will ever have, the best microstructure feature ever
documented adds nothing to forecasting. It explains the move that just happened.

Everything genuinely microstructural lives between **one tick and twenty
seconds**. Futures→stock lead-lag peaks at 0.2–0.95 seconds and Huth & Abergel
state plainly that the bid-ask spread eats the entire 60%-accuracy edge.

---

## 2. The hurdle: what it costs to trade direction with 0DTE options

Measured from 391,401 at-the-money SPXW quotes.

| | index points |
|---|---:|
| ATM premium, median | 7.30 |
| round-trip bid-ask | 0.30 |
| **extrinsic lost per half hour** | **0.37** |

**Theta over a two-hour hold costs five times the spread.** Every analysis that
stops at the bid-ask — including my own first pass at this — understates the
hurdle by an order of magnitude.

Break-even accuracy is `p* = 0.5 + (spread + theta) / (2 · delta · move)`:

| move | 30 min hold | 1 h | 2 h | 4 h |
|---|---:|---:|---:|---:|
| 0.25% | 57.2% | 61.2% | 69.2% | 85.1% |
| **0.50%** | **53.6%** | 55.6% | 59.6% | 67.6% |
| 0.75% | 52.4% | 53.7% | 56.4% | 61.7% |
| 1.00% | 51.8% | 52.8% | 54.8% | 58.8% |
| 1.50% | 51.2% | 51.9% | 53.2% | 55.9% |

Anything above **52.9%** is unreachable whatever the signal.

### What move size is required at the ceiling

| hold | move needed to break even at 52.9% |
|---|---|
| 30 min | 0.62% of spot |
| 1 hour | 0.96% |
| 2 hours | 1.65% |
| 4 hours | 3.03% |

**CORRECTED 2026-08-25.** An earlier version of this section compared the
hurdle against the *intraday range* (median 0.43% from SPXW snapshots). That was
wrong twice: 13 half-hourly snapshots understate true range by roughly half, and
more importantly **range is not the move a trade captures** — a day can range
1% and close flat. Feeding range into the hurdle credits the trade with a move
it cannot realise, which is trap #6 in another guise.

The correct input is |return over the hold|, measured on 495 sessions of minute
bars:

| hold | median &#124;move&#124; | p90 | median range | accuracy needed at median |
|---|---:|---:|---:|---:|
| 30 min | **0.09%** | 0.32% | 0.23% | **69.3%** |
| 1 hour | 0.13% | 0.45% | 0.33% | 71.8% |
| 2 hours | 0.19% | 0.63% | 0.48% | 74.9% |

Range runs 2–3× the captured move at every hold. Only **1.9%** of 30-minute
windows (4.4% on QQQ) are large enough to clear the hurdle at the 52.9% ceiling.

The gap is therefore far wider than first stated: a typical 30-minute 0DTE
directional trade needs **69.3%** accuracy against a ceiling of **52.9%**.

**On a median day, a directional ATM 0DTE trade is not payable at the best
accuracy anyone has ever demonstrated.** The binding constraint is theta, not
signal quality — so more signal research cannot fix it.

---

## 3. What actually works: dealer gamma

Baltussen, Da, Lammers & Martens, *JFE* 142 (2021). 20+ index futures,
1974–2020; gamma conditioning on SPX options 1996–2020.

Net gamma exposure: `NGE = Σ[Γ_call·OI_call − Γ_put·OI_put]·100·P / market cap`.
Take the sign of the open→15:30 return into the final 30 minutes, but **only
when dealers are short gamma**:

| regime | β | t | R² |
|---|---:|---:|---:|
| NGE ≥ 0 (dealers long gamma) | 0.82 | 1.03 | **0.05%** |
| **NGE < 0 (dealers short gamma)** | **6.63** | **4.78** | **3.58%** |

Continuous version: NGE × r_ROD coefficient −123.04 (t = −3.42), surviving a
difference-in-difference control (−119.79, t = −4.06).

This is the only signal in the entire sweep with all of: peer review in a top-3
journal, 45 years of data, four asset classes, a **stated mechanism**
(short-gamma dealers must hedge *with* the move), independent confirmation of
that mechanism through a second channel (leveraged-ETF rebalancing), positive
out-of-sample R², and a **30-minute horizon**.

**It independently reproduces our own in-house result** that 8 of 8 directional
structures pay more in low-gamma regimes. Two different methods, same mechanism.

### Why the naive momentum trade died

The same mechanism explains the decay. Zarattini's SPY intraday momentum,
Sharpe 1.33 published May 2024:

| period | Sharpe |
|---|---:|
| 2007–2024 in-sample | 1.33 |
| May 2024 – Aug 2025 | 1.06 |
| **Sep 2025 – Aug 2026** | **−0.46** |
| pooled post-publication | ~0.35 |

Two independent replications, cross-checked on SPY and ES with 0.97 return
correlation. Dim, Eraker & Vilkov show dealer net gamma is *on average positive*
and that positive dealer gamma converts end-of-day momentum into **mean
reversion**. 0DTE growth pushed dealers long gamma; the unconditional momentum
trade broke. Trading it without the gamma condition is trading the wrong side of
a regime.

Baltussen also re-tested Gao's first-half-hour rule on a broader sample and got
**OOS R² = −1.71%**. Our own measurement — 495 post-publication days, hit rates
46.3–49.4%, all |t| < 1.2 — agrees.

---

## 4. Trade it delta-1, not with ATM options

The effect is a **mean shift of ~2.7bp against a noise level of ~26bp** —
an information ratio of 0.10 per trade. Options do not pay off on mean shifts;
they pay off on exceeding a breakeven, and the premium for that convexity is set
by dealers who know the same distribution.

| vehicle | edge/trade | cost | net |
|---|---|---|---|
| MES futures, full 2.65bp edge | $9.01 | $2.25 | **+$6.76** |
| MES futures, decayed 0.7bp edge | $2.38 | $2.25 | ~0 |
| SPX 0DTE ATM options | 13.2% of premium gross | VRP + spread | **~0 to negative** |

The 0DTE variance risk premium is not merely positive but **specifically
compensates upside risk** (Almeida, Freire & Hizmeri) — precisely the leg bought
when momentum is positive. Long ATM 0DTE is a negative-expectancy vehicle for
this signal.

**If options must be used, use deep ITM (delta ≈ 0.9) or a tight debit
vertical** — capturing ~90% of the mean shift while paying little extrinsic. But
understand that this is paying a spread to synthesize a futures position.

---

## 5. Candlestick and chart patterns: real, and useless

The most precise answer in the whole sweep. "Retail Trader's Ruin" tested a
7-pattern battery on the **Russell 3000 with point-in-time membership and
delisting correction -- 4,152 stocks**, with pre-declared significance,
cost, and survival gates.

**All 7 of 7 patterns are statistically significant. The family is still
refuted.** Maximum Cohen's **d = 0.026** against a materiality floor of 0.2,
and only 1 of 7 is sign-preserving at 5bp of cost.

That is the honest shape of the thing: with 4,000 stocks you can measure the
effect precisely, and the precise measurement is about one-eighth of a
materially relevant effect, smaller than the spread you pay to trade it.

The peer-reviewed intraday tests agree:

| study | test | result |
|---|---|---|
| Duvinage et al. 2013, *Quant Finance* | 5-min bars, 30 DJIA names, SSPA correction | **no rule beats buy-and-hold** |
| Fock et al. 2005, *J. Derivatives* | 19 patterns, intraday DAX & Bund futures | **no predictive ability**, alone or with oscillators |
| Marshall, Young & Rose 2006, *JBF* | 28 rules, EGARCH bootstrap | no rule significant; significant t-stats ran **backwards** |
| Horton 2009, *QREF* | 9 patterns, 349 S&P 500 names | "little value" |

Marshall et al.'s detail is worth keeping: Opening White Marubozu, a *bullish*
pattern, predicted significantly **negative** returns; Long Black and Black
Marubozu, *bearish* patterns, predicted significantly **positive** ones.
Returns after all bullish single lines were positive less than half the time.

### Our own test agrees

Opening-range breakout on 496 SPY and 495 QQQ sessions, entered at the break:
**+1.18 bp (t = 0.34)** and **+5.74 bp (t = 1.36)**. Neither is significant.
The apparent +13 to +23 bp came from measuring the move before the breakout --
see trap #6.

### Two traps specific to pattern literature

**Bulkowski's "average rise" is a perfect-foresight exit.** His own glossary
defines it as the move to the **ultimate high** -- the highest peak before a 20%
decline. You cannot trade to the ultimate high. Every headline percentage in the
*Encyclopedia* is a maximum favourable excursion, not a return. His bullish
engulfing ranks **84th of 103** and the best move 10 days after an upward
breakout is a **drop of 1.18%**.

**The exit rule is the strategy.** Lu, Chen & Hsu crossed 3 trend definitions
with 4 holding strategies: the same eight patterns are profitable with one exit
rule and unprofitable with another, on identical data. Before believing any
pattern, test it against a **random-entry control using the identical exit**.

---

## 5b. We tested the dealer-gamma signal ourselves. It does not replicate.

Section 3 called this the one signal worth building. Built it; it fails.

**Test 1 — SPXW chains, 862 days, 2016-2024.** NGE from same-day options at
10:00, r_ROD = 10:00→15:30, traded 15:30→16:00.

| regime | beta | t | R² |
|---|---:|---:|---:|
| dealers long gamma | 0.03 | 1.36 | 0.37% |
| dealers short gamma | 0.00 | 0.09 | 0.00% |

Interaction term `NGE × r_ROD`: **+0.005, t = +0.19** — insignificant and the
*wrong sign*; Baltussen predict negative. But this test deviates from the paper
twice: a ±2% same-day slice is not the full surface, and r_ROD started at 10:00
rather than the open. A null from a different test is not a refutation.

**Test 2 — the proper version.** Full-surface daily net gamma from Unusual
Whales (`call_gamma + put_gamma`, whole surface), lagged one day, against the
true 09:30 open. 219 sessions each on SPY/QQQ/IWM, Aug 2025 – Jul 2026.

| regime | n | beta | signPnL | hit rate |
|---|---:|---:|---:|---:|
| dealers long gamma | 184 | −0.05 | −1.77 bp | 45.7% ± 3.7 |
| dealers short gamma | 488 | −0.02 | −2.86 bp | 45.3% ± 2.3 |

Baltussen report short-gamma beta **+6.63**. We get **−0.02**.

**The finding that matters is not the failure, it is the indistinguishability.**
Long-gamma and short-gamma days produce the same hit rate (45.7% vs 45.3%) and
the same sign. The regimes are not different, so NGE carries no conditioning
information here — and that conclusion is robust to sign convention, because
flipping the sign merely relabels two rows that are already the same.

Intraday momentum is now mildly **negative** in both regimes: following the
rest-of-day move into the close loses about 2–3 bp and wins under 46% of the
time. That direction is consistent with Dim/Eraker/Vilkov — 0DTE growth pushing
dealers long gamma converts end-of-day momentum into mean reversion.

### Three caveats, stated because they cut against the conclusion

1. **11 months is not a verdict.** 219 sessions cannot distinguish "dead" from
   "dormant." Baltussen have 45 years across four asset classes.
2. **Pooling inflated the t-stat.** SPY/QQQ/IWM are ~0.85+ correlated, so the
   pooled n = 488 is nowhere near 488 independent observations. Per instrument
   only SPY reaches significance (t −2.48); QQQ −1.59 and IWM −1.37 do not.
   This is trap #9 and it applies to our own table.
3. **Sign convention is unverified.** We read dealers as short gamma on 62–88%
   of days; Baltussen report NGE positive on most days. Either UW's convention
   differs from ours or the modern regime genuinely inverted. Unresolved.

**Do not trade the fade.** The inverse of a failed rule, discovered by watching
it fail, is the textbook overfit. It would need its own out-of-sample test.

---

## 6. What this rules out

| claim | verdict |
|---|---|
| Candlestick / chart patterns | see [WHAT_FAILED.md](WHAT_FAILED.md); no pattern survived |
| First-half-hour → last-half-hour (Gao) | dead OOS, in our data and in Baltussen |
| Order flow imbalance at retail horizons | negative OOS R² on better data than ours |
| Options flow (public, Lee-Ready inferred) | Pan & Poteshman: "**no predictability at all from the public signal**" |
| Dark pool prints as smart money | Zhu: theory predicts dark pools attract the **uninformed** |
| VPIN for direction | unsigned by construction; Andersen & Bondarenko show its power is a classification artifact |
| Pre-FOMC drift | 49bp (1994–2011) → 9.2bp, insignificant (2016–2019) |
| ML / deep learning for direction | ceiling 52.5–53.5% on real production data |
| ORB breakout systems | breakeven slippage 2.2¢/share — edge lives inside the spread |
| Unconditional 0DTE credit structures | gross SR 0.77 → **net −0.20** (Vilkov), matching our own null |

### A warning specific to this repo

**MinBTL** (Bailey, Borwein, López de Prado & Zhu): with 5 years of data, more
than ~45 independent configurations is enough to be *almost guaranteed* an
in-sample Sharpe of 1.0 whose expected out-of-sample Sharpe is 0. **With 2 years
of data, that number is 7.**

We have 2 years of minute bars. The bucket-pair matrix tested **91 pairs**. That
is thirteen times the MinBTL limit, and it is exactly why 12 of 78 pairs
appeared significant and why the whole thing collapsed to one outlier day. See
trap #5 in [METHODOLOGY_TRAPS.md](METHODOLOGY_TRAPS.md).

Overfit strategies do not have zero expected out-of-sample return. They have
**negative** expected return — the fitted noise mean-reverts against the position.

---

## 7. What to build

1. **Compute NGE from our own option chains** and validate the Baltussen split
   on 2020–2026. Their sample ends May 2020, before the 0DTE era. Our SPXW
   panel is the right data. Check the sample size of the NGE < 0 regime — it is
   a minority of days.
2. **Gate on predicted move size, not just direction.** Volatility is genuinely
   predictable (OOS R² 0.4–0.7, two orders of magnitude above direction) and the
   hurdle table above is a direct function of move size. Benchmark against plain
   HAR — 1,455 stocks say ML does not beat it.
3. **Institutionalize the slippage-breakeven sweep.** Sweep entry cost 0→5¢ and
   find where the edge dies. This one test kills the entire ORB literature.
4. **Wire purged/embargoed CV with deflated Sharpe** before the next experiment,
   not after (`purgedcv`).
5. **Meta-labeling**: keep existing entry rules, train a classifier on *given
   this signal fired, will this trade win*. Converts an intractable problem into
   a tractable one and monetizes the null results already produced.
