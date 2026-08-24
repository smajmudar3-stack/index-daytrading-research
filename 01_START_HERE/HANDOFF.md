# Options / swing research — state of play as of 2026-08-06

Everything below is measured on **real quotes** (entries at ask, exits at bid) unless
explicitly marked otherwise. Written so the next session can resume without
re-deriving anything.

---

## 1. Data assets on disk

| path | what | rows |
|---|---|---|
| `data/opt_eod/SPY_options.parquet` | real SPY EOD chains 2008-2025, bid/ask + full greeks + IV + OI | 24.7M |
| `data/opt_eod/QQQ_options.parquet` | same for QQQ, 2011-2025 | ~15M |
| `data/spxw/data_opt.parquet` | real SPXW intraday quotes, 1,919 sessions 2016-09 → 2024-05, 30-min grid | 1.37M |
| `data/swing/panel.parquet` | 45 tickers daily 1998-2026 (11 sector SPDRs, broad/style, macro, VIX complex) | 260k |
| `data/stocks/panel.parquet` | 74 liquid optionable names, Tiingo adj daily 2005-2026 (**incomplete — 74 of 190 requested**) | 354k |
| `data/squeeze_dix_gex.csv` | SqueezeMetrics DIX/GEX daily, 15 years | — |

Polygon key is **free tier** — reference data only, no historical option or equity aggs.
Tiingo works for daily equities but has no delisted names (survivorship gap).

**SINGLE-STOCK GAP CLOSED — DoltHub `post-no-preference/options`** (verified live):
**2,321 tickers**, 2019-02-09 → 2026-08-05, updated daily, **free**. Real **bid AND ask**
+ IV + full greeks. Branch is **`master`**, not `main`:

    curl -s --get "https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master" \
      --data-urlencode "q=select * from option_chain where date='2026-08-05' and act_symbol='AAPL'"

Filter by `date` AND `act_symbol` — unfiltered queries hit a server deadline. Only ~3
near-dated expirations per symbol per day (14/30/44 DTE, strikes ±30%) — fine for swing
to ~6 weeks and earnings, useless for LEAPS/far wings. Shipped greeks unstable on
wide-spread ITM (recompute from bid/ask). **Unblocks the pre-earnings straddle test.**

## 1b. DATA HYGIENE — read before touching any chain file
- **SPY `mark` is CORRUPT** — differs from mid in 58% of rows, max deviation $100,000.
  Use bid/ask only. (My backtests already did.)
- 7.1% of SPY rows have `bid == 0`; 2,083 crossed. 2008-09 is monthlies only, so
  sub-14-DTE work is invalid before ~2011.
- `bid > 0` belongs on ENTRY filters only — **never exits**, or you delete the losers.

## 1c. THIRD-PARTY ENGINES — audited, do NOT reuse blindly
- **lambdaclass**: core sound (crosses the spread, retains worthless options at
  intrinsic), but **`iron_condor()` is DEGENERATE** — ignores its own delta/wing args,
  zips legs by row index with no expiration join, resolves short and long call to the
  SAME contract. And **no margin model**: sizes by net CREDIT not max loss ($100k on a
  $1.50 credit = 666 condors = $233k risk).
- **`goldspanlabs/optopsy`** (1,435★): genuine 4-leg definitions and real costs, but no
  capital/margin/sizing.

---

## 2. Scripts written (all use `venv/bin/python3`)

| script | purpose |
|---|---|
| `scripts/swing_data.py` | fetch the 45-ticker daily panel |
| `scripts/stock_data.py` | fetch single-stock daily panel from Tiingo |
| `scripts/swing_lab.py` | signal library + 3-way split harness + deflated Sharpe |
| `scripts/swing_sweep.py` | 3,536-config sweep: sector rotation + regime timing |
| `scripts/stock_direction.py` | beta/residual decomposition, cross-sectional signal test |
| `scripts/option_edge.py` | Black-Scholes + greeks + structure EV + break-even win rates |
| `scripts/strategy_eval.py` | directional signals through real SPY chains, multi-timeframe |
| `scripts/structure_lab.py` | **26 structures × 4 DTE × 2 holds × 11 regimes on real quotes** |
| `scripts/daily_engine.py` | per-trade edge + regime gates + daily/weekly/monthly compounding |
| `scripts/signal_vs_base.py` | signal vs unconditional entry — the decisive benchmark |
| `scripts/stress_spread.py` | measured spread by VIX regime + wrong-way risk |
| `scripts/check_apis.py` | probes what Polygon/Tiingo keys can reach |

---

## 3. THE HEADLINE RESULT — premium selling is negative on real quotes

`daily_engine.py`, 147,350 de-duplicated structure-trades, SPY 2008-2025:

| structure | win rate | avg/trade | t | worst trade |
|---|---|---|---|---|
| iron condor 30/16 | 48.6% | **−15.83%** | −17.5 | −3111% |
| iron condor 16/05 | 63.6% | **−10.54%** | −13.5 | −3111% |
| iron butterfly ATM | 45.9% | **−13.83%** | −20.1 | −425% |
| jade lizard | 65.2% | **−2.88%** | −18.0 | −89% |
| twisted sister | 54.6% | **−0.32%** | −9.4 | −27% |
| broken-wing fly (put) | 55.2% | **−8.94%** | −18.1 | −505% |
| put credit 30/16 | 68.6% | **−11.41%** | −15.4 | −767% |
| put credit 16/05 | 75.7% | **−12.84%** | −17.6 | −1300% |
| call credit 30/16 | 54.7% | **−16.47%** | −10.9 | −6850% |
| christmas tree call | 38.2% | **−23.42%** | −24.5 | −723% |
| short strangle 16d | 68.7% | **−3.79%** | −17.7 | −130% |
| short strangle 30d | 61.2% | **−4.19%** | −18.1 | −127% |
| short straddle | 57.1% | **−4.44%** | −18.3 | −135% |

**Every single one is negative, all with |t| > 9.** High win rates (63-76%) coexist
with deeply negative expectancy — that IS the trap, demonstrated on real fills.

Dominant cause: a 4-leg structure crosses **8 spreads round-trip**, which is ~10% of
capital at risk when capital = (width − credit). Not a modelling artifact; it is the
quoted spread.

### Regime gating does not rescue it
1,001 structure × gate cells tested, including **GEX and DIX** (high/low z-score),
VIX percentile, VIX term structure, IV-minus-RV percentile, breadth, trend.
- Best cell: `put credit 30/16` on `DIX high + VIX>67pct`, +4.30%/trade, t=+3.49
- Multiple-testing bar for 1,001 trials: expected best |t| under the null ≈ **3.72**
- **The best gate does not clear the noise bar.**
- **ZERO of the top 15 gates are positive in all three periods** (2008-13 / 2014-19 / 2020-25).

### Sizing (asked explicitly)
$3,000 start, chronological, real trades:

| structure | 10% | 25% | 50% | 100% |
|---|---|---|---|---|
| iron condor 16/05 | $0 by trade 49 | $0 by 13 | **$0 by 1** | $0 by 1 |
| put credit 16/05 | $0 by 31 | $0 by 8 | **$0 by 1** | $0 by 1 |
| jade lizard | $0 by 96 | $0 by 39 | $0 by 12 | $0 by 4 |
| short strangle 16d | $0 by 86 | $0 by 30 | $0 by 6 | $0 by 2 |

Sizing multiplies whatever sign the edge has. These edges are negative, so bigger size
just reaches zero faster. 0.6% of condor trades are worse than −200% of capital at risk;
one of those at 50% size ends the account.

---

## 4. Directional side — this is where the positive numbers are

`strategy_eval.py`, real SPY chains, 21-day hold:

| structure | win | avg/trade | maxDD (25% size) |
|---|---|---|---|
| call debit 0.70/0.30 | **67-68%** | +10.8 to +15.3% | −52% |
| call debit 0.50/0.30 | 65-67% | +14.6 to +18.6% | −62% |
| deep ITM call 0.80d | 62-65% | +13.4 to +15.4% | −54% |
| ATM call 0.50d | 57-60% | +24.8 to +31.7% | −73% |
| OTM call 0.30d | 47-55% | +28 to +38% | −87% |
| far OTM call 0.16d | **29-43%** | +2.8 to +33.7% | **−96 to −99.6%** |

Win rate rises **monotonically** with delta: 37% → 48% → 58% → 61% → 63% → 68%.
Structure choice moves the win rate 30 points on identical trades.

**CRITICAL CAVEAT — these win rates are largely MECHANICAL, not edge.** A 0.90-delta
call is ~90 shares of SPY minus theta, so its win rate necessarily approaches SPY's
21-session up-rate (~65-69%). Before optimising any exit rule, run the option against
**delta-matched shares** — if the option does not beat the share position, the win rate
is just beta wearing a costume.

**Management rules (evidence):** profit target at 25/50% = FOLKLORE as a return rule;
2x-credit stop = UNEVIDENCED (no public study either way); rolling = FOLKLORE; hold to
expiry = the correct default; close at 21 DTE = real but a RISK rule only. spintwig's
archived pre-paywall studies falsify the tastytrade claim on real quotes: managing at
50%/21DTE had the WORST win rate at every risk level, and on 120,700 SPY condor trades
**56.6% of profits went to commissions**. tastytrade is not an evidence source — its
own footer states the broker-dealer is a subsidiary of the publisher and pays it to
market brokerage services.

**BUT** — see §5. The signals driving these were largely base-rate artifacts.

---

## 5. Signals — what is real and what is not

### Falsified
- **Sector rotation**: 1,512 configs. 40 survived train+validate; **none beat SPY buy & hold**.
  Independent repo audit found the two best open-source projects publish the same null.
- **Dip-buying** (`breadth_hi+dip3`, `above50+dip3`): **base-rate artifact.** SPY's
  *unconditional* 21-day win rate is 60.1% / 69.5% / 68.8% across the three splits.
  `breadth_hi+dip3` wins 61.3% in test — **7.5pp BELOW** buying on a random day.
  The trend filter actively *lowers* forward return in every split.

### Survives on the underlying
- **`backward + golden`** (VIX ≥ VIX3M inside a golden cross): excess mean 21-day return
  of +1.3 to +1.8pp over base, **t = +3.90 / +2.84 / +2.06 across all three splits**.
  Mechanism: Nagel 2012 RFS "Evaporating Liquidity" — reversal returns rise with VIX,
  driven by intermediary funding constraints. Structurally hard to arbitrage.
  Caveat: effective n ≈ 20-35 independent episodes. Do not tune it.

### Does NOT survive into options
`signal_vs_base.py`: `backward+golden` tested against buying the **same call on a random
day**. Only 1 of 24 configurations beat unconditional entry in all three splits, at
**t = +0.07**. Reason is mechanical: the signal fires when VIX spikes, i.e. exactly when
options are most expensive. You pay for the edge in IV.

**→ Express it in shares or deep-ITM/ZEBRA, not in premium.**

---

## 6. Measured costs (real quotes, not assumed)

SPY option spread, median % of mid, 20-60 DTE, OI>10:
- deep ITM (0.75-0.95Δ) **1.34%** · ITM 1.37% · **ATM 0.75%** · OTM 0.87% · far OTM 1.30%
- U-shaped with the minimum at ATM (differs from the monotonic ITM-cheapest pattern
  Muravyev-Pearson report for single stocks — SPY's ATM liquidity is exceptional)

By VIX regime: <15 → 1.75%, 15-20 → 1.27%, 20-25 → 1.19%, 25-30 → 1.23%, 30-40 → 1.35%,
**>40 → 2.01%. Only 1.15× wider in extreme stress** — the blowout is far milder than
folklore claims. Worst episodes: 2011 downgrade and 2015/2018 shocks at ~1.8× calm.

**Costs are NOT what kills these strategies.** The absent edge is.

Single stocks are a different world: median 4.51% (NVDA 0.80% → PANW 13.66%), ~6× SPY.
Robinhood all-in SPY round trip ≈ $0.095/contract; index options $0.50/contract each way.

---

## 7. Key literature conclusions (14 agents, primary sources verified)

- **VRP is index-only.** Driessen-Maenhout-Vilkov: index IV−RV **+3.77 vol pts** vs
  single-stock **−1.35**; zero VRP unrejectable for **108 of 135 stocks**. It is a
  *correlation* risk premium — a single stock has no correlation to sell.
- **Dew-Becker & Giglio (Chicago Fed WP 2025-17)**: option alphas indistinguishable
  from zero for 15 years; **zero cumulative return on traded puts Mar 2009 → Dec 2022.**
- **CBOE's own condor index CNDR**: −0.70%/yr 2010-2019, +1.61% 2020-2026, negative
  Sharpe in both. Its entire positive record predates 2010.
- **Weekly < monthly**: WPUT collects 37.1%/yr premium vs PUT's 22.1% and has earned
  LESS for 20.5 years; gap widened to 5.1pp/yr since 2019. Premium scales as √T —
  more premium is an accounting identity, not edge.
- **CORRECTED — the "PUT beats PUTY by 0.23 Sharpe over 40 years" claim is WRONG.**
  Cboe's public `PUT_History.csv` is continuous only from 2007-01-03, so a 40-year
  comparison cannot be built from the primary source. On the common 2007-2026 sample
  (n=235 months): PUT excess Sharpe **0.552** vs PUTY **0.448** — difference **+0.104,
  not +0.23** — and Memmel-corrected Jobson-Korkie **z=+1.90, NOT significant at 5%**
  (correlation 0.971). The sign even flips by subperiod (2013-2018: PUTY 0.86 > PUT 0.76).
  Also 2% OTM on 1-month SPX is ~30-35 delta, so PUT-vs-PUTY is 50D vs ~32D and never
  reaches the 10-16D region at issue. **It is not a test of the delta question.**
- **The delta "optimum" is PART artifact, part real.** The CAGR ranking IS a
  normalisation artifact (margin is ~delta-invariant, so equal margin utilisation means
  wildly unequal risk: SPY short put max DD −11.62% at 2.5D vs −67.83% at 50D). But
  **Sharpe is invariant to leverage at the risk-free rate** — verified numerically —
  so a Sharpe ranking CANNOT be a leverage artifact. The real distortion is that
  spintwig computes Sharpe as CAGR/vol with **no risk-free subtraction**, biasing
  low-vol (low-delta) cells upward by rf/vol. Correcting it (avg 3m T-bill 0.859% over
  their sample): best SPY condor cell **0.91 -> 0.45**, and cells beating buy-and-hold
  collapse from **21/40 to 4/40**. A genuine interior optimum survives at **~10-16 delta**
  on two leverage-invariant comparators.
- **"45 DTE optimises theta/gamma" is mathematically false**: Θ/Γ = −½σ²S², invariant
  to DTE. tastytrade is the brokerage, the media arm AND the research publisher.
- **Broadie-Chernov-Johannes**: naked OTM put returns are statistically INSIGNIFICANT
  vs a stochastic-vol null (p=24%). Only **delta-hedged / ATM straddle** survives.
- **Independent real-quote tests** (213 non-overlapping SPY trades): long straddle
  −3.28%/trade, long strangle −20.5% (median −100%), short straddle +2.21% t=0.40,
  short delta-hedged straddle +4.31% t=+1.53 and **decaying** (7.6→4.8→4.1→3.5).
- **Earnings**: Gao/Xing/Zhang JFQA 2018 — delta-neutral straddles earn **+2.3%** from
  one day BEFORE the announcement to the announcement. Retail has the sign backwards;
  the trade is BUYING pre-earnings, not selling. Unverified after costs.
- **Ruin math**: a 90%-win condor at 10% of width has a breakeven win rate of exactly
  90% — **zero edge by construction**. Defined-risk max loss = **12.9× credit**.
  CORRECTED frequency: **18 distinct episodes since 2007, one every ~1.1 years** (not
  one per 3.8 years) — at 12.9× credit that is roughly break-even before costs.
  Loss-to-credit on a short 16d strangle: Feb 2018 **10.1×** in 9 sessions, Mar 2020
  **35.5×** in 23 sessions, Aug 2024 **4.0×** in 3 sessions. Feb 2018 and Aug 2024
  needed only −10.2% and −8.5% moves. NOTE: Feb 2018 never breached on a SETTLE basis
  (−6.19%), only on the touch (−10.16%) — settlement-only backtests understate losses.
- **"Sell premium only when calm" is dead**: mean RV÷IV is 0.75-0.81 and p99 is 1.8-2.3
  in EVERY VIX quintile since 1990. The VIX level tells you almost nothing about your
  worst-case credit multiple. (The "all ten worst inversions began at VIX 14-17" claim
  is FALSE — four began at VIX 25-32. Do not repeat it.)
- **PDT rule was eliminated 4 June 2026** (FINRA RN 26-10).

---

## 8. Bugs found and fixed in my own code (all produced spectacular fake results)

1. **Capital-at-risk ignored naked legs** — jade lizard denominator used only the call-spread
   width, ignoring the naked put. Inflated returns ~50×, produced +800%/yr. Fixed via
   `max_loss_at_expiry()` evaluating the real payoff across a terminal price grid with
   unbounded-tail detection.
2. **Survivorship filter on the exit chain** — `bid > 0.02` applied to exit quotes deleted
   every option that expired worthless, i.e. **deleted the losers**, producing 100% win
   rates. Fixed by splitting entry/exit universes + intrinsic-value fallback.
3. **Duplicate trades** — two DTE targets resolving to the same expiry double-counted
   (153,340 → 147,350 after de-dup).
4. **Calendar annualisation** — annualised by elapsed time for signals firing ~5×/year,
   understating a daily-frequency strategy. Now compounds on trade count × gate frequency.
5. **`pct_change` pad-fill** — fabricated returns across pre-inception NaNs for XLRE/XLC.

**Every bug failed in the flattering direction.** That is not coincidence: denominator
errors and survivorship both push the same way.

---

## 8a. INDEPENDENT REPLICATION — separate code, same file, same answer

| structure | my run | independent run |
|---|---|---|
| monthly condor 30/16 | 48.6% win, −15.83%, t=−17.5 | 49.7% win, −8.14%, t=−19.9 |
| monthly iron fly ATM | 45.9% win, −13.83%, t=−20.1 | 41.1% win, −11.74%, t=−20.4 |

Signs, win rates and t-magnitudes all agree. **Two independent implementations now
reach the same conclusion.**

### The key refinement: TWO different failure modes
- **Near-the-money structures are negative at MID prices, before any cost** — monthly
  30/16 condor −2.24%, monthly ATM butterfly −4.86% of risk per trade with zero costs.
  **Better fills cannot save these.**
- **Far-OTM structures (16/05, 10/05) are POSITIVE at mid** (+1.25%, +1.41%) and are
  killed purely by the round trip. Break-even fill quality for monthly 10/05 is ~50-60%
  of the quoted spread — achievable in principle, worth ~1%/yr at 5% sizing.

So "get better fills / widen the wings" is coherent research for far-OTM condors and a
waste of time for butterflies.

### Spread drag, measured (medians, ask-in/bid-out)
30/16 condor and ATM/16 butterfly **4.2-4.8% of capital at risk** (my ~10% is a fair
MEAN — the distribution is heavily right-skewed); far-OTM condors 1.2-2.2%;
**0.5%-wing 0DTE butterfly 18-26%**. **Wing width, not delta, drives this.**

### 0DTE butterflies — the decisive measurement
On ~1,390 sessions of real SPXW quotes the ATM straddle is priced at **fair value**:
realised/implied **0.978-1.007 at every hour**, short straddle at mid earns +0.3 to
+0.9bp (t <= 0.85). **There is no 0DTE ATM variance risk premium.** All 36
structure x time x wing cells are negative once you cross the spread once.

**Profit targets are strictly HARMFUL at 0DTE on real quotes**: the 16d condor goes
78.9% -> 85.4% win rate while the mean goes −0.68 -> −1.30bp. The tastytrade result
reproduces exactly on the win rate and inverts on the money.

### CNDR sharpened
CNDR's +1.66%/yr in 2020-2026 is **entirely T-bill interest** — excess is **−1.18%/yr**,
so the overlay lost in BOTH windows. Alpha to SPX 2010-2026: CNDR −2.74%/yr, BFLY
−5.86%/yr. Control: PUT's +6.42%/yr excess is **beta 0.63 with alpha +0.01%**.
**No alpha in any of these programmes since 2010.**

### lambdaclass, verified further
It IS the source of `data/opt_eod/`. Default fill is `MarketAtBidAsk` (honest), settles
expiries at intrinsic (immune to the worthless-leg bug), no `bid > 0` filters. Caveats:
**default commission model is `NoCosts`**, and **upstream provenance is undocumented**
(philippdubach/options-data, now gone; unknown whether the quotes are NBBO).
`isaaclee2/Iron_Condor_Backtest` is a textbook instance of the exit-filter bug
(`iron_condor_backtest.py:169-172`), then cherry-picks `.min()`/`.max()` on top.

## 8b. EXOTIC STRUCTURES — independently tested, all dead

Verdicts from a clean run (held to expiry, settled at intrinsic, so no exit chain is
consulted and the worthless-option bug is structurally impossible). 850 weekly entries
at 35 DTE, normalised to 100 SPY deltas:

- **ZEBRA**: does NOT strip extrinsic to zero but cuts it **8.2x** ($26.33 vs $216.31 for
  a 0.80d call). Costs **1.52x more in spread** (6 crossings vs 2). After costs it is
  **statistically indistinguishable from just buying the 0.80d call** (paired −$2.12,
  t=−0.31 at 35d; +$7.59, t=+0.67 at 90d). **SHARES beat both significantly: −$87,
  t=−3.95.** Why the $190 extrinsic saving doesn't convert: extrinsic is not a cost, it
  is the price of convexity — the ATM call loses least in crashes and gains most in
  rallies. ZEBRA is a faithful stock substitute, which is exactly why it has no edge.
  **Verdict: a tool, not an edge. And it needs a signal we do not have.**
- **Gamma scalping**: costs are NOT the problem (Leland's term is 0.14% of vol on
  penny-wide SPY). The mean is: replication gives **−4.54% net, profitable 37% of the
  time, median −12.3%**. Bakshi-Kapadia's $0.43 loss vs a $0.375 spread — the VRP is
  one round trip wide.
- **Box spread**: real economics (van Binsbergen-Diamond-Grotteria JFE 2022), edge
  **0.40%/yr** against a measured SPY crossing cost of **5.1-12.5%/yr — 13-31x**. SPY
  boxes price ABOVE their own payoff at <=6 months (American exercise breaking parity).
  1R0NYMAN: ~$5k -> −$58k. SPX only, if ever.
- **Jade lizard**: "credit > call-spread width" is satisfiable on **100% of dates** —
  it trivially eliminates a risk that never existed while **$38,343 of downside remains**.
- **Twisted sister**: collects $215 for UNBOUNDED risk vs the lizard's $355 for bounded.
  It sells the cheap wing naked.
- **Broken-wing fly**: min-risk credit version collects **$16 against a $15 round-trip
  spread — 94% of the credit**.
- **Christmas tree**: crosses **12 spreads**, 5.0% of max risk at 35d and 16.5% at 90d.
  Matches its worst-of-everything ranking.

**The premium itself has decayed to nothing**: the 25-delta put seller's edge went
−13.79% (2008-25) -> −10.68% (2013-25) -> **+0.40%, t=0.05 (2018-25)**.

**GitHub: ZERO backtests of any of these structures against real bid/ask exist.** Only
payoff plotters, broker templates, strike screeners, and one gamma-scalping "backtester"
that prices from Black-Scholes — the exact error that burned this repo twice.

## 8c. BREAK-EVEN ACCURACY BY STRUCTURE (calibrated to MEASURED spreads)

SPY, 43 DTE, base rate 67.1%. "sign-only" = what a direction-only signal must deliver.

| structure | capital $ | B/E (sign-only) | vs base rate | friction |
|---|---|---|---|---|
| **shares, long** | 76,876 | **56.0%** | **−11.1pp** | 0.00% |
| long call 0.16d | 222 | **79.0%** | +11.8pp | 0.67% |
| long call 0.30d | 504 | **72.0%** | +4.9pp | 0.44% |
| long call 0.50d | 1,038 | **67.0%** | −0.1pp | 0.38% |
| long call 0.70d | 1,977 | **64.2%** | −3.0pp | 0.69% |
| long call 0.80d | 2,790 | **63.2%** | −3.9pp | 0.67% |
| ZEBRA | 2,920 | **63.3%** | −3.8pp | 1.06% |
| call debit .70/.30 | 1,476 | **61.9%** | −5.2pp | 1.07% |
| put credit .30/.16 | 1,306 | **60.0%** | −7.1pp | 0.67% |
| butterfly | 258 | **60.9%** | −6.3pp | **3.84%** |
| put debit .50/.30 (bear) | 664 | **39.9%** | +7.0pp | 1.65% |

**A 60%-accurate direction-only signal fits SHARES and essentially nothing else.**
Break-even falls monotonically as delta rises: the lower the delta, the more MAGNITUDE
information you must supply, and a sign classifier supplies none.

**CORRECTION to an earlier claim in this file.** I previously wrote that an OTM credit
spread "needs 67-80% accuracy to break even." That was **quantity confusion** — three
different numbers get called "win rate": the naive figure (87%), the structure's own win
rate (79%), and the actual requirement on YOUR SIGNAL (60.0%). Only the last is a
constraint on a signal. The conclusion survives (a 57.9% signal still misses 60.0%) but
the number was the wrong quantity.

**Shares are uniquely robust to the unmeasurable parameter.** Across kappa in [0.90,0.97]
shares move 0.1pp; the 0.16d call moves **22pp** (67.5% -> 89.6%). A conclusion that
swings that far on a parameter nobody can pin down is not a conclusion.

**One flagged divergence, resolved in favour of the real-quote measurement.** The model
puts the 0.16/0.05 condor at +2.8%/trade against my measured −10.5%. The model holds to
expiry and therefore never pays 8 crossings or books a mid-trade loss — most of a
condor's theoretical edge lives in the final three weeks. **Prefer the measurement.**

## 8d. WHY THE LITERATURE AND MY NULL DO NOT CONFLICT (verified reconciliation)

1. **ERA — dispositive on its own. No founding paper has a single observation inside
   2008-2025.** Coval-Shumway 1990-95, Bondarenko 1987-2000, BCJ 1987-2005, Whaley
   1988-2001. Zero overlap.
2. **Coval-Shumway's only cost-realistic result is an EQUITY OVERLAY, not a premium
   structure** — short ATM straddle + long 15% OTM put + principal invested in the index
   (Table VI, real bid/ask, monthly Sharpe 0.31 ~ 1.08 annualised). Israelov-Nielsen
   decompose it: short vol earns Sharpe ~1.0 but contributes only **10% of the risk**.
   A delta-neutral condor is that sleeve **with the equity carry deliberately stripped
   out** — you removed the component that made the money.
3. **BCJ already showed SPREADS are where the evidence is weakest.** Put spread
   p-values **12.5-17.1%**, "less significant than individual put returns." An iron
   condor IS two vertical spreads. Under a no-VRP null, Black-Scholes predicts −11.1%
   for a long put spread purely from **leveraged equity premium** — so most of the
   apparent "premium" in a spread was never a volatility premium at all.
4. **The premium is a TAIL premium.** Bollerslev-Todorov (JF 2011): **88.4%** of the
   variance risk premium comes from the left tail (~20-75% depending on method).
   A 5-delta long wing caps the payoff **exactly where the premium lives** while
   retaining the body's negative skew — a coherent mechanism for a defined-risk condor
   being worse in expectation than a naked strangle.
5. **Regime instability inside the founding sample.** BCJ: for 29 months (10/2000-02/2003)
   put BUYING returned +45% to +67%/month. "Average put returns are unstable over time."
6. **The 1,001-cell null is the EXPECTED result.** Cederburg, O'Doherty, Wang & Yan
   (JFE 138, 2020), 103 strategies: vol-managed portfolios "are not implementable in
   real time... poor out-of-sample performance stems primarily from **structural
   instability in the underlying spanning regressions**."
7. **VIX-percentile gating is backwards.** Cheng (RFS 32, 2018): ex-ante volatility
   premium **falls or stays flat when ex-ante risk rises**. March 2020 confirms — VIX
   futures premiums "turned sharply negative and remained negative until mid-April,"
   precisely when a contango/VIX gate would have been most bullish on selling.
8. **Johnson (JFQA 2017) on VIX term structure is IN-SAMPLE predictive regression only** —
   it makes no out-of-sample trading claim. Do not cite it as gate evidence.

**"The iron condor specifically has no serious academic literature. Your backtest is
closer to primary evidence on that structure than anything published."**

### Cboe's own 40-year indices — the cleanest independent confirmation
Zero transaction costs, collateral in T-bills, excess-return Sharpe, 1986-06 -> 2026-08:

| index | construction | CAGR | Sharpe | maxDD |
|---|---|---|---|---|
| **CNDR** | 20d shorts / 5d wings, monthly | 5.31% | **0.35** | −19.0% |
| **BFLY** | ATM straddle / 5% OTM wings | 3.52% | **0.10** | **−53.4%** |
| PUTY | 2% OTM putwrite | 6.85% | 0.46 | −28.9% |
| BXMD | 30d buywrite | 10.63% | 0.62 | −42.7% |
| SPX +2% divs | total-return proxy | 12.39% | 0.57 | −51.2% |

**The two four-legged defined-risk structures are the WORST in Cboe's own family,
before any transaction costs.** Iron butterflies: 0.10 Sharpe with a 53% drawdown over
40 years. Over 2007-2019: CNDR **0.40% CAGR, excess Sharpe −0.02**; BFLY **−2.84% CAGR,
Sharpe −0.27**. CNDR's 40-year 0.35 lands almost exactly on the rf-corrected spintwig
value of 0.36 — two independent routes agreeing.

**Vilkov (SSRN 4641356, MIT-licensed replication package) is the only 0DTE source with
no commercial stake**: 0DTE iron fly/condor mean **−0.0073%/day at mid, −0.0125% after
half-spread**, Sharpe **−0.56 -> −0.96**. His best ML-timed version goes **SR 0.77 gross
-> −0.20 net**. For this structure the cost model IS the entire result — any backtest
marking 0DTE condors at mid is measuring nothing.

## 8e. THE HONEST PRIOR — read this before believing ANY future backtest

Computed directly from the Open Source Asset Pricing library (212 predictors, 1926-2024)
plus five meta-studies.

**The shrinkage formula. Apply it before believing any number:**

    post-publication mean (%/mo) = -0.122 + 0.61 x (in-sample mean %/mo),  R^2 = 0.19

**Read the intercept: a signal with ZERO true in-sample edge is expected to LOSE 12bps
per month going forward.** You keep ~61% of whatever in-sample edge you had. Then
subtract costs.

**Survival conditional on in-sample t (this IS the prior):**

| in-sample t | n | in-samp mean | post-pub mean | survival | frac post-pub t>1.96 |
|---|---|---|---|---|---|
| t < 2 | 20 | 0.384%/mo | 0.108% | 28% | **0%** |
| 2-3 | 64 | 0.493% | 0.164% | 33% | 23% |
| 3-4 | 47 | 0.716% | 0.391% | 55% | 23% |
| 4-6 | 46 | 0.863% | 0.448% | 52% | 46% |
| t > 6 | 29 | 1.139% | 0.384% | 34% | 55% |

**DEMAND in-sample t >= 4.0 (4.5 for a large grid). t=2 is worthless; t=3 is where
published anomalies sit and they die anyway.** Median in-sample t of 3.26 collapses to
median post-publication t of **1.13**.

**Base rate: P(a self-mined candidate has a real, net-of-cost edge) ~ 1-3%.**
- Chen & Velikov (JFQA 2023), 120 anomalies net of costs: average expected return
  **8bps/month (SE 4)**, 4bps value-weighted, "statistically indistinguishable from
  zero." **Only 11 of 120 have post-pub t>2.0, vs 6 expected under the PURE NULL.**
- Goyal-Welch-Zafirov (RFS 2024): **0 of 17** predictors significant both IS and OOS;
  **45/45 underperformed unconditional buy-and-hold**; 20/45 lost money outright.
- Chen-Lopez-Lira-Zimmermann (2025): mining 29,000 ratios for t>2 gives **the same
  post-sample survival as peer review**. Peer review buys you nothing.
- Applying a 30bps/month cost to every OSAP predictor's post-publication return:
  **mean net = −0.004%/month, only 40.5% positive.**

**In the last decade (2015-2024, 208 predictors, GROSS of costs): 15.9% have t>1.96,
4.8% have t>2.78, 3.4% have t>3.0, and 28.4% have a NEGATIVE mean.**

## 8f. RETRACTION — the option-implied predictor family is NOT the next step

I previously flagged option-implied cross-sectional predictors (IV spread, skew, O/S) as
the most promising untested direction. **Withdrawn.**

**Muravyev, Pearson & Pollet, JFE 172 (2025), art. 104153.** OptionMetrics implied
volatilities are computed **assuming a zero stock borrow fee**, and a nonzero borrow fee
moves call and put IVs in OPPOSITE directions. So the academic volatility spread and skew
are, by construction, near-linear transforms of **the short borrow fee** — itself one of
the strongest known return predictors. Verbatim: *"When we adjust returns for the borrow
fees, the abnormal returns on the tenth decile spread-sorted and skew-sorted portfolios
are only about one-third as large, and not significantly different from zero."*
Excluding high-fee stocks (only ~7% of observations) leaves decile-10 returns
**insignificant and <30% as large**. **The signal is real and unavailable to retail** —
you cannot capture a borrow-fee premium you have to pay.

**Decay, computed per signal from OSAP** (in-sample -> post-publication):
CPVolSpread −53% · RIVolSpread −85% · dVolCall −32% · dVolPut −41% · dCPVolSpread −49% ·
OptionVolume1 −87% · **OptionVolume2 −133% (now NEGATIVE)** · skew1 −72% · SmileSlope −53%.
Aggregate for the 9 option signals **−63.6%**, vs −56.7% for the 203 non-option
predictors — **option signals decay faster than average.**

**Only Yan (2011) SmileSlope is still clearly alive gross of costs** (2019-2023: +0.894%/mo,
t=2.38) — **and it is one of exactly the two signals MPP show is mostly a borrow-fee
proxy, short-side driven.** Johnson-So O/S is negative over the last five years.

Also: **Eaton, Green, Roseman & Wu (JFE 2026)** — retail traders are net buyers of
short-dated OTM options and brokerage outages causally LOWER implied vol, so the
post-2020 IV surface is materially shaped by uninformed retail flow, contaminating
exactly the ATM/OTM differentials these signals are built from.

**Caveat: OSAP's option series end January 2023.** There is no evidence here for 2024-2026.

## 8g. THE ONE LIVE LEAD — intermediary-state variables, not price/vol variables

My 1,001-cell null over VIX percentile, VIX term structure, IV−RV and GEX/DIX is
**exactly what the literature predicts**. Every gate I tested is price- or vol-based.
The conditioning variables that still identify non-zero option alpha are
**intermediary-state** variables, and I tested none of them in the form the papers use.

**1. Johnson's SLOPE — and I tested the WRONG THING.** Travis Johnson, *JFQA* 52(6)
2461-2490 (2017). SLOPE is **NOT VIX/VIX3M**. It is the **second principal component of a
SIX-point VIX term structure** (1, 2, 3, 6, 9, 12-month model-free implied vol, VIX-style,
from OptionMetrics). His real-time test (expanding-window PCA, 1996-99 training): when
SLOPE is in its **bottom quintile, BUY straddles; otherwise short them**. That beat the
unconditional short-straddle **by a factor of 4.8 over 14 years, 11.9%/year**.
Three caveats from his own text: returns use **bid-ask midpoints** ("overstate returns
available to real-time investors"); much of the gain is late 2008 when the rule was LONG
vol into the crash; **the value is in flipping to long vol, not in selling harder**; and
the sample ends 2013, before 0DTE existed. Counterintuitive sign: variance risk premia
are large when short-term VIX is LOW relative to long-term.

**2. Signed dealer net gamma != retail GEX. This is probably why my GEX cells were null.**
Dew-Becker & Giglio construct net gamma from **CBOE open-close data**, which classifies
each option's daily buy/sell orders **by entity type** (intermediaries = neither customer
nor firm), with gamma from OptionMetrics, 10-180 day maturities. Retail GEX (including
the SqueezeMetrics series I used) is built from **open interest with ASSUMED signing**.
Their traded-minus-synthetic alpha **loads positively** on lagged exponentially-weighted
intermediary net gamma. Different variable, not a different threshold.

**3. PNBO / intermediary constraint.** Chen, Joslin & Ni, *RFS* 2019 (open: NBER w25573).
Public net buying of deep-OTM SPX puts identifies shocks to intermediary constraints:
"a tightening... is associated with increasing option expensiveness, higher risk premia
for a wide range of financial assets, deterioration in funding liquidity, and
broker-dealer deleveraging."

**4. Intraday inventory (0DTE).** Dorion, Orlowski & Song (SSRN 7149778, 2026):
"Option alphas fall as inventories build and, secondarily, intermediary balance sheet
conditions tighten." But also: "**a factor-neutral strategy becomes infeasible under
minimal transaction costs.**"

### Dew-Becker & Giglio, precise
Break test identifies **2012m5**. Traded 5% OTM put information ratio moved **−0.6 -> +0.09**.
Synthetic options showed **no** significant change — traded converged to synthetic.
The exact qualifier to quote: *"There is still a premium for variance risk, but... the
premium is no larger than what would be expected from the CAPM beta."* A beta-only
premium does not survive transaction costs. **That is precisely why every structure I
tested is negative and why CNDR has lost for 15 years.**

### 0DTE specifics
- **The 0DTE premium is UPSIDE-driven; the monthly premium is DOWNSIDE-driven.** They are
  not the same premium scaled (Almeida, Freire & Hizmeri, SSRN 4701401).
- Same paper: a strategy exploiting 0DTE price-bound violations was "**highly profitable
  up to 2022, but dissipates after the daily availability of 0DTEs**."
- **Wilkens (SSRN 7094758, 2026)** — best 0DTE cost numbers found: put-call parity holds
  tightly at MID, but "once the spread is crossed, the round-trip cost... is roughly
  **fifteen to twenty times larger, near 10% and 13% of the ATM straddle premium**...
  rising to roughly **40% and 70% of the straddle value in the final half-hour**."
- Dew-Becker/Giglio/Le/Rodriguez (JFE 2017) **cannot** be used to argue 0DTE VRP is
  richer than monthly — their shortest instrument is ONE MONTH.
- Whether 0DTE raises or dampens underlying volatility is **unsettled** — Brogaard-Han-Won
  say raises, Adams et al. (resubmitted RFS) say dampens.

## 8h. SKEW IS THE UNTESTED VARIABLE — and a third confirmation of the GEX/DIX null

**All 1,001 of my dead regime cells conditioned on VOL or POSITIONING proxies (GEX, DIX,
VIX percentile, VIX term structure, IV−RV). Realized SKEWNESS is untested in my work.**

From `vilkovgr/0dte-strategies` (Vilkov, Frankfurt School, SSRN 4641356) — real Cboe
30-min SPXW NBBO bars, 2016-09 -> 2026-01 — the only BH-corrected, clustered-SE-robust
result in the package: **realized skewness explains 20-40% of 0DTE structure PNL**.
Bull Call **t=8.64**, Bear Put **t=−8.74**, Risk Reversal **t=7.30**, all **q<0.001**.
A trailing-RV VRP gate by contrast fires on 87.3% of days with 16 transitions in
3.5 years — structurally too slow to time anything.

**Third independent confirmation of my GEX/DIX null**: `marcusdrewry/gex-forward-returns`
regressions show **DIX insignificant at every horizon**. (Note this is the RETAIL
open-interest-signed GEX — see 8g for why signed dealer gamma from CBOE open-close data
is a genuinely different variable.)

**Vilkov's own defect, worth knowing before replicating him**: his modelled half-spread is
~50-100x too small (0.065% of gross premium for a 4-leg 0DTE condor; truth is 3-6%) —
almost certainly a fraction-vs-percent unit mismatch. His net edge (0.0198) is the same
size as his total cost charge (0.0053), so **his put ratio spread likely goes negative
once fixed.** Cheap verification: compare `median(bas/mid)` in his parquet against our own
SPXW chains at 10:00 ET. His PNL is expressed **in percent of underlying notional, not
premium** — that normalisation sidesteps the naked-short-leg denominator trap I hit.

### Engines worth stealing
- **`YichengYang-Ethan/0dte-strategy` -> `src/pipeline/leak_safe.py`**: `future_poison_test()`
  randomizes every post-cutoff row, re-runs, asserts bit-identical output. **This would
  have caught the bug in half the broken repos — and arguably two of mine.**
- Vilkov's walk-forward harness: correct `fit_transform(train)`/`transform(test)`,
  clustered SEs, Benjamini-Hochberg, structural-break test.

### Broken repos — named, do not replicate
- `iulianallroad-glitch/gamma` (claims $25k->$5.1M): exit valuation takes **no
  time-to-expiry argument**, so every spread marks at zero on entry and books ~100%
  profit instantly (`backtest.py:320`). Also ships live Tradier keys.
- **`emlama/gex-backtesting`**: exit returns `None` when no trades occur, so decayed-to-zero
  puts silently drop out — **my own survivorship bug in a new costume.** Also buys at bid,
  sells at mid. (This is the repo an earlier session flagged as a promising data source.)
- `repque/vrp`: P&L is `position x pct_change(VIX spot)` — untradeable index, no instrument.
- `puneet-chandna/0DTE-dealer-gamma`: no `.shift(1)`, fills on the signal bar's close.
- `Matteo-Ferrara/gex-tracker` (207 stars): ships a cached `SPX.json` from May 2022 and
  silently serves it as current GEX.
- `grantreed1/Cross-Asset-Macro-Volatility`: Sharpe 1.97 from a Taylor-expanded straddle
  re-struck daily for free.

**DoltHub coverage note:** a second agent reported ~2020-02 -> 2024-11 with gaps; my own
live query returned 2026-08-05 data successfully, so the wider range (2019-02 -> present,
daily) is correct. No open interest column. A ready-made client exists at
`quanttqueensu/earnings_iv_crush/.../dolthub_options.py`.

## 8i. THE THROUGH-LINE, AND THE THREE EXPERIMENTS WORTH RUNNING NEXT

**Two papers independently reproduce my exact result.** Vilkov (SSRN 4641356), SPXW
0DTE 2016-09 -> 2026-01: iron butterfly/condor **SR 0.77 gross -> −0.20 net** once
half-spread + 0.5bp is charged; median VRP from 10:00 ET to expiry ~**0.11 bp of spot**,
"too small to monetize after realistic trading frictions." Almeida, Freire & Hizmeri
(SSRN 4701401), CBOE intraday SPX with bid/ask 2012-2023: naive short-ATM-delta-hedged
benchmark **gross Sharpe 0.004-0.043**, **net −0.032 to +0.013**. My SPY EOD result is
the strong-form version of the same fact.

**Almost nothing in 0DTE asset pricing is peer-reviewed.** "SSRN Electronic Journal" is
a preprint deposit, not a journal. Of the ~11 headline 0DTE papers, ALL are working
papers, several circulating 2+ years. The genuinely refereed 0DTE list is an econometrics
estimator, a vol-forecasting paper, a VRP decomposition, and two pricing-numerics papers.
**Not one refereed paper says 0DTE selling makes money.**

### THE THROUGH-LINE
**Dealer gamma is real, but it shows up in the UNDERLYING's intraday path — not in
harvestable option premium.** That single sentence reconciles the whole project: the
gamma/range finding from the prior session was real (t=−13.2 over 15 years) and did not
convert to profit; the GEX gating here was null; and the one published, replicable,
gamma-conditioned signal trades futures, not options.

### EXPERIMENT 1 (highest EV) — Baltussen, Da, Lammers & Martens, JFE 142 (2021)
The only PUBLISHED, replicable, dealer-gamma-conditioned index signal. 60+ futures,
1974-2020. At 15:30 ET compute r_ROD = P(15:30)/P(prev close) − 1; if dealer net gamma
exposure < 0, take sign(r_ROD) into the close; else no trade.

| condition | beta_ROD | t | R2 |
|---|---|---|---|
| **NGE >= 0** | 0.82 | 1.03 | **0.05%** |
| **NGE < 0** | **6.63** | **4.78** | **3.58%** |

Unconditional equity-futures **SR 1.73 gross** (6.86%/3.96%), OOS R2 2.88%, positive in
14 of 17 contracts. Costs NOT netted — authors assert positive net SR at 1-tick in ES.
**No clean post-2021 US OOS test exists, and 2021-2026 is exactly the 0DTE era when NGE
dynamics changed most. That gap is the experiment.** We have SPY EOD chains to build NGE;
need intraday SPY prints for r_ROD.

### EXPERIMENT 2 (cheapest, decisive) — split the sample at 2012m5
Dew-Becker & Giglio identify a structural break at **2012m5** in dealer net gamma;
traded 5% OTM put information ratio moves **−0.6 -> +0.09** (significant), while SYNTHETIC
options show no change. On our SPY/QQQ chains 2008-2025, estimate the 1-month delta-hedged
short-vol alpha pre- and post-2012m5. **If we reproduce −0.6 -> +0.09 we have independently
confirmed a 2025 Fed working paper and can stop looking for carry entirely.**
Note DBG et al. (JFE 2017) term structure: zero-coupon variance claim Sharpe **−1.4 at
1 month, −0.5 at 2 months, ~0 at 3 months to 14 years** — so if carry exists anywhere it
is at 1 month, NOT 0DTE. Do not extrapolate "shorter is better" to 0DTE: the premium per
unit time may rise but the spread per unit premium rises faster.

### EXPERIMENT 3 (falsify, don't trade) — Almeida-Freire-Hizmeri stochastic dominance
Their SSD-violation strategy reports per-trade **net Sharpe 0.230-0.290** = **~4.1
annualised**. Red flags: unrefereed for 2.5 years; the physical density is estimated from
**the same intraday sample the strategy trades on**; and their own clean benchmark in the
same table correctly reproduces the null — a pipeline calibrated for the easy case
producing Sharpe-4 on the hard case is more consistent with leakage than a 10x edge.
**Decisive test on our SPXW intraday quotes: strict EXPANDING-WINDOW P-density (data
strictly prior to t) vs their in-sample version.** Informative either way. I'd bet against.

### One peer-reviewed paper that may unify everything
**Papagelis & Dotsis, Journal of Futures Markets (2025)**: VRP decomposed into overnight
vs intraday components — **significantly negative during the NON-TRADING overnight period,
positive and often insignificant INTRADAY**. VERIFY THE SIGN CONVENTION before relying on
it, but if it reads as expected it means **the entire harvestable premium sits in the
overnight window** — which would explain both why 0DTE (a pure intraday instrument) has no
carry AND the prior session's finding that only overnight drift works. See
[[index-daytrading-research]] for that overnight result.

### Correction to earlier citations in this file
- Andersen-Fusari-Todorov (JF 2017, JFE 2015): priced left-tail risk **cannot be spanned
  by market volatility**. **So conditioning a put-selling strategy on VIX is not
  conditioning on the thing that is actually priced.**
- "Fear Sells" by Beckmeyer/Branger/Gruenthaler **does not exist**. The real paper is
  Beckmeyer, Branger & **Gayda**, "Retail Traders Love 0DTE Options... But Should They?"
  (SSRN 4404704).
- Bollerslev-Todorov's 75% tail share is **method-dependent** — nonparametric EVT gives
  ~75%, but parametric SVCJ (Broadie-Chernov-Johannes) gives **24.4%** and Eraker 20.0%.
  Do not quote 75% as settled.

## 8j. CORRELATION PREMIUM — corrected, and it died at the short end

**CORRECTION to an earlier figure in this file.** I wrote that index implied correlation
was 46.7% vs realised 28.7% (an 18-point gap). **Wrong.** The authors' own published
figures: **S&P 500 implied 39.5% vs realised 32.5% — a 7-point gap**, not 18. (46.0% vs
35.5% is the DJ30 pair; the 28.7% could not be sourced anywhere.) The prize is less than
half what I quoted.

**DMV's own net-of-cost result, which I had not stated.** Their dispersion strategy:
gross monthly excess return 10.37%, CAPM alpha 10.59% (t=1.96), annualised Sharpe 0.73.
**Net of bid-ask: 5.3%, alpha t-stat falls to 0.77, Sharpe 0.41 — and the plain short
index straddle (0.52) and short index put (0.58) BOTH BEAT IT.** Their published abstract
says it outright: *"The correlation risk premium cannot be exploited with realistic
trading frictions."* Note the cost treatment is gentle (held to expiry, no roll).

**Original analysis on the authors' updated data** (OSF doi:10.17605/OSF.IO/CKGYF, 7,046
daily obs 1996-2023, now on disk). The published IC−RC gap is **contemporaneous, not
tradeable** — their RC is backward-looking. Re-aligned against FORWARD realised
correlation, non-overlapping monthly (n=334):

| period | 30-day premium | t | frac > 0 |
|---|---|---|---|
| DMV's own 1996-2003 | **+10.39 pts** | 8.58 (artifact) | 0.82 |
| 2010-2017 | +6.51 pts | 4.58 | 0.72 |
| **2018-2023 (true OOS)** | **−0.61 pts** | **−0.35** | 0.51 |
| 2021-2023 | −2.51 pts | −1.67 | 0.44 |

Ex-2022 it is +1.06 pts (t=0.53) — **compressed to statistical zero, not reliably
negative.** Positive median with a negative mean is the short-correlation signature:
wins small and often (51% of months post-2018 vs 82% in DMV's sample), loses huge and
rarely (2022: −10.11 pts).

**The one place it survives is the LONG end — opposite to where retail dispersion sits:**

| horizon | full sample | 2018-2022 |
|---|---|---|
| 30d | +4.20 pts | **−1.62 pts** |
| 91d | +9.03 pts | — |
| **365d** | **+10.90 pts** | **+4.52 pts** |

**A timing overlay on it has ZERO out-of-sample information.** Sorting on IC−RC gives a
beautifully monotonic full-sample result (Q5−Q1 = 10.53 pts, slope t=4.84) that collapses
to **Q5−Q1 = 1.45 pts, slope t = −0.00, R² = 0.000 in 2018-2023.** Exactly the
conditioned-subsample pattern this whole session has been about.

**Sector-ETF dispersion is genuinely untested — but the theory does not promise a free
lunch.** The harvestable quantity scales with (1 − rho-bar). Pairwise correlation among 11
sector ETFs is far HIGHER than among 100 single stocks (sectors share the market factor
almost entirely — that is what a sector IS), so cutting from ~100 legs to ~11 may shrink
the premium by MORE than it shrinks cost. And you would be harvesting something that has
been ~zero at 30 days since 2018. **Cutting costs on a zero edge yields zero.**

**Vol-of-vol, for completeness.** Baltussen, van Bekkum & van der Grient (JFQA 2018)
VOV signal is clean (VW 4-factor alpha −0.60%/mo, t=−2.62) but **has no transaction-cost
analysis anywhere in the paper**, runs ~68% monthly turnover per leg, is concentrated in
the short leg, and decays by 3x across subsamples (1996-2004 t=−2.57 -> 2005-2014
t=−1.54). Park (2015) VVIX results are on **daily-rebalanced deep-OTM delta-hedged
options at mid**, where real spreads are 5-15% of premium — the edge lives exactly where
costs are worst. **No peer-reviewed test of the VVIX/VIX ratio exists.**

## 8k. WHY MY VIX-TERM-STRUCTURE TEST MISSED JOHNSON'S SIGNAL

An agent audited my own code before recommending anything, and found the specific defect:

**My 1,001-cell null used `VIX/VIX3M` as a BINARY GATE on a FIXED SHORT-PREMIUM
structure. Johnson's SLOPE is PC2 (orthogonal to the level, which he shows carries no
information), CONTINUOUS, and SIGN-FLIPPING.** A signal that says "be long vega here,
short vega there" is **structurally invisible to a test that only ever holds short vega.**
That configuration is genuinely untested in my work.

Two candidates, both index-level (so the borrow-fee critique does NOT apply), both
predicting straddle/variance-swap returns rather than direction, both testable on data
already on disk:
- **Johnson, JFQA 2017** — VIX term-structure SLOPE = PC2 of a 6-point MFIV curve
- **Vasquez, JFQA 2017** — IV term-structure slope, cross-sectional straddle returns

**Honest prior on it: 20-25%** that it clears the t=3.72 bar with the correct sign.
Johnson has no published post-publication replication, and my own base rates argue
against it. **Worth one test because it is cheap, not because it is likely.**

### FEATURES ARE ALREADY BUILT
`scripts/build_iv_features.py` -> `data/opt_eod/SPY_ivfeatures.parquet`
**4,371 daily rows 2008-2025, zero NaNs**: `iv30`, `iv90`, `slope`, `gs_spread`,
`rr25`, `smirk`. The inputs are ready — the test is a short script away.

### DATA TRAP (new, and it would poison any surface build)
**7.8% of SPY chain rows carry a filler `implied_volatility = 0.01488`** on deep-ITM
contracts. Filter it before building any IV surface. (This is in addition to the corrupt
`mark` column and the 7.1% zero-bid rows already noted in 1b.)

### Value-weighted / liquidity-screened decay — original computation
Under `price>$5`, `ME>NYSE20`, VW deciles, **only SmileSlope and dCPVolSpread survive at
all**; everything else is a microcap artifact. **`OptionVolume1` goes NEGATIVE
value-weighted (t = −1.57).** Baseline to judge any candidate against: across all 210
replicated OSAP signals, **only 14.3% clear t>2 in 2015-2024**.

### Goyal & Saretto is probably a SPREAD ARTIFACT
Monthly Sharpe 0.718 (~2.49 annualised) — but **their own robustness section shows the
long-short straddle falls from 22.5% to 7.5%/month when effective spread equals quoted
spread**, and the effect is LARGER in high-spread stocks, which is the signature of an
artifact rather than an edge. Duarte-Jones-Wang (JF 2024) is the formal version. OSAP's
cousin `RIVolSpread` is dead (2015-24 VW t = −0.37). Any index-level test of it should be
**pre-registered as an expected null** — SPY ATM spreads are 0.46-0.81% today vs the
20-40% that generates the published number.

### Also: there is NO peer-reviewed 0DTE literature at all
Crossref returns only SSRN preprints with 1-7 citations, several of which are vendor
backtest compilations. Recent arXiv q-fin (q-fin.PR, q-fin.TR) is a dead end for this.

## 8l. EARNINGS-DATE GAP CLOSED — the full DoltHub stack

Same publisher, same `act_symbol` key as the options DB, so it joins with **no symbology
work**. Licence **CC BY-SA 4.0**. All free.

**`post-no-preference/earnings`** (1.7 GB, cloned and verified locally):
- **`earnings_calendar`** — 117,593 events, 7,370 symbols, 2020-01-22 -> **2026-09-11
  (forward-looking)**. The `when` field (Before market open / After market close) is
  populated ~75%. **This matters: for an AMC announcement the D-1 -> D window is a
  different calendar window than for BMO, and getting it backwards INVERTS the trade.**
- **`eps_history`** — 166,307 rows, reported vs estimate (142,812 with both) = realized
  earnings surprise, 2016-07 -> 2026-06.
- **`eps_estimate`** — **7.0M rows of POINT-IN-TIME daily consensus** with count/high/low
  (analyst dispersion), 2017-10 -> 2026-08. Point-in-time means no lookahead, and
  dispersion is a known conditioning variable for straddle returns.

**`post-no-preference/options`**: **114,451,312 rows**, 66 GB logical.
**`post-no-preference/stocks`**: ohlcv, splits, dividends.

### ON DISK NOW (moved off the session scratchpad, which gets reaped)
**`data/dolt/`** — 14 GB, verified queryable from that path:
`options` 7.9GB (**114,562,042 rows**) · `stocks` 4.4GB · `earnings` 1.7GB (117,593 events).
Run `dolt sql` from `data/dolt/` and all three mount as databases, so
`options.option_chain JOIN earnings.earnings_calendar` works directly.
Helper scripts kept alongside: `coverage.py`, `expcheck.py`, `straddle_extract.sql`.
**Clones are NOT resumable** — a killed clone restarts from scratch.

### CORRECTION: the data is NOT daily, and this materially bounds the test
Snapshot days per year: **2019: 48 · 2020: 155 · 2021: 156 · 2022: 151 · 2023: 155 ·
2024: 183 · 2025: 259**. So 2020-2023 is roughly **three snapshots a week, not daily**.
Daily cadence only arrives in 2025. IV present on 100% of rows; **~85% carry a genuine
two-sided market**.

**What that does to the pre-earnings straddle test** (earnings calendar joined against
the actual snapshot index, 117,593 events -> **23,115 usable D-1/D pairs**):

| period | true D-1 share | verdict |
|---|---|---|
| **2020-2023** | **0.5%** (73% are 2 days back) | NOT the paper's estimand |
| **2024-2026** | **78.9%** | the real test, **~12,900 clean pairs** |

**Run the test on 2024-2026. Report 2020-2023 SEPARATELY as a wider-pre-announcement-window
variant — do NOT pool them.** They are different estimands.

**The expirations ROLL between snapshots** (NVDA 2025-08-25: Sep5/Sep19/Oct17; two days
later: Sep12/Sep26/Oct17). You must trade an expiry present on BOTH dates. Measured across
12,930 usable 2024-2026 pairs: **99.6% do have a common post-event expiry**, so it costs
almost no sample — but it pushes you long-dated. DTE of the nearest common post-event
expiry: 0-6d **6.6%** · 7-13d 19.8% · **14-20d 38.4%** · 21-27d 23.8% · 28+d 11.4%.
**Median ~2-3 weeks; only 29% offer a <=14-day expiry.** Expect a DAMPED version of the
published +2.3% — the pre-announcement vega run-up is diluted at 3 weeks' maturity.

**Pipeline validated end-to-end on one real event**: NVDA 2025-08-27 AMC, Oct-17 expiry,
180 strike, delta-neutral straddle 24.41 -> 24.06 = **−1.42%**, IV essentially flat
(0.4102 -> 0.4108). One event proves nothing directionally, but it confirms the join, ATM
selection, delta weights and bid/ask all work.

Strike grid is ~27 strikes at +/-30% of spot, ~1% spacing near the money — **ATM is well
covered but there are NO WINGS.**

### Two design constraints, verified not assumed
1. **Exactly 3 expirations per symbol per day, and they are NOT weeklies.** Verified on
   AAPL 2026-08-05: expiries 08-19, 09-04, 09-18, ~27 strikes each spanning +/-30% of spot
   at ~7-point spacing (ATM well covered). **Consequence: the nearest post-earnings expiry
   is often 2-4 weeks out rather than the front weekly**, so you hold a longer-dated
   straddle — dampening both the vega run-up and the theta bleed. The Gao/Xing/Zhang
   effect should still be measurable but **will not map 1:1 to +2.3%**.
2. **No open-interest and no volume columns**, and no underlying price in the chain table.
   Liquidity screening must come from the bid-ask spread itself plus `stocks.ohlcv` volume
   on the underlying — weaker than an OI filter; some illiquid names will get through.

### Reproducible pull
```
brew install dolt
dolt clone post-no-preference/options    # 114M rows, ~1hr
dolt clone post-no-preference/earnings
dolt clone post-no-preference/stocks
cd options && dolt pull                  # refresh
```
The hosted API is fine for single symbol-days but **throttles on range scans — useless
for bulk**. Run the study against the local clone.

**Do NOT run the earnings x chain join as a single pass over 114M rows.** Drive it from a
loop over the earnings calendar, pulling one symbol/date-window slice at a time. Starter
SQL (cadence check, two-sided-quote quality check, straddle join) is in the scratchpad at
`straddle_extract.sql`.

## 9. Open threads

- 9 research agents still running: condors/butterflies, exotic structures (ZEBRA, jade
  lizard, twisted sister, broken-wing, christmas tree, gamma scalping, box spread),
  options expression / break-even table, blowup episodes, management rules, real-chain
  repos, plus dedicated **academic-paper sweep** and **GitHub sweep**.
- Reports already on disk: `RESEARCH_SWING_REPOS.md`, `RESEARCH_SWING_ACADEMIC.md`,
  `RESEARCH_COSTS.md`, `RESEARCH_FEES.md`, `RESEARCH_RUIN_SIZING.md`,
  `RESEARCH_STRADDLE_STRANGLE.md`, plus `FINDINGS.md` / `RESEARCH_DIRECTION.md` /
  `RESEARCH_0DTE_EDGE.md` / `RULES.md` from the prior session.
- **Untested and most promising**: (a) pre-earnings long straddle on single names
  (Gao/Xing/Zhang) — needs single-stock chains; (b) option-implied cross-sectional
  predictors (IV spread, skew, O/S ratio) — the family that predicts what options
  actually price rather than mere direction; (c) sector-ETF reversal conditioned on
  high VIX (Nagel) — data already on disk, opposite sign to the falsified rotation.
- `data/stocks/panel.parquet` needs a re-fetch (74 of 190 tickers landed).
