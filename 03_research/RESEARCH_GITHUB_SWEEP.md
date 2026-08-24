# Public GitHub Sweep: Options & Volatility Strategies with Verifiable Edges

Sweep date: 2026-08-06/07. Companion to `RESEARCH_REALCHAIN_REPOS.md`, `RESEARCH_SWING_REPOS.md`, `FINDINGS.md`.

Method: GitHub repo-search API for breadth (~40 themed queries), then **reading the actual
source and the committed result tables** for every repo claimed on. README performance numbers
are treated as marketing until the code says otherwise. Where a claim could not be verified
without downloading gigabytes of LFS data, that is stated with the exact command to check.

Calibration used throughout: your real-SPY-quote result that every premium structure is negative
expectancy (iron condor 16Δ/5-wide: 63.6% win, −10.5%/trade, t=−13.5; put credit 16Δ/5: 75.7%
win, −12.8%/trade), and that 1,001 regime-gated cells including GEX and DIX produced zero cells
positive in all three subperiods.

---

## 0. Headline — four things

1. **A real academic's replication package independently reproduces your null on different
   data.** `vilkovgr/0dte-strategies` (Grigory Vilkov, Frankfurt School, SSRN 4641356), built on
   **real Cboe 30-min SPXW NBBO bars 2016-09 → 2026-01**, reports iron butterfly/condor at
   **SR −0.96** and strangle/straddle at **SR −0.51** net. Two researchers, two instruments, two
   datasets, same answer. **The condor question is closed.** §1
2. **The single-stock chain gap is closed, free, today.** The DoltHub `dolthub/options` public
   database serves dated single-stock chains with **real bid AND ask, IV, and full greeks**, over
   a broad US universe, ~2020-02 → 2024-11, via keyless SQL-over-HTTP. **I verified it live** —
   AAPL, NVDA, TSLA, MSFT, SPY all return real quotes. §5.1
3. **Your GEX/DIX null is now triple-confirmed**, including by a 15-year SqueezeMetrics
   regression (DIX insignificant at *every* horizon) and by a 952-day ThetaData 0DTE study that
   killed itself. §4.1
4. **Every profitable options result in this sweep traces to a specific broken line**, and I can
   name them. The most spectacular: a repo claiming $25k → $5.1M marks spreads with a function
   that takes **no time-to-expiry argument**, so every trade books ~100% profit at the instant it
   opens. §6.1

---

## 1. TIER A — `vilkovgr/0dte-strategies`

- URL: https://github.com/vilkovgr/0dte-strategies · 46★ · created 2026-04-09, last push **2026-06-16** · MIT
- Author: **Grigory Vilkov**, Frankfurt School — a real, heavily-cited options academic.
- Paper: *"0DTE Trading Rules: Tail Risk, Implementation, and Tactical Timing"*, https://ssrn.com/abstract=4641356

### 1.1 Data — real quotes, overlapping what you already own

From `docs/agent-context/method.md`: **Cboe 30-minute SPXW option bars with NBBO quotes**, sizes,
OHLC, volume, underlying; ThetaData 1-min SPX/VIX for realized moments. SPXW only (European,
cash-settled 16:00 ET — no early-exercise contamination). Sept 2016 – Jan 2026.

Pipeline: filter same-day-expiry SPXW at each 30-min bar → moneyness = K/S → keep K/S ∈
[0.98, 1.02] → scale mid and spread by spot → **Akima 1-D interpolation onto a moneyness grid of
step 0.001** → split calls/puts → payoff, intrinsic, time value, PNL.

Raw Cboe bars are not redistributed, but the **derived panels ship via Git LFS (~400 MB)**:
`data_opt.parquet` (~3.5M rows: mid, **spread `bas`**, greeks, payoff, PNL), `data_structures.parquet`
(~700K strategy-level rows), `vix.parquet`, `slopes.parquet` (PIT surface slopes),
`future_moments_{SPX,VIX}.parquet`, `ALL_eod.csv`.

Your own real SPXW intraday 2016-2024 covers the same instrument and overlapping period, so you
can cross-validate his panel against your raw chains — which is exactly how you check §1.3.

### 1.2 The unconditional result — it replicates your null

`tests/reference/tables/0dte_implementable_pnl.tex`, committed ground truth. Entry 10:00 ET,
one trade/day, hold to 16:00 settlement, 953 days. Units: % of underlying.

| Structure | Mean Mid | Mean net | SR mid | **SR net** | ES₁% | Obs |
|---|---|---|---|---|---|---|
| Iron Butterfly/Condor | −0.0073 | −0.0125 | −0.56 | **−0.96** | 0.579 | 953 |
| Strangle/Straddle | −0.0059 | −0.0110 | −0.27 | **−0.51** | 1.423 | 953 |
| Call Ratio Spread | −0.0140 | −0.0194 | −0.55 | **−0.76** | 1.209 | 953 |
| Bull Call Spread | −0.0101 | −0.0154 | −0.35 | **−0.53** | 0.904 | 953 |
| Bear Put Spread | +0.0138 | +0.0085 | 0.48 | +0.30 | 0.827 | 952 |
| Risk Reversal | +0.0157 | +0.0106 | 0.65 | +0.44 | 1.601 | 953 |
| **Put Ratio Spread** | +0.0251 | **+0.0198** | 1.06 | **+0.84** | 0.710 | 952 |

The paper's own summary: *"Median VRP from 10:00 ET to expiration ≈ 0.0011% of underlying — too
small to trade after realistic friction"*, and *"0DTE is a tightly risk-budgeted tactical
overlay, not a standing carry strategy."*

An academic who wanted to find an edge, on real SPXW quotes, found short premium negative.
**Stop re-testing unconditional condors.**

### 1.3 ⚠️ THE DEFECT — modelled half-spread looks 1–2 orders of magnitude too small

`code/analysis/compute_implementable_pnl.py` builds three execution tiers:

```python
strats["pnl_mid"]      = strats["reth_und"].astype(float)
strats["pnl_ba"]       = strats["pnl_mid"] - strats["half_spread_cost"]
strats["pnl_ba_fee05"] = strats["pnl_ba"] - 0.005   # "0.5bp in percent units (1bp = 0.01)"
```
```python
def calc_half_spread(row):
    total = sum(abs(qty) * bas_lookup[(date, time, otype, m_int)] for otype, m_int, qty in legs)
    return 0.5 * total
```

The *structure* is right — per-leg real NBBO spread weighted by |qty|, so a ratio spread with two
short legs pays two half-spreads. The *magnitude* is not:

| Strategy | Mean Mid | Mean B/A | half-spread | Turnover | cost/turnover |
|---|---|---|---|---|---|
| Iron Butterfly/Condor | −0.0073 | −0.0075 | 0.0002 | 0.310 | **0.065%** |
| Put Ratio Spread | 0.0251 | 0.0248 | 0.0003 | 0.574 | **0.05%** |
| Bull Call Spread | −0.0101 | −0.0104 | 0.0003 | 0.791 | **0.04%** |

A four-leg 0DTE SPX iron condor should lose ~**3–6% of gross premium** to half the NBBO spread.
The table implies 0.065% — **~50–100× too small**. Cross-check: SPXW ATM 0DTE at 10:00 ET is
worth ~$20–30 with a ~$0.20–0.40 NBBO spread; on spot 6000 that is ~0.005% of underlying per leg,
so four legs at half-spread ≈ 0.01% — versus the 0.0002 implied.

**Likely cause: a unit mismatch.** `method.md` says mid prices and spreads are *"scaled by spot"*
(so `bas` is a **fraction**), while the hard-coded `0.005` is commented as *"percent units
(1bp = 0.01)"*. Both cannot be true. The tell: the flat fee is currently doing **~25× more cost
work than the entire modelled bid/ask**.

**This matters because the surviving edge is the same size as the total cost charge.** Put ratio
spread: +0.0251 mid → +0.0198 net; the whole charge is 0.0053. If the true half-spread is ~50×
larger (≈0.015), the put ratio spread goes **negative**.

**Cheap verification, using data you already own:**
1. Pull `data_opt.parquet` (LFS); compute `median(bas / mid)` for the ATM 0DTE option at
   `quote_time == "10:00:00"`.
2. Compute the same ratio from your own raw SPXW chains at 10:00 ET.
3. Truth should be ~1–3%. If his panel gives ~0.02–0.05%, the unit bug is confirmed and **every
   "net" column in the paper is wrong**, including SR 0.93.

Until then: treat Vilkov's **mid** columns as sound and his **net** columns as unproven.

### 1.4 What is genuinely right (rare, worth copying)

`code/analysis/compute_conditional_oos_protocol.py`, read line by line:

- **Lines 284–304 — strict one-step-ahead walk-forward.** `X_train = X[start:i]`,
  `X_test = X[i:i+1]`. Expanding or rolling 252d. OOS starts April 2019 after 252-day burn-in.
- **Lines 299–301 — standardization fit on training window ONLY:**
  ```python
  scaler = StandardScaler()
  X_train_sc = scaler.fit_transform(X_train)
  X_test_sc  = scaler.transform(X_test)      # transform, not fit_transform
  ```
- **Line 238:** `spx10[col] = spx10[col].shift(1)` — realized features lagged.
- **Lines 443–445:** `pnl_l1 = pnl_net.shift(1)`; rolling 5d mean/std on the *already-shifted*
  series.
- **`moneyness_selection.py` — strikes are NOT performance-selected.** The representative config
  is chosen by *data availability* (most days, then most rows, then smallest deviation, then
  lexicographic). This is where most authors quietly cherry-pick strikes; he does not.
- Date-clustered SEs + Benjamini–Hochberg (`compute_clustered_inference_mht.py`), an explicit
  structural-break test, and tail risk as ES₁%/maxDD/worst-day — not just Sharpe.

### 1.5 The remaining caveats, in severity order

1. **The edge is decaying hard.** `0dte_structbreak_post2022.tex`: put ratio spread mean falls
   from **0.0381 pre-2022 to 0.0055 post-2022** — an 85% decay. t(Δ)=−1.22, p=0.222 — but *no*
   strategy shows a significant break (all p ≥ 0.22), so the test simply has no power. The thing
   you'd want to trade has largely stopped working in the half of the sample resembling today.
2. **Protocol is selected on realized OOS performance.**
   `compute_conditional_oos_investment_ts.py:222–247` sorts by `sr_net`/`mean_net_bp` and takes
   `.head(1)` per strategy. What that hides, from `0dte_conditional_oos.tex` — Risk Reversal:
   **Expanding SR net −0.11, Rolling SR net +0.34.** Same strategy, same features, sign flip on
   an arbitrary window choice.
3. **The Top-3 basket (SR net 0.82) is hindsight-selected** — `select_top_strategies` ranks all 7
   by full-OOS mean/SR and keeps 3. The honest number is the all-strategies basket:
   **SR net 0.25, mean net 0.22 bps.**
4. **The model zoo is a large multiple-testing surface.** `compute_conditional_model_zoo.py` is
   91 KB and `tests/reference/tables/` holds **40+ model-zoo tables** (Ridge/ElasticNet/RF/LGBM/
   XGB/CatBoost/NN × binary/return × hard/soft × expanding/rolling). "Ridge-logit SR slightly
   above 1.0" is the max of that search. BH is applied to the *moment regressions*, **not** to the
   OOS Sharpes. Apply your own DSR.
5. Half-spread assumes fills *at the touch* — optimistic for 4-leg 0DTE even before §1.3.
6. Only 953–1,061 daily observations; one entry per day at 10:00 ET.

---

## 2. SIGNALS WORTH BACKTESTING

Ranked, each specified precisely enough to code directly.

### S1. Put ratio spread, SPXW 0DTE — run it as a COST-MODEL FALSIFICATION, not as a strategy
The highest-value item in this report: a falsification test against data you already own.

- **Instrument:** SPXW, same-day expiry, European, cash-settled 16:00 ET.
- **Entry:** 10:00 ET, one trade per day.
- **Structure:** long 1 put nearer ATM, short 2 puts further OTM; legs on the moneyness grid
  K/S ∈ [0.98, 1.02] step 0.001. Choose the representative config **by data availability**
  (most days present), never by performance.
- **Exit:** hold to 16:00 settlement. No intraday stop.
- **PNL units: percent of underlying notional — NOT percent of premium.** This is the detail that
  matters most. A ratio spread has an uncovered short leg; normalizing per unit of spot notional
  is what sidesteps the naked-short-leg denominator trap that manufactured +800%/yr in your code.
- **Costs:** charge the **FULL** per-leg NBBO spread from your own chains (not half), weighted by
  |qty| so both short legs are charged, plus real SPX commissions (~$0.65/contract × 3 legs × 2 sides).
- **Prediction to falsify:** Vilkov reports +0.0198% of underlying, SR 0.84 net. **My prediction
  is this goes to zero or negative on honest full-spread fills.** If it survives, it is the first
  premium structure that has and deserves real work. If it doesn't, you have closed the 0DTE
  structure question permanently — with an academic's own dataset as the counterweight.
- Run pre-2022 and post-2022 separately; expect the post-2022 half much weaker (§1.5.1).

### S2. Realized/implied SKEW as the conditioning variable — your 1,001 dead cells used the wrong axis
The most robust finding in the best study in the space, surviving clustered SEs **and** BH
correction (`0dte_inference_cluster_mht.tex`):

- Realized **skewness** dominates realized **variance** in explaining 0DTE structure PNL;
  RS explains **20–40%** of PNL variation for directional spreads and risk reversals.
- t-stats on RV+RS and IV+IS+RV+RS specs: Bull Call **t=8.64**, Bear Put **t=−8.74**,
  Put Ratio **t=−6.27**, Risk Reversal **t=7.30** (all q < 0.001, BH-corrected).
- Adding implied vol and implied skew adds 2–7 pp of R² beyond RV alone.

These are *contemporaneous explanatory* regressions — not a trade by themselves. But they say the
state variable driving 0DTE PNL is **skew, not vol**. Every gate you have tested — GEX, DIX, VIX
regime — is a vol/positioning proxy. **You have 1,001 dead cells built on the wrong state
variable.** Build the forward-looking version: does implied skew, or the implied-minus-realized
*skew* premium at 10:00 ET, predict the sign of the day's structure PNL? Untested axis in your
work, and the one the data says matters.

Corroborating evidence from an independent direction (§4.4): a VRP gate built on *trailing*
realized vol fires on 87.3% of days with only 16 transitions in 3.5 years — too slow to be a
timing signal at all. Fast, forward-looking surface variables (slope, skew) beat slow reactive
ones structurally, not just empirically.

### S3. Continuous term-structure sizing instead of a threshold
From `jironghuang/volatility_risk_premium` — the mechanism, not the repo:
```
signal   = 1 − VIX/VIX3M
position = clip(signal / j, −1, +1),   j ≈ 0.10–0.25
position = position.shift(1)           # already correct in the source
position > 0 → long SVXY at that fraction;  position < 0 → long VXX at |that|
```
Size is *continuous in the slope*, so as the curve flattens toward inversion, exposure shrinks to
zero automatically. **There is no threshold to grid-search — the sizing is the risk control.**
Its data file contains a genuine Feb 2018 (SVXY 287.28 → 48.96, −83%), so it can be tested against
the event that kills short-vol. Caveats: zero transaction costs in the original, an undocumented
asymmetric 0.5× leverage on VXX vs 1.0× on SVXY, and the "walk-forward optimized" params are a
hardcoded default argument. Re-derive costs and params yourself; take only the sizing idea.

### S4. Binary direction target ≫ return-magnitude target
Methodological import, cheap to re-run on your existing panels. Predicting `1 if net PNL > 0
else 0` with a logit substantially beats predicting PNL magnitude with a regressor, and *hard*
mapping (`w = sign(p̂−0.5) ∈ {−1,+1}`) ≥ *soft* (`w = 2p̂−1`) for most model families.
Features: 10:00 ET implied state (IV, IS, slope_up, slope_dn) + lagged realized (RV, RS, return)
+ lagged strategy PNL.

### S5. Conditional VRP entry architecture (template, not a result)
From `pi-mis/spx-vol-backtest` — the cleanest look-ahead-free conditional-entry code found:
```
spread   = NS/ARIMA-forecast VIX(30d) − spot VIX
contango = VIX < VIX3M
eVRP     = VIX − 10d trailing realized vol of SPY × √252 × 100

spread < −2.0 AND contango     AND eVRP > 0 → LONG SVXY, size = VIX/100
spread < −2.0 AND backwardation AND eVRP > 0 → LONG SVXY, size = 0.5 × VIX/100
spread > +2.0 AND backwardation AND eVRP ≤ 0 → LONG VXX,  size = VIX/100
else FLAT
```
Daily rebalance with a **2% no-trade band**. Forecast: Nelson-Siegel on {VIX9D, VIX, VIX3M, VIX6M}
at fixed λ → rolling ARIMA on β₁,β₂,β₃ (120d, refit/5d, AIC-selected). Verified clean:
`arima_forecaster.py:109-111` trains on `betas.iloc[i-w:i]` strictly; `backtest.py:41-42` does
`held_pos = effective_pos.shift(1)`; costs 5bps/unit turnover. **But it commits no results,
`BACKTEST_START="2019-01-01"` deliberately excludes Feb 2018, and it has no train/test split with
≥5 free parameters.** Take the architecture, supply your own discipline.

---

## 3. ENGINES / TOOLS WORTH REUSING

1. **`YichengYang-Ethan/0dte-strategy` → `src/pipeline/leak_safe.py`** (439 LOC) — **the single
   best thing to steal in this whole sweep.** `future_poison_test()` (`:299-363`) copies a day's
   data, **randomizes every post-cutoff row**, re-runs the computation and asserts the output is
   bit-identical. Used by 5 validation scripts with no false positives. `rolling_zscore_shifted()`
   (`:186-198`) shifts *both* the rolling mean and std. This is a stronger look-ahead detector
   than anything in your stack and would have caught the entry-price bug in half the repos below
   in one run.
2. **`vilkovgr/0dte-strategies` walk-forward + inference harness** — §1.4. Correct scaler
   discipline, clustered SEs, BH correction, structural-break test. ~550 lines, MIT.
3. **`oimosanAI/strategy-lab` → `core/backtest/` + `core/evaluation/`** — `EXECUTION_LAG = 1`
   enforced at exactly one site (`engine.py:44,289`); `assert_causal()` (`:51-104`) is
   property-based (random cut, perturb everything after, assert prior signals identical);
   `assert_backtest_causal()` also compares **pre-lag** fields, because a 1-bar peek would
   otherwise be absorbed by the lag and pass silently; and the guards have **planted-bug negative
   controls** (`tests/core/test_backtest_engine.py:170-209`). `portfolio.py:39-82` decomposes each
   day into carried / newly-entered / **exited** legs — the term everyone forgets.
   **Equities/ETFs only — no options, no strikes, no greeks, no expiry roll.** No DSR, no White
   Reality Check, no PBO. And note its own worst flaw: every published report contains
   `assert_backtest_causal PASSED` as a **hardcoded string literal** (`generate_reports.py:110-116`)
   — the script never calls the function.
4. **`lambdaclass/options_portfolio_backtester`** (already on disk) — still your best *fill*
   engine, with the caveats already in `RESEARCH_REALCHAIN_REPOS.md`: `iron_condor()` silently
   ignores `short_delta_call`/`short_delta_put`/`wing_width`, and there is **no options margin
   model at all**. Use its fill logic; never its multi-leg presets.

No other engine cleared the bar. The GitHub options-backtester space is otherwise 50–200 line
scripts on yfinance snapshots.

---

## 4. NULLS THAT SAVE YOU WORK (independent confirmations)

### 4.1 GEX and DIX do not predict forward SPX returns — 15 years, proper HAC
`marcusdrewry/gex-forward-returns`, from committed `data/regression_results.csv` (not the README):

| Horizon | Univariate GEX_z | + confounders |
|---|---|---|
| 1d | β=−0.00024, t=**−1.17** | t=+0.70 |
| 5d | β=−0.00117, t=**−1.55** | t=+0.22 |
| 21d | β=−0.00406, t=**−2.05**, R²=0.9% | β=+0.00245, t=**+1.09** |

The only significant univariate effect **flips sign** once log VIX / realized vol / momentum /
trend / DIX are added. **DIX is insignificant at every horizon** (t = 0.43, 0.19, 0.41).
Subperiods unstable: t=−2.07 (2011-18) vs t=−1.14 (2019-26). GEX predicts *vol* (t=−4.25), but
that dies under VIX too (t=−1.21). Newey-West lags `int(1.5*h)+1` — correct HAC practice.
Two flaws that don't change the conclusion: `scripts/analysis.py:72-73` `zscore_full()`
standardizes on the full sample (harmless for t-stats, but makes βs non-tradeable units), and
there is an unflagged publication-lag leak — SqueezeMetrics publishes date *t* after the close of
*t*, but `fwd_h` is measured from `price(t)` (`:51`).

### 4.2 A 952-day real-quote 0DTE GEX study killed itself
`YichengYang-Ethan/0dte-strategy` tested "dealer 0DTE gamma hedging causes intraday drift toward
GEX walls." Data: **Theta Data Pro, 952 days SPXW 0DTE, 2022-07-01 → 2026-04-16, minute-resolution
quote/trade/greeks/OI, 468,887 parquet files, 16 GB.** Results, from `docs/R0_RIP_2026_04_21.md`:
wall-targets beat spot-as-target on MAE by **−15 to −44% (worse)**; a 24-cell parameter grid
passed **0 of 24**; momentum-vs-pin was 49/49 random walk. The prior 1DTE version showed PF
1.23–1.77 OOS but a 2023 holdout gave 0.75–0.91, and attribution found the edge was **prior-day
SPY drop (mean reversion), not the GEX mechanism**. Its fill simulator documents **57% spread cost
on 0DTE**. Archived the same day it failed.

### 4.3 Single-stock VRP — academic evidence for your "index-only" calibration
`hkalager/optionm` (7★, WRDS OptionMetrics + CRSP, 2001–2020, top-100 by market cap re-selected
per year so survivorship is handled correctly). README opens: *"This is an exploratory study with
no profitable strategy in sight."* Accurate. **Not tradeable** — it uses the OptionMetrics
`stdopd` Standardized Options file, i.e. model-interpolated constant-maturity ATM-forward
**synthetic** options with no strike, no bid/ask, no OI, and a surface-derived theoretical
premium. Zero spread by construction, and American exercise unmodelled. Use as citation.

### 4.4 A trailing-RV VRP gate is structurally too slow to be a timing signal
`oimosanAI/strategy-lab`'s vol sleeve: `VRP = VIX/100 − rolling_std(SPY.pct_change(),21)·√252`,
long SVXY when VRP > 0. Real ETF, real costs (0.5bp commission + 5bp slippage), 2023-01 → 2026-07.
Result: **ann. return −0.26%, Sharpe 0.06, maxDD −14.2%, permutation p=0.46**, bootstrap CI
straddles zero. The decomposition is the valuable part: **buy-and-hold SVXY returned +13.5% OOS
vs −0.41% for the timed strategy — the VRP timing signal destroyed value**, because `VRP > 0` on
**87.3% of days with only 16 off→on transitions in 3.5 years**. Trailing RV only rises *after* a
spike, so there is structurally no chance to de-risk. To their credit they refuse to promote the
best grid point to default. (Caveat: Feb 2018 and Mar 2020 are both outside their sample — they
disclose this twice.)

---

## 5. DATA SOURCES

### 5.1 ⭐ `dolthub/options` — closes the single-stock gap, free, verified live

**This is the most actionable finding in the report after §1.** Found via
`quanttqueensu/earnings_iv_crush/earnings_iv_crush/data/dolthub_options.py`, then **verified
directly by me against the live API**.

- **Endpoint:** `https://www.dolthub.com/api/v1alpha1/dolthub/options/master` — SQL over HTTP,
  **no API key, public database, no multi-GB clone required.**
- **Table `option_chain`**, columns: `date, act_symbol, expiration, strike, call_put,
  **bid**, **ask**, vol (IV), delta, gamma, theta, vega, rho`.
- **Real bid AND ask, publisher-computed IV and full greeks.** Live sample I pulled
  (2023-06-02 AAPL 2023-06-16 expiry):
  `{'strike':'125.00','call_put':'Call','bid':'55.95','ask':'56.60','vol':'0.8115','delta':'0.9922', ...}`
- **Universe: broad US single stocks.** I confirmed **AAPL, NVDA, TSLA, MSFT, AMZN, GOOGL, SPY**
  all return real quotes on 2024-06-03. A single truncated `DISTINCT` query returned 603 symbols
  before hitting the server time budget — and only reached the letter G alphabetically — so the
  true universe is in the thousands, not hundreds.
- **Coverage [measured by probing]:** DATA on 2020-02-03, 2020-04-01, 2020-05-01, 2020-06-01,
  2023-06-02, 2024-06-03, 2024-10-01, 2024-11-01. EMPTY on 2019-06-03, 2019-11-01, 2020-01-02,
  2024-09-03, 2024-12-02, 2025-01-02, 2026-08-05. So: **roughly 2020-02 → 2024-11, with gaps**
  (2024-09-03 empty while 2024-10-01 has data). Verify per-date before relying on continuity.
- **Known limitation: no `open_interest` column.** Any OI-dependent feature needs another source.
- **Query discipline (important):** the `option_chain` primary key is **date-led**, so every query
  must pin an exact `date`. An unbounded `WHERE act_symbol = ...` scan times out server-side by
  design — I hit `context deadline exceeded` repeatedly on aggregates. Pin the date, bound the
  expiry range, and bound strikes to a band around spot. Retry `deadline exceeded` with backoff;
  treat any other rejection as permanent.
- **Ready-made client:** `earnings_iv_crush/data/dolthub_options.py` is a clean, documented,
  injection-safe (`_SYMBOL_RE`) adapter with retry/backoff and weekend/holiday step-back. Copy it.

Gaps this leaves: no OI, ends ~late 2024, EOD only. But it is **real single-stock bid/ask with
greeks, free, today** — exactly the gap you named as your biggest.

### 5.2 `vilkovgr/0dte-strategies` derived panels (~400 MB, Git LFS, MIT)
Interpolated SPXW 0DTE 2016-09 → 2026-01, 30-min bars, **with per-option bid/ask spread (`bas`)**,
greeks, payoff, PNL, plus PIT vol-surface slopes and forward realized moments.
`git clone https://github.com/vilkovgr/0dte-strategies.git` (LFS pulls automatically).
Caveats: moneyness restricted to K/S ∈ [0.98, 1.02] — near-ATM only, **no wings**; and verify the
`bas` units per §1.3 before trusting anything derived from it.

### 5.3 `marcusdrewry/gex-forward-returns/data/squeezemetrics_dix_gex.csv` — 15y DIX/GEX
Columns `date,price,dix,gex`; **3,796 rows, 2011-05-02 → 2026-06-04**, pulled 2026-06-05.
`gex` in raw dollars (−$7.5bn to +$24.2bn), 346 negative-gamma days (9.1%). `data/merged.csv`
(1.2 MB) ships it pre-joined with `^VIX`. SqueezeMetrics withdrew free distribution, so a
committed copy has scarcity value — **grab it before the repo disappears**, and remember the
~1-day publication lag when aligning. Given §4.1 this is a reference series to validate your own
DIX ingestion against, not a signal source.

### 5.4 Other real-data leads (lower priority)
- **`emlama/gex-backtesting` dataset** — not in the repo (304 KB tree). `download_data.sh:14`
  points at a bare IP, `http://45.55.51.49/data/gex-spx-0dte-trades.tar.gz`, **verified live:
  HTTP 200, 2.47 GB, Last-Modified 2026-03-03**. Claimed contents: 513 days SPX 0DTE
  2024-01-02 → 2026-02-19 from Polygon flat files, 400–900k trades/day, with `bid`, `ask` and
  quote-matched `side` per trade. Repo description says 305 days, README says 513 — unreconciled.
  **Unauthenticated IP, unverified provenance — sandbox it if you fetch it.** The analysis built
  on it is broken (§6.3), but the raw trade data may be sound.
- **`lucasbertovic/Volatility-Risk-Premium`** — ~165 MB committed CSVs, Polygon.io, **200 most
  liquid US stocks, ATM calls, 2022-11-04 → 2024-11-02**. Only the option **close/last-trade**
  price, **no bid/ask** — so usable for IV/RV work, not for fills. Extends past DoltHub's end date.
- **`peterchettiar/trading-volatility`** — the committed VIX futures CSV is the one asset worth
  taking from that repo (yfinance cannot serve it).
- **Vendor paths in Vilkov's `code/ingest/`**: working clients for **ThetaData** (known to you)
  and **Massive** (`massive.com`) — the latter less well known, ships a full SPXW downloader, and
  was chosen over CBOE DataShop for a published paper. Worth a pricing enquiry.

---

## 6. BROKEN — named, with the specific defect

### 6.1 `iulianallroad-glitch/gamma` ⚠️ DANGEROUS — live Tradier keys on a fabricated backtest
10★, last push 2026-01-10. Claims **$25,000 → $5,119,202, +20,376%, CAGR 148%, 3,789 trades,
61.4% win, PF 4.42, max drawdown $2,449** on 0DTE SPX credit spreads and iron condors — precisely
the family you measured at −10.5%/trade. Wired to **live Tradier keys** (`config.py:11-12`,
`LIVE_ACCOUNT_ID`) with Discord alerting. Someone may be trading this.

- **There is no GEX in the GEX strategy.** `backtest.py:717-719`: `pin_price = round_to_25(prev_close)`,
  with `round_to_25()` at `:121` = `round(price/25)*25`. The entire "gamma exposure pin" signal is
  **yesterday's SPX close rounded to the nearest 25 points.** No chain, no OI, no gamma, ever.
- **The decisive bug: the exit valuation has no time dimension.**
  `estimate_spread_value_at_price(setup, spx_price, entry_credit)` (`:284-335`) takes **no
  time-to-expiry and no volatility argument**. For an OTM short call spread:
  ```python
  dist_otm = short_strike - spx_price
  return max(0, entry_credit * (1 - dist_otm / 15))     # backtest.py:320
  ```
  Strike placement guarantees `dist_otm ≥ 8`, usually ≥ 15 (`core/gex_strategy.py:141-143`).
  So at entry, with 6+ hours to expiry, the spread marks at **zero**, and `simulate_trade_outcome`
  computes `profit_pct = (entry_credit − value)/entry_credit = 100%` (`:403-431`). Iron condors
  mark at ~70% profit instantly via the `/20` variant at `:307`. **The "edge" is an entry-time
  markup.** It is also why max drawdown is $2,449 against $5.1M terminal equity — an impossible
  number that should have ended the investigation by itself.
- Entry credit is Black-Scholes with `sigma = vix/100` flat across strikes (`:245-256`) — no 0DTE
  smile, no skew, **no bid/ask anywhere in the file**.
- `spx_at_entry = spx_close` (`:740`) — **all** entry times (9:36, 10:00, 11:00, 12:00) use the
  same day's **closing** price as entry. Direct look-ahead; the comment calls it "conservative."
- Stops read daily `spx_high`/`spx_low` (`:425-426`) — cannot know which came first, so stop-outs
  are ordered by assumption. Expiry outcomes are hand-written buckets (`:463`). Fill probability
  is invented from "empirical observations" (`:124-173`) resolved by an **unseeded**
  `np.random.random()` (`:790`), so results aren't reproducible run to run.
- `SLIPPAGE_PER_LEG = 0.02` (`:887`) = **$2/leg** on 0DTE SPX, ~an order of magnitude light — and
  gated behind an opt-in `--realistic` flag (`:1469`), so headline numbers exclude even that.
- Parameter fitting in plain sight: `core/gex_strategy.py:29` —
  `FAR_FROM_PIN_MAX = 50  # FIX 2026-01-10: Increased from 25 to 50 (was rejecting all trades)`.
- Contains ~25 LLM-written markdown reports including `CRITICAL_ANALYSIS_MONTE_CARLO.md`, which
  asks "Are These Results Real?", audits the *Kelly sizing*, marks it "✅ VERIFIED", and never
  opens the pricing function.

### 6.2 `repque/vrp` — backtests the untradeable spot VIX index
2★, 2025-08-24. 465 tests, Markov chains, pydantic, SQLite, production trader. Killer, in
`services/backtest_engine.py::_calculate_trade_pnl`:
```python
iv_change_pct = curr_iv / prev_iv - 1.0
pnl = old_position * iv_change_pct
```
**P&L is position × the percentage change in the VIX index itself.** No instrument — no futures,
no ETF, no option, no roll, no term structure, no vega, no theta, no bid/ask, no commission
(grep for `cost|commission|slippage|spread` in the backtest engine returns nothing). **Spot VIX has
never been tradeable.** Compounding it: `total_return = sum(pnls)` (`:355`), no compounding, no
capital base; max drawdown in the same undefined units. Win rate is a headline metric alongside
`avg_win`/`avg_loss`. `iv_change_ratio` clipped to [0.1, 10] (`:72-74`) silently truncates exactly
the tail moves that decide short-vol survival. **Not one of the 465 tests validates that the P&L
corresponds to a tradeable position.**

### 6.3 `emlama/gex-backtesting` — survivorship that deletes the losers, exactly as predicted
8★, created *and* pushed 2026-03-03 (one-day repo). Not a trading backtest — a hypothesis test of
"does a gamma metric spike predict a 0DTE put gaining >100% in 15/30/45/60 min", with GCI
(Herfindahl of gamma by strike) > 0.30, PGR < 0.25, CAR > 2.5 (`src/config.py:128-131`).

1. **Survivorship — deletes the losers.** `src/put_tracker.py:334-341`: exit price comes from
   `get_prices_at_time()`, which returns `None` if **no trades occurred** at that strike in a
   ±60s window (`:247-251`). A 0DTE put decaying to zero stops trading; an exploding put trades
   constantly. Dead options silently become `pct_gain = None` and drop out. **The outcome variable
   is conditioned on the option still being alive** — your `bid > 0` failure mode in a new costume.
2. **Buys at the bid, sells at the mid.** `:308` `entry_price = entry.bid_price`; `:336-338` exit
   uses `mid_price`. The docstring (`:15-19`) calls bid entry "conservative" — for a **long** put
   it is the single best possible fill. Free half-spread on every trade.
3. **The real bid/ask is never used.** Despite the README advertising `bid`/`ask` columns,
   `put_tracker.py:255-269` re-derives them from trade-side classification, and with no bid-side
   trade falls back to `df_window["price"].min()` — the minimum trade price in a 2-minute window
   as your entry.
4. **Spot is fabricated.** `src/data_loader.py:137-156` `_estimate_spot()` sets spot = the
   highest-volume strike that minute. SPX strikes are quantized to 5/25 points and gamma is acutely
   moneyness-sensitive, so every downstream greek is quantization noise. `:156` `.bfill()` is also
   intraday look-ahead.
5. **Threshold shopping.** `src/processor.py:293-294` substitutes `df_valid[metric].quantile(0.90)`
   — a **whole-sample** quantile of the data being tested.
6. **The backtest was never run.** `notebooks/02_multi_metric_backtest.ipynb` has **0 of 27 cells
   with saved output** and cell 8 is hardcoded `LIMIT = 10`. The one notebook with results ran on
   **9 days** against a *different* private source, and its two reported GCI spikes fire at 15:50
   and 15:55 ET — **outside its own declared 14:00–15:45 window**.

Credit where due: it uses intraday trade flow rather than OI, sidestepping the OI-publication
look-ahead entirely.

### 6.4 `grantreed1/Cross-Asset-Macro-Volatility` — Sharpe 1.97 is near-tautological
1★, 2026-03-13. The most professional-looking and the most misleading. Look-ahead discipline is
genuinely correct (z-score moments `.shift(1)` at `:133`, backtest uses `yesterday_z` at `:34`).
Then:
- **`z_threshold=0` in every notebook invocation** (`:705, 725, 743, 766`). The advertised
  "conditional relative-value gate" is disabled — it trades every day. This is a permanent
  2×-levered short-vol/long-vol pair, not VRP timing.
- **There are no option prices anywhere in the repo.** P&L is a second-order Taylor expansion
  (`:92-95`): `pnl_short = −[0.5·Γ·(dS)² + 𝒱·dIV + Θ] × shares`, with greeks from
  `calculate_greeks(spot_yest, spot_yest, 30/365, iv_yest, rate)` — **a fresh ATM 30-day straddle,
  re-struck at yesterday's spot, every day, for free.** No option bid/ask, no commission, no strike
  slippage, no assignment. `friction_bps=0.0005` is charged **only on delta-hedge shares**
  (`:98,121`), never on the options. Real ATM straddle round-trips on GLD/USO/HYG are 1–3% of
  premium; ~252×/year annihilates the result.
- **The 1.97 Sharpe is close to arithmetic tautology.** Theta is computed *from* IV and gamma P&L
  *from* realized dS. If IV > RV on average — which it does — the model is structurally obliged to
  print positive P&L. It measures the VRP's *existence*, not its *harvestability*.
- Sample 2015–2025 nominally includes Feb 2018 and Mar 2020, but `0.5·Γ·(dS)²` wildly misstates a
  true straddle payoff on a −12% day, and the delta term is omitted entirely.

### 6.5 `puneet-chandna/0DTE-dealer-gamma` — unshifted signal, and SPX is SPY×10
4★, 2026-05-10. Mostly a dashboard; the backtester is `backend/app/core/vectorbt_backtester.py`
(238 lines). Signal: long when `net_gex < −$1e9`, exit when `net_gex > 0` (`:52-53, :93-94`).
- **Unshifted signal into same-bar close fill.** `:90` ffills GEX onto the close index, `:93` builds
  entries, `:98` `vbt.Portfolio.from_signals(close=close, ...)`. **No `.shift(1)` anywhere** — vectorbt
  fills at the signal bar's own close.
- **GEX-specific look-ahead confirmed:** GEX built from open interest
  (`gex_calculator.py:115`, `:281`), so same-day OI drives a same-day close entry. OI publishes
  after the close.
- **SPX is fake.** `yfinance_provider.py:52` `SPY_TO_SPX_RATIO = 10.0`, applied to bid, ask and spot
  (`:151-152, :273-274`). "SPX dealer gamma" is the SPY chain multiplied by ten.
- Costs *are* modelled (`fees=0.001, slippage=0.001`, `:55-56`) — but on the **underlying**, because
  it trades the index close. A "0DTE dealer gamma" repo whose backtest contains no option.

### 6.6 `jefrnc/ibkr-odte-strategies` — cannot execute a single trade
16★, 2026-04-02. `src/backtesting/backtest_engine.py` (28 KB): grep for
`slippage|commission|bid|ask|mid|black_scholes` returns **zero matches**.
- **It never touches an option.** `backtest_odte_breakout` (`:99`): `premium = close * 0.015  # Estimación`.
  The option price is a hardcoded 1.5% of the stock price. No delta, gamma, theta, IV.
- **It also produces zero trades.** `load_historical_data()` defaults to `timeframe='day'` (`:65`) and
  the breakout function calls it without a timeframe, so `day_data` is one row per date and the loop
  `for i in range(1, len(day_data))` iterates over an empty range. **The intraday breakout backtest
  cannot fire on daily bars.** Whatever numbers exist were not produced by this code path.

### 6.7 `auto-d1dact/spx_options_backtesting` — dead, and a data trap
14★. Its own README says it uses **"Black-Scholes Proxies"** — no real option quotes anywhere.
`Python Code/spx_checking.py` imports **`pandas.stats.moments`**, removed in pandas 0.20 (2017);
the code has not run in ~9 years, and it reads CBOE URLs that 404 today.
**Trap:** it ships ~200 files named `bokeh-spx/daily/table_aapl.csv`, `table_abbv.csv` etc. that
look like single-stock option chains. **They are not.** I fetched `table_aapl.csv` — plain daily
equity OHLCV (`19980102,0,3.31397,3.95098,...`). No strikes, no expiries, no bid/ask.

### 6.8 `guiregueira/Put_Call_Ratio_Backtest` — avoid
3★. README advertises **"Annual returns = 22.51%"**. The entire repo is a 345 KB notebook, a 74 KB
`PUT_CALL_PARITY_DATA.xlsx`, and a 244-byte README. A hand-built Excel file as the only data
source, a headline annual-return claim, no cost model, no OOS split, no trade count — and the file
name (`PUT_CALL_PARITY`) doesn't even match the stated signal (put/call *ratio*).

### 6.9 `Matteo-Ferrara/gex-tracker` — 207★, and it silently serves 2022 data
**Last push 2023-04-08 (dead).** 163-line script, no backtest, no strategy, no returns.
GEX = `spot * gamma * open_interest * 100 * spot * 0.01` (`main.py:75`), then `puts *= -1` (`:78`)
— the naive convention, stated in the README: *"we assume that dealers are long calls and short
puts."* **The bug worth knowing:** `main.py:31-33` checks `if f"{ticker}.json" in os.listdir("data")`
and prefers the cached file, and the repo **ships `data/SPX.json` (8.5 MB)** with header
`{"timestamp": "2022-05-06 10:06:11", ...}`, committed in the initial commit and never updated.
**Anyone who clones this and types `SPX` gets a May 2022 snapshot presented as current GEX.**
That is what 207 people starred. `plt.style.use("seaborn-dark")` (`:11`) also breaks on
matplotlib ≥3.6, so it likely doesn't run at all.

### 6.10 The rest of the GEX dashboard genre — no backtest exists
`gammagrid/gammagrid` (44★, yfinance only, honest about it — `app/metrics.py:15-19` explicitly
documents that *"open_interest barely updates intraday"*), `EazyDuz1t/EzOptions` (74★),
`zrack/gex-terminal`, `tony3641/spx_0dte_gex_dashboard`, `isayev75/spx-greeks-dashboard`, and ~20
near-identical others: **live visualizers with no PNL series anywhere.** Star counts here measure
chart aesthetics. `aicheung/0dte-trader` (94★, dead since 2023-01-27) is an IBKR order-router —
grep returns **zero** occurrences of "backtest", "GEX" or "gamma" as a signal; it defaults to
short-premium structures with a 300% stop, i.e. it automates the exact negative-expectancy trade
you already measured.

Two generic defects to check in any GEX code you write yourself:
- **The naive dealer-sign assumption** ("calls dealer-long, puts dealer-short") is asserted in
  every repo above, never estimated. It is the entire foundation of the number.
- **Open-interest look-ahead.** OI publishes *after* the close; any intraday GEX signal using
  same-day OI uses tomorrow's information.

### 6.11 Also checked, nothing to take
- **`eigenquant53/VRP`** (32★, dead 2022-12-20): `LSV.py` and `HSLV.py` are **byte-identical**
  (md5 `504c7018…`), so "three strategies" is two. Signal is `UX1/VIX_spot − 1` at 10:00 ET,
  threshold 0, all-in SVXY or VIXY. To its credit it uses **real ETFs, not XIV**, uses
  `DataNormalizationMode.Raw` for the front future (the author understood back-adjustment would
  corrupt the basis), and Feb 2018 and Mar 2020 are **both inside** — at 100% notional in SVXY
  overnight on 2018-02-05, which should be a near-account-death event. **Zero results are
  committed.** 32 stars for an unreported backtest.
- **`peterchettiar/trading-volatility`** (10★): replicates the *same* Swedish thesis — I diffed
  the PDFs, identical file (md5 `adbb91f1…`). **Zero transaction costs** (grep returns nothing),
  and the notebook passes the portfolio **value** series where `perf_measure.py:107` expects
  returns, so the reported Sharpe is meaningless. Signal and fill are both the same day's open.
- **`aaajiao/VIX-Term-Structure-Pro`** (3★): an `indicator()`, not a `strategy()`. **56 `input.`
  declarations** and an "AI Score" of hand-assigned magic integers. Win rate only — no expectancy,
  no drawdown, no costs, no instrument.
- **`lucasbertovic/Volatility-Risk-Premium`** (1★): no backtest, no P&L. A vol-*forecasting*
  exercise on a 2-year window (2022-11 → 2024-11) containing neither Feb 2018 nor Mar 2020, in a
  monotonically-declining-vol regime maximally flattering to "IV > RV". Likely alignment bug at
  `:899,901` — `groupby(level=0)[iv].rolling(N).mean().shift(1).values` assigned back to the parent
  frame, where the groupby-rolling MultiIndex row order need not match. Value is the CSVs (§5.4).
- **`duc-v-le/dealer-gamma-volatility`** (1★): genuine academic 2SLS (WRDS/OptionMetrics,
  2016–2024, monthly-OPEX dollar gamma as a calendar instrument). **No strategy, no backtest,
  correctly so** — the outcome is realized volatility, never returns. Committed results are a
  negative: the policy variable gives **first-stage F = 1.6 and 1.9** (hopelessly weak
  instruments); the spec with a strong instrument (F=62.8) instruments *gross* gamma and he labels
  it `"not policy var"` himself (`scripts/e4_iv2sls.py:80`). His own docstring: *"the exclusion
  restriction... is not airtight."* Literature, not code.

---

## 7. WHAT THIS SWEEP CHANGES

1. **The condor question is closed.** Your SPY result and Vilkov's SPXW result are two independent
   real-quote datasets, two instruments, two researchers, one answer. Write it down; stop testing it.
2. **Your single-stock data gap is closed today, for free.** §5.1. Real bid/ask + greeks, broad US
   universe, ~2020-02 → 2024-11, keyless. This is the highest-leverage action item in the report.
3. **Your 1,001 dead regime cells may have been conditioning on the wrong variable.** The one
   BH-significant, clustered-SE-robust result in the best study in the space is that **realized
   skewness, not variance, drives 0DTE structure PNL** (§2 S2) — and an independent repo shows a
   trailing-RV gate fires 87% of days with 16 transitions in 3.5 years (§4.4). GEX, DIX and VIX
   regime are all slow vol/positioning proxies. **Skew is untested in your work.**
4. **Exactly one unconditional structure is left standing anywhere** — the put ratio spread — and
   §1.3 gives a concrete, checkable reason to expect it dies under an honest spread charge. That
   test is cheap and you have the data.
5. **Adopt `future_poison_test`** (§3.1). Randomize everything after your decision cutoff, re-run,
   assert bit-identical output. It would have caught the entry-price bug in half the repos in §6.
6. **The public GitHub options space contains essentially nothing else.** Outside one academic's
   replication package, it is dashboards without backtests, yfinance snapshots without bid/ask,
   Taylor-expanded straddles with no option spread, and spot-index P&L. That is not a failure of
   searching — it is the finding.

---

## 8. Appendix — dominant failure modes observed, ranked by frequency

| Failure mode | Repos |
|---|---|
| **Fictional execution** (no option ever priced from a real quote) | §6.1, 6.2, 6.4, 6.5, 6.6, 6.7, 4.3 |
| No transaction costs at all | §6.11 (×2), S3 source |
| Unshifted signal / same-bar close fill | §6.1, 6.5 |
| Survivorship deleting worthless options | §6.3 |
| Asymmetric fills (buy bid, sell mid) | §6.3 |
| Whole-sample normalization or quantile | §4.1, §6.3 |
| Open-interest look-ahead | §6.5, genre-wide §6.10 |
| Win rate reported without expectancy | §6.2, §6.11 |
| Dashboard presented as research | §6.9, 6.10 |
| Selection on realized OOS performance | §1.5.2, §1.5.3 |

Notably **absent**: the XIV survivorship trap. Not one repo in the VRP set traded XIV or a
reconstructed post-2018 series. The dominant sin in this space is not survivorship — it is
**pricing options that never existed**.

---

*A parallel data-source sweep (DoltHub breadth beyond what §5.1 measures, Hugging Face, Kaggle,
Zenodo, OptionsDX free tiers, 2026 vendor pricing) was still running when this was written. §5 is
complete and verified as it stands; that sweep can only add.*
