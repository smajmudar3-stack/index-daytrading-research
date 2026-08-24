# Macro-Conditioned Swing Systems: Public GitHub Sweep

Companion to `RESEARCH_SWING_REPOS.md` (price/TAA-focused) and `RESEARCH_SWING_ACADEMIC.md`.
This one is scoped to **macro, rates, credit, and economic-surprise** signals at a
5–21 trading day horizon, and to the one methodological question that dominates them all:
**did the author use data that existed at the time?**

Method: GitHub repo-search API across ~95 distinct queries, plus GitHub code-search for the
ALFRED vintage API. ~250 repos triaged; 28 read at source level (including notebook cells).
Every performance number below was checked against the code that produced it, not the README.

---

## THE HEADLINE ANSWER

**No. There is no public repo with a macro-conditioned swing strategy that both survives
methodological scrutiny and shows an edge.**

But the shape of the failure is informative, and it is not "nobody tried." It is this:

> The three repos in this sweep that handle macro data correctly **all report a null.**
> Every repo reporting a large macro-conditioned edge has a specific, locatable bug.

| Repo | Methodology | Result it reports |
|---|---|---|
| `brianbeals/sector-rotation-screener` | ✅ real ALFRED vintages, unit-tested; costs; PIT price slicing | **Did not beat SPY net of cost, 2011–2026** |
| `rapu34/Macro-Quant-Sector-Rotation` | ✅ expanding walk-forward, frozen-param holdout, cost sensitivity | **Alpha t = 0.15**, R²=0.85 vs mkt/size/mom/duration |
| `marcellekostic/macro-treasury-futures` | ✅ real ALFRED vintages, 21d purge, cost sweep | Sharpe 0.50 / 6.5y ⇒ **t ≈ 1.3** |
| `WKoniczynski/AI-Fund` | ❌ 2024 mega-caps run from 2009 | +3.57%/yr "alpha" |
| `TradingBotRepo/…-Sector-Rotation-Bot` | ❌ same-day close in signal *and* return | $1M → $39.3M |
| `JacksonSeowJX/macro-sector-allocation` | ❌ regime at t trades return at t | (invalidated anyway, see below) |

This is convergent corroboration of your own null, from three independent codebases with
different universes (sector ETFs, sector ETFs + XGBoost, Treasury futures), different macro
inputs, and different horizons. **Treat the macro-conditioned sector-rotation hypothesis as
falsified in its naive forms**, and spend the remaining effort on the two dimensions nobody
in this sweep actually tested (see "Open gaps", below).

### On your own `scripts/macro_test.py`

Two things worth recording, because they change how to read your result:

1. **Your test is vintage-clean, and that is not luck — it is a limitation.** Every series you
   used (`^TNX`, `^FVX`, `^IRX`, `TLT`, `HYG/IEF`) is a market price. Market prices are never
   revised, so the vintage trap that kills 9 of the 10 sector-rotation repos below simply does
   not apply to you. The flip side: you only tested macro variables that markets reprice
   continuously and therefore arbitrage away within the day. You have **not** tested
   slow-published macro (claims, IP, CPI surprises), which is where any residual would live —
   and testing that *will* require ALFRED.

2. **Your t-stats are inflated by ~√h, and your null survives it anyway.** In `macro_test.py`:

   ```python
   fwd = c[sec].shift(-h) / c[sec] - 1.0          # h ∈ {5, 10, 21}, sampled DAILY
   rec[f"{lab}_t"] = (f_sig.mean() - f_all.mean()) / (f_sig.std() / np.sqrt(len(f_sig)))
   ```
   At h=21 each observation shares 20 of its 21 days with its neighbour, so effective N is
   ~len/21 and the t-stat is overstated by roughly √21 ≈ 4.6×. **This makes your null
   stronger, not weaker** — you found nothing even with generously inflated t-stats. Worth
   stating explicitly in `FINDINGS.md` so it isn't re-litigated later.

3. **Your multiple-testing bar is mis-specified in the opposite direction.** `sqrt(2*ln(216))
   ≈ 4.6` assumes 216 independent trials. Your 18 sectors are pairwise ~0.7–0.9 correlated, so
   the effective number of independent tests is closer to ~15–25 than 216, and the correct bar
   is nearer 2.6–2.9. The two errors partly offset, which is why the conclusion holds — but
   the right fix for both at once is a **panel test with date-grouped random effects**
   (see Signal #0).

---

## TIER A — Worth mining for METHOD (none of them for edge)

### A1. `macrosynergy/macrosynergy` — 190★, BSD-3, pushed today. **The single most valuable repo in this sweep.**
`https://github.com/macrosynergy/macrosynergy`

This is J.P. Morgan Macrosynergy's open-source research stack. The *data* (JPMaQS via DataQuery)
is premium and out of reach. The *methodology* is BSD-3 licensed and directly liftable, and it
is the only codebase in this sweep built from the ground up around "the information state of
markets."

**Four things to take:**

1. **`panel/make_zn_scores.py` — sequential zn-scores.** The correct anti-look-ahead
   normalization, and a strictly better default than a z-score:
   - `sequential=True` → neutral level and dispersion estimated on an **expanding** window
     using only concurrently available data.
   - Dispersion is **mean absolute deviation**, not standard deviation — far more robust to the
     fat tails macro series actually have.
   - `neutral="zero"` by default (not "mean") — an explicit choice that a signal like a credit
     z-score is naturally centered at zero rather than at its own historical mean.
   - `thresh` winsorizes at ±N.
   - **Caveat to fix if you lift it:** `iis=True` (the default) estimates the first `min_obs`
     (261 days ≈ 1 year) window *in-sample from the full initial sample* — a documented, bounded
     look-ahead over the burn-in year. Set `iis=False` or discard the first year.

2. **`signal/signal_return_relations.py::map_pval` — the Macrosynergy Panel test.** This is the
   fix for your 18-sector problem. It fits a **period random-effects panel model with random
   effects grouped by `real_date`** (Swamy-Arora feasible GLS) and reports the two-sided p-value
   on the slope. Because the random effect is on the *date*, it absorbs the cross-sectional
   correlation that makes 18 correlated sectors masquerade as 18 independent tests. It also
   ships a degeneracy guard that returns `nan` rather than a spurious p≈0 on a near-constant
   column — a bug class worth stealing the guard for.

3. **`pnl/naive_pnl.py` — the backtest engine.** `make_pnl(sig_op=..., rebal_freq=...,
   rebal_slip=...)`. Signals computed daily, positions shifted `.shift(1)` then held to the
   next rebalance, plus an explicit `rebal_slip` in days on top. `rebal_freq="weekly"` gives
   ~5-day holds and `"monthly"` ~21-day holds — **exactly your swing band**, with the
   signal/execution lag handled correctly by construction rather than by discipline.

4. **`management/utils/sparse.py::InformationStateChanges` — the right data model for vintage
   macro.** Rows are stored only where the *information state* changed, and each carries
   `eop_lag` (days since the end of the observation period the value describes) plus a
   `grading`. This is the schema to replicate on top of ALFRED: not "value by date" but
   "value, as known on date D, describing a period that ended `eop_lag` days ago."

**Do not** expect a free signal from this repo. Expect a correct measuring instrument.

---

### A2. `stefan-jansen/machine-learning-for-trading` — 20,445★, MIT, pushed today
`https://github.com/stefan-jansen/machine-learning-for-trading`

Two files are the best free written treatment of the exact trap you need to avoid:

- **`04_fundamental_alternative_data/07_macro_data_alignment.py`** — ships an explicit
  `RELEASE_LAGS` table (CPI ~15d, GDP ~30d, ICSA ~5d, WALCL ~7d, daily series 0) and an
  `apply_release_lag()` implementation. It is honest about its own limits, which is why it's
  trustworthy: *"NOTE: This uses row-based shift, which assumes continuous daily data with no
  gaps... the lag values are approximate anyway (release schedules vary)."* Its closing
  checklist names your three failure modes verbatim: observation date instead of release date;
  final revised values instead of vintage data; ignoring the release calendar.
- **`02_financial_data_universe/14_point_in_time_validation.py`** — the bitemporal framing
  (event time vs knowledge time), a demonstration that a *centered* moving average leaks, and
  a worked FRED `vintage_date` query showing the GDP advance estimate against the revised value.

Use `07_macro_data_alignment.py` as the spec for your own lag table, and `14_point_in_time_validation.py`
as the source of CI assertions.

---

### A3. `brianbeals/sector-rotation-screener` — 0★, MIT, pushed 2026-08-09. **The only correct ALFRED implementation in the sector-rotation cluster.**
`https://github.com/brianbeals/sector-rotation-screener`

Already noted in `RESEARCH_SWING_REPOS.md` §B1. The macro-specific verdict: **lift `data.py`
wholesale.** It is the single most directly reusable artifact in this sweep.

`fetch_macro_vintage()` calls `fred.get_series_all_releases(code, realtime_start=…,
realtime_end=…)` in **2-year realtime chunks to stay under FRED's 2,000-vintage cap** — a
real API gotcha you would otherwise discover the hard way on `DGS10`. It then derives
`realtime_end` per reference date as `groupby("date")["realtime_start"].shift(-1) - 1 day`,
and `value_as_of()` filters `realtime_start <= asof <= realtime_end`. There are unit tests:
`tests/test_vintage_data.py::test_value_as_of_hides_future_revisions` and
`::test_value_as_of_hides_unpublished_observations`. It also refuses to write its cache if
any series came back empty, with the comment that a poisoned cache *"produces a misleadingly
good backtest."*

**One subtle bug to fix when you lift it:** ALFRED clamps the returned `realtime_start` to
whatever you passed in. For the earliest chunk, any value first published *before* the chunk
start comes back stamped with the chunk boundary, so its "first known" date is wrong. Start
the chunking at least one full revision cycle before your backtest start and discard the
lead-in.

**Its actual signal** (worth knowing, because its result is a null):
`spread = DGS10 − DGS2`, `indpro_yoy` = 12m % change of INDPRO, `spread_dir` = 6m change in
spread. Then, in order: `indpro_yoy < −2%` → Recession; `spread ≤ 0 and indpro_yoy ≤ 0` →
Recession; `spread_dir ≥ +0.50 and spread ≤ 0.50` → Early; `spread ≤ 0` → Late;
`spread_dir ≤ −0.50 and indpro_yoy > 0` → Late; `indpro_yoy > 4% and spread > 0` → Early;
else Mid. Phase→sector: Early = XLY/XLF/XLI, Mid = XLK/XLC, Late = XLE/XLB/XLV,
Recession = XLP/XLU/XLV. Composite = 0.25·seasonality + 0.40·cycle_fit + 0.35·rel_strength;
month-end rebalance into equal-weight top-3 with composite ≥ 50, else park in SPY.
1 bp one-way on L1 turnover. **Result: did not beat SPY net of cost since 2011-05.**

Red flags are minor by this cluster's standards: no parameter holdout (weights, `SIGNAL_BUY=65`,
`MAX_POSITIONS=3` all fixed and evaluated on one window), and one admitted in-sample choice —
`# Park in SPY instead of cash to avoid drag in bull markets.` It handles the ETF-inception
problem properly (`SECTOR_INCEPTION` + `inception + 365d <= asof`), so XLRE and XLC only enter
the universe when they existed.

---

### A4. `marcellekostic/macro-treasury-futures` — 0★, pushed 2026-08-05. **ALFRED claim verified; price data broken.**
`https://github.com/marcellekostic/macro-treasury-futures`

The only other repo that genuinely reconstructs point-in-time macro. `src/data/alfred_client.py`
hits `series/observations` once per vintage with matched bounds:

```python
params={"series_id": series_id,
        "realtime_start": vintage_date,
        "realtime_end":   vintage_date,   # true as-of snapshot
        "observation_start": observation_start, ...}
```
enumerating vintages via `series/vintagedates`; `build_asof_snapshot` filters
`vintage_date <= asof_date` before taking the last value per observation date, and
`build_asof_yoy_series` computes YoY **only on release dates** before forward-filling onto
business days. That last detail is the one most people get wrong.

**The signal, precisely:** 6 ALFRED series → `CPIAUCSL` YoY, `CPILFESL` YoY, `PAYEMS` YoY,
`UNRATE` level, `INDPRO` YoY, `ICSA` level. Each → 4 transforms: raw level, `.diff(21)`,
`.diff(63)`, expanding z-score with `min_periods=252` = **24 features**. Target =
`prices.shift(-21)/prices - 1`, i.e. **21 trading-day forward return**. Model =
`Pipeline(StandardScaler, Ridge)` refit every 5 days on an expanding window, `min_train_size=756`.
Universe TU/FV/ZN/ZB/UB. Sizing: forecast → avg-abs-10 scaling (expanding, shifted) → capped
±20 → `/ann_vol` (EWM 32, shifted) → gross-normalized → 10% portfolio vol target (EWM 63,
shifted) → leverage cap 3×. Daily rebalance, `positions.shift(1)`. Costs 1 bp/unit turnover
with a `[0, 0.5, 1, 2, 3, 5]` bp sweep.

**The purge is genuinely correct**, and worth copying verbatim:
```python
training_end_position = forecast_position - target_horizon   # 21
historical_data = dataset.iloc[:training_end_position][...].dropna()
```
The last training row's 21-day label ends the day before the forecast date. Scaler fit inside
the loop on train only. Ridge alpha tuned on a 2018–2019 slice preceding the 2020+ test.

**Why you cannot use its result:**
- 🔴 **Unadjusted Yahoo continuous futures.** `ZN=F` etc., `Close`, with exactly one break
  patched: `KNOWN_PRICE_BREAKS = {"ZB": ["2015-03-23"]}`. Every other quarterly roll injects a
  fabricated return into both the label and the P&L. On 2y/5y notes the roll gap is comparable
  to a month of alpha.
- 🔴 No t-stat, no Newey-West, no DSR anywhere. The headline Spearman IC ~0.13 and 55% direction
  accuracy are computed on 21-day forecasts sampled daily — each day counted ~21×.
- 🔴 The README's "2020–2026 out-of-sample" table corresponds to no script in the repo:
  `build_ridge_forecasts.py` hardcodes `alpha=1.0`, `final_model_evaluation.py` uses
  `FROZEN_ALPHA=0.0001`, and `build_portfolio_returns.py` computes stats over the entire
  2014–2026 series with no test-window filter.
- Sharpe 0.50 over 6.5y ⇒ t ≈ 1.3. Not significant; the README doesn't say so.

**Take:** `alfred_client.py` and the purged expanding-ridge loop. Leave the rest.

---

### A5. `eslazarev/purged-cross-validation` — 25★, pushed 2026-08-01. **Adopt it.**
`https://github.com/eslazarev/purged-cross-validation`

Not a strategy — the correct implementation of the statistics you need, with an
arXiv/JDSSV paper, ~25 unit + ~28 e2e test files, and property-based tests. Verified correct
at source level in several places where the standard references are subtly wrong:

- **`purge`** merges disjoint test intervals *before* filtering rather than purging the convex
  hull between them. For CPCV with non-adjacent test groups the naive version over-purges.
- **`apply_embargo`** is properly asymmetric, and `embargo == 0` is an explicit identity rather
  than a degenerate single-point window.
- **PSR** uses **raw (non-excess) kurtosis** — `fisher=False  # NOT excess` — which is the exact
  line most implementations get wrong.
- **DSR** = PSR against `SR* = √V[SR]·[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne))]`. Correct composition.
- **PBO/CSCV** uses contiguous (not shuffled) blocks and `omega = rank/(n+1)` to keep logits finite.
- **`deflated_sharpe_ratio` refuses to estimate `var_sharpe` for you.** That is the honest
  choice — a library-guessed trial variance is exactly where DSR silently becomes meaningless.
  Given your prior DSR mis-specification on the ETF ensemble (per `MEMORY.md`), this is the
  library to standardize on.
- `diagnostics.assert_no_temporal_leakage`, `assert_embargo_respected`,
  `compute_overlap_fraction` are usable as CI assertions on *your* pipeline independent of the
  splitters.
- Its leakage demos are controlled experiments, not marketing: on a synthetic unpredictable
  target, naive shuffled KFold reports R² 0.83 (kNN) / 0.91 (RF); `PurgedKFold` returns negative.

Caveat: `PurgedKFold(purge_horizon=0, embargo=None)` is exactly `KFold(shuffle=False)` — it
does nothing unless you supply horizons.

---

### A6. `mcravi8/PEAD-mini-WRDS` — 0★, **no license** (read, reimplement, don't copy)
`https://github.com/mcravi8/PEAD-mini-WRDS`

Included for one reason: it contains **the correct construction for overlapping multi-day
holds**, which is the bug live in your own `macro_test.py`. Instead of treating each event as
an independent observation, it accumulates every currently-open position into a **daily
portfolio return series**:

```python
pos = idx.searchsorted(d, side='left')
if pos < len(idx) and idx[pos] <= d: pos += 1      # start NEXT trading day
start = pos; end = min(start + hold_days, n)        # hold_days = 20
r = returns.iloc[start:end][t].astype(float).values
long_sum[start:end] += np.nan_to_num(r, nan=0.0)
long_cnt[start:end] += ~np.isnan(r)
...
ls_daily = pd.Series(mean_long - mean_short, index=idx)
```
The resulting `ls_daily` is a genuine daily P&L series whose Sharpe and t-stat are honest,
because each calendar day is counted exactly once. Cross-sectional deciles are assigned
**per date** (`groupby('date')`), so there is no whole-sample normalization. Costs are
modelled (`commission_bps`, `slippage_bps`, `borrow_bps` on turnover).

**Its remaining flaw, which you should not inherit:** `summarize_metrics` regresses `ls_daily`
on the market with plain OLS and reports `model.tvalues`. With 20-day overlapping holds the
daily series is strongly autocorrelated, so even this t-stat needs **Newey-West with ~20+
lags**. And its reported `ic_spearman_mean` is computed on per-event `fwd_ret`, which *is*
overlapping — the IC is not protected by the portfolio construction.

---

## TIER B — Read the code, ignore the numbers

**`rapu34/Macro-Quant-Sector-Rotation`** (0★) — the most elaborate build in the cluster (~70
files, governance/audit scripts, Streamlit dashboard) and the most honest reporting.
`PROJECT_REPORT.md` §1.5 states the OLS alpha is **not significant (t = 0.15)**, R² = 0.85
against market/size/momentum/duration/vol, β_mkt ≈ 0.31. Signal: 6 FRED series → 252d rolling
z, 21d MoM, 252d YoY, plus `yield_curve_10y2y` and `real_rate_zscore`; XGBoost (depth 4,
lr 0.05, 200 trees) predicting "top-3 by 20-day forward return"; expanding walk-forward with
per-fold scaler refit; costs 10 bp/side plus a sensitivity script;
`scripts/robustness_oos_evaluation.py:212` runs a genuine **frozen-parameter** holdout
(train 2010–2018, apply 2019+ with `scaler_train.transform()` and no refit) — copy that pattern.
Its bugs: plain `get_series` (revised data); `MACRO_LAG_DAYS = 20` business days is **~2 weeks
short for CPI and UNRATE** given FRED indexes them at period *start*; no purge at the fold
boundary despite a 20-day label; a whole-sample `hist_mean_5d` used as the crowding threshold
inside the walk-forward; and feature selection (`selected_features.json`) done on the full
sample before the folds.

**`oj0nathan/Macro_Factor_Model`** (1★) — cleanest design of the hobby cluster: 12 macro factors
(IP YoY and its 6m change, UNRATE gap vs 60m mean, CPI YoY and its 6m change, real fed funds,
120m z of T10Y2Y, 24m z of VIX, 120m z of BAA, M2/WALCL/USD YoY), `X = macro.shift(1)`, rolling
**84-month OLS** refit monthly with **standardization computed inside the training window only**,
sector target = excess return minus SPY, long top-3/short bottom-3 inverse-vol weighted.
Two disqualifiers: plain `fred.get_series` (`src/pipeline.py:81`), and a **look-ahead in the V2
short filter** — notebook cell 19 builds `trend_up = px > px.rolling(10).mean()` on month-end
closes, then cell 22 uses `trend_up.loc[dt]` to pick shorts for the return earned *over* month
`dt`. The author correctly `.shift(1)`'d `rolling_vol` one cell earlier and forgot here. That
bug is the source of V2's edge over V1. Also: zero costs, `sharpe = cagr / ann_vol`, and a live
FRED API key committed in cell 3.

**`shuklavaibhavv/Macro-regime-sector-rotation`** (0★) — the most intellectually honest README in
the cluster; it leads with its own negative result (Sharpe 0.87 vs SPY 0.91) and reports that
its vol-target overlay made things worse. Signal: `PMI proxy = 50 + IPMAN.pct_change(12)*100`
(note the unit mismatch — a YoY percent added to the number 50, then compared against ISM-style
45/50 thresholds) crossed with the sign of T10Y2Y into Expansion/Slowdown/Recovery/Contraction;
hold 100% of one sector per month. Disqualifiers: `pd.read_csv("…fredgraph.csv?id=IPMAN")` is the
current vintage; `resample('MS')` + `shift(1)` gives February's trade January's IPMAN, which is
published ~Feb 15 — **~2 weeks of look-ahead every month, needs `shift(2)`**; and the regime
thresholds (`pmi_change_3mo < -4`) were explicitly reverse-engineered from 2008 and held fixed
across the train/test split, so only the *sector map* is genuinely out-of-sample.

**`paride11/treasury_curve_rv`** (1★) — the best walk-forward discipline in the whole sweep, on
an instrument you can't trade. 7 duration-neutral zero-coupon butterflies off the Fed **GSW**
curve; signal = consensus of three z-scores (252d level z, 63d z, and the z of a **rolling
504-day causal PCA reconstruction residual**, refit daily, `hist = arr[start:i]` predicting
`arr[i]`); `entry_z=1.25`, `exit_z=0.25`, `max_holding_days=60`; 8% vol target; costs 0.15 bp.
Rolling 10y train / 2y test with non-overlapping concatenated test blocks, and it **ships a
deliberately-overfit full-sample benchmark purely so the IS-vs-OOS gap is visible**. Why it
doesn't transfer: the traded object is a constant-maturity zero-coupon point on a *fitted*
Nelson-Siegel-Svensson curve — much of the "PCA residual" at short tenors is curve-fitting
noise, not dislocation. Also, the signal-design hyperparameters (butterfly list, `z_window=252`,
PCA window/components, consensus threshold) sit **outside** the walk-forward grid and were
chosen on the full sample.

**`jamesjxliao/yass`** (2★) — PIT claim is **half true**. The Sharadar path is genuine
(`datekey` = public-availability date). The FMP path is a **synthetic fixed lag applied to
current, possibly-restated vendor values**: `observed_at = str(rd + timedelta(days=90))` for
annual, `+45` for quarterly. That removes announcement-timing look-ahead but **not restatement
bias**. Credit where due: `pit_server.py` refuses to fall back to live data when no PIT snapshot
qualifies — it skips the period rather than cheat; and `evaluation/robustness.py` has a correct
DSR plus a **Politis–Romano stationary block bootstrap**, the right tool for serially-dependent
returns.

**`younghwan91/opt_portfolio`** (2★) — best PIT *architecture* here, for equities not macro.
A bitemporal DuckDB store that keeps the first-reported value on restatement, per-source
availability offsets (13F +45d vs insiders +3d) kept separate, and — the part worth stealing —
**PIT enforcement that is architectural, not disciplinary**: factors can only read through
`PanelContext`, and `to_daily()` *raises* if no availability frame is supplied. Correct
Bailey–López de Prado DSR and CSCV/PBO. Its headline (CAGR 16.9%, Sharpe 0.756, DSR 0.992) does
not survive its own admission: **50 bps commission and zero slippage on a $5M–$80M market-cap
universe**, and factor selection (124 factors screened) never charged to the trial count.

**`FrancisSciaroni/hybrid-trend-following`** (1★) — excellent cost modelling (10 bp/side with a
breakeven sweep locating alpha=0 at ~80–90 bp round-trip) and unusually good self-criticism,
wrapped around a poisoned sleeve: `config/universe.yaml` hardcodes **50 mega-caps of 2024
(NVDA, TSLA, META, AVGO, LLY, AMD, NFLX…) and runs an all-time-high breakout strategy on them
from 2005.** That is ex-post winner selection, worse than plain survivorship, and it is the
sleeve credited with Sharpe 1.04 vs the clean sleeve's 0.51. Its "OOS Sharpe 1.02 > IS 0.72" is
a window artifact it identifies itself: the GFC is only ever in training.

---

## TIER C — Broken. Named so you don't spend time on them.

| Repo | The bug, specifically |
|---|---|
| `WKoniczynski/AI-Fund` | Universe is 100 hardcoded **2024 mega-caps run from 2009** (`backtest_engine.py:47-57`: NVDA, AVGO, TSLA, LLY, CRM…), then `dropna(axis=1, thresh=0.80*len)` silently deletes anything without full history. Plus `fred.get_series(series_id, observation_end=end)` — `observation_end` filters by *reference period*, not release date. Plus no publication lag: `as_of = month_start − 1 day` reads Q4 GDP first published a month later. Plus **scenario cherry-picking in a code comment**: the README's headline is Scenario E, defined as `# Scenario E: growth tier — allow PE 50-60 when ROE > 50% (catches NVDA-like compounders)`. Plus the regime rule was rewritten because the old one lost money in a known episode. Ironically its *fundamentals* are vintage-correct (SEC EDGAR filing dates) and its macro is not. |
| `TradingBotRepo/Macro-Economic-Sector-Rotation-Trading-Bot` (and the identical fork `idkwhattonamethis-cyber/…`) | **The "macro" is fake** — `coreTickers = {"consumer":"XLY","labor":"SPY","inflation":"XLE","credit":"XLF"}`; it is ETF momentum wearing macro clothing, no FRED anywhere. **Same-day look-ahead on every rebalance**: `windowPrices = prices.iloc[startIdx : i+1]` and momentum via `.iloc[-1]` use today's close to pick the book that earns today's return; and it fires on every regime-transition day, i.e. exactly the high-vol days where the bias pays most. **Second look-ahead** in the vol target: the leverage window `rawRets.iloc[i-lb+1 : i+1]` includes day `i`'s own return. Reports $1M → $39.3M. |
| `JacksonSeowJX/macro-sector-allocation` | **The returns are mangled**: `df_monthly = (1 + df/100) ** (1/12) - 1` applied to Ken French's `12_Industry_Portfolios.CSV`, whose monthly block is *already* monthly — de-annualized a second time, compressing every return ~12×. Every number in the notebook is computed on that. Separately, the regime at t (a 3-month rolling mean ending at t) selects the portfolio that earns month t's return. Also the OECD CLI (`USALOLITOAASTSAM`) is amplitude-adjusted with **two-sided smoothing**, so its published history embeds future information by construction — avoid that series for backtests on principle. |
| `MalharMardikar/SECTOR-ROTATION-BACKTEST-STRATEGY` | Not macro at all (no FRED; the "regime filter" is a MACD). **Input CSVs are missing from the repo** — not reproducible. **Short leg has a sign error**: `active_return = long_avg*long_w + short_avg*short_w` adds the unnegated short returns, so the advertised long/short is long-only. MACD is applied to a *return* series, not prices. Sharpe computed with no annualization on annual-resampled data. |
| `ZakariaGuemghor/macro-sector-rotation-…` | No backtest at all — correlation study only (and the README says so). One mislabeled series: `'Construction Spending': 'CPIAUCSL'`. Quarterly rows stamped `groupby('Quarter')['date'].first()`, so Q1-2020 GDP is dated `2020-01-01` though the advance estimate landed 2020-04-29 — ~4 months of look-ahead for anyone who reuses it. |
| `benjaminkhelifa/factor-rotation` | No macro, no signal, no backtest. The 26 files named `S*_financial_report.pdf` under `report/Backtest/` are **stress tests of the PDF reporting engine**, not strategy backtests. Hardcoded 3-month data window. |
| `ItsSawhill/market-regime-detection` | The ML plumbing is actually leakage-clean (genuine walk-forward, `scaler.fit_transform(X_train)`/`transform(X_test)`, `km.fit_predict`/`predict`, `exposure.shift(1)`). But **zero transaction costs** on a daily-flipping 0/0.25/0.5/1.0 exposure overlay, no significance test of any kind, and it averages SPY/QQQ/IWM as if they were 3 independent tests. Evaluation window 2015–2026 contains no 2008. |
| `genekindberg/DFM-Nowcaster` (34★ — the most-starred macro repo found) | Fine as an econometrics teaching artifact, **fatal as a signal source.** `_NormDframe`: `df2 = (df2 - df2.mean())/df2.std()` — whole-sample standardization. `_RemoveOutliers` clips against `np.nanmean`/`np.nanstd` of the **full** column. `_InterpolateNaN` uses `np.interp` over indices on both sides — **bidirectional interpolation**. And `Nowcast()` consumes `Hdraw/Qdraw/Fdraw/Sdraw` estimated **once on the full sample** by `estimateGibbs`, then emits "nowcasts" across history — textbook `fit(all) → predict(all)`. Its historical nowcast series is not a real-time series and must never be used as a backtest input. |

---

## THE ECOSYSTEM-WIDE FINDING

I ran GitHub **code search** to size the problem rather than guess at it.

| Query (language:Python) | Total hits | Genuine first-party users |
|---|---|---|
| `get_series_all_releases` | **103** | ~6. The rest are vendored `site-packages/fredapi/fred.py` copies inside committed venvs. |
| `get_series_as_of_date` | **37** | ~5, same story. |
| `fred.get_series` + `backtest` | **171** | essentially all of them |

**Almost nobody on public GitHub backtests macro on vintages.** The non-library first-party
users of the ALFRED vintage API across all of GitHub are roughly: `cuemacro/findatapy`,
`yieldcurvemonkey/Curvy-CUSIPs`, `ionmihai/finsets`, `RezaSoleymanifar/vintage`,
`brianbeals/sector-rotation-screener`, and `marcellekostic/macro-treasury-futures`. Two of
those are strategies, and both report a null.

Corollaries:
- **Any macro backtest you find on GitHub is contaminated until proven otherwise.** The prior
  should be ~95% contaminated, and "the README mentions point-in-time" is not evidence — three
  repos in this sweep claim PIT and two of the three don't deliver it for macro.
- **Zero repos replicate a Citi-CESI-style economic surprise index.** I searched
  "economic surprise index", "citi economic surprise", and scanned ~250 deduped repos: one
  hit, and it's an LLM news-scoring toy. This is a genuine open gap, not a crowded trade.
- **The index-rebalance / earnings-flow space is empty.** Twenty queries across
  S&P inclusion effects, Russell reconstitution, and ETF flows returned 18 deduped repos,
  all ≤1★, none with a working announcement-date dataset.

---

## OPEN GAPS — the two macro dimensions nobody in this sweep tested

1. **Surprise, not level or change.** Every repo here conditions on the *level* or *change* of
   a macro series. None conditions on **actual minus consensus**. That is the variable the
   literature says moves markets, it is the one you named, and it has zero public
   implementations. It is also the only one that requires data you don't yet have.

2. **Vintage-sensitive series.** Your test used only unrevised market prices. Every repo that
   used revised series (IP, CPI, UNRATE, GDP) got the vintage wrong. **Nobody has run a clean
   test of revised macro at a 5–21 day horizon.** That is a real hole — and A3/A4 give you the
   two working ALFRED clients to fill it.

---

## RANKED: signals worth backtesting, stated precisely enough to code

Ordered by (probability it's real) × (cheapness to test). #0 is not a signal — it's the
instrument, and everything else is unreliable without it.

### 0. Re-run your existing macro panel as a PANEL, not 216 cells — **do this first, it's a day**
Not a new hypothesis. A correct re-measurement of the one you already ran, fixing both
errors identified above.

- Keep `scripts/macro_test.py`'s signals and universe exactly as-is.
- Replace the per-cell t-stat with **one panel regression** across all 18 sectors:
  `fwd_ret[i,t] ~ 1 + signal[i,t]`, with **random effects grouped by date `t`** (Swamy-Arora
  FGLS, per `macrosynergy/signal/signal_return_relations.py::map_pval`, or `statsmodels`
  `MixedLM(groups=date)`). The date grouping absorbs the cross-sectional correlation that makes
  18 correlated sectors look like 18 independent tests.
- Additionally cluster/HAC the standard errors by date with **Newey-West at ≥ h lags** to kill
  the √h overlap inflation.
- Report a **single p-value per (signal, horizon)** — 12 tests, not 216. The honest
  multiple-testing bar is then ~2.5, not 4.6.
- **Expected outcome: still null.** The value is that the null becomes defensible and citable,
  and the instrument is then trusted for signals #1–#4. If a cell *does* survive here that
  didn't before, that is a genuine finding produced by fixing the statistics.

### 1. Trade the residual, not the forecast — your rate betas are the asset
Your strongest measured result is contemporaneous: **KRE +1.09, XLRE −0.24 to Δ10y**. You
concluded (correctly) that this is descriptive, not tradeable — because trading it requires
forecasting rates. But there is a second use that requires no forecast at all.

- Estimate `β_i` for each sector on Δ10y over a **trailing 252d** window, `.shift(1)`.
- Form the rate-neutral residual: `resid[i,t] = r[i,t] − β_i[t]·Δy10[t]`.
- Cumulate `resid` into a synthetic rate-neutral sector index per sector.
- Test the signals you have already falsified on raw returns — **on the residual series
  instead**: 5/10/21-day reversal and momentum, cross-sectional rank.
- Hypothesis: the sector-level noise you were testing was swamped by a rate factor with
  β up to 1.09. Removing a factor that large is the highest-leverage transformation available
  to you, and it costs one regression.
- Also test the **pair directly**: long KRE / short XLRE sized to β-neutrality
  (`w_XLRE = −1.09/0.24`… no — size to equal *dollar* rate exposure: `w_KRE·1.09 + w_XLRE·(−0.24) = 0`).
  That pair is a pure "rate-sensitivity spread" and is a cleaner instrument than 18 separate cells.
- Cost: uses only data you already have. **Test this second.**

### 2. Build the CESI nobody has built — free consensus data exists after all
This was the highest-value find of the data sweep: **a free, downloadable, 14-year history of
economic releases with both `Actual` and `Forecast`.** Zero repos have used it to build a
surprise index.

**Data:** `spoluan/forex-factory-scraper` →
`datasets/forex_factory_calendar_{2010..2023}.csv`, verified header
`Date,Time,Currency,Event,Impact,Actual,Forecast,Previous,Combined DateTime`.
Filter `Currency == "USD"`, `Impact == "High"`. **Fork it immediately** — 11 stars, no
maintenance guarantee. Bridge 2024→present with EODHD's `economic-events` endpoint (`estimate`
field confirmed, history from 2020, so you get a 2020–2023 overlap to cross-check for
back-edited forecasts) and cron the free ForexFactory weekly JSON going forward.

**Construction (standard CESI):**
1. Per event type `e`, compute raw surprise `s[e,t] = actual − forecast`.
2. Normalize by that event's **own rolling** surprise dispersion:
   `z[e,t] = s[e,t] / rolling_std(s[e,·], window=last 12 releases of e)`. Rolling, not
   full-sample — this is the exact spot the index becomes look-ahead if you get lazy.
3. Aggregate to a daily index with exponential decay:
   `CESI[t] = Σ_e Σ_{releases within 90d} z[e,τ] · exp(−(t−τ)/λ)`, λ ≈ 30 days.
   (Citi's actual construction is a 3-month rolling sum; the decay version is smoother and
   less prone to cliff effects when a release rolls out of the window.)
4. Timestamp with the **release date**, and only let the signal act from the **next** session —
   US macro prints at 08:30 ET, so same-day close is arguably tradeable, but assume T+1 first
   and test T+0 as a separate, clearly-labelled variant.

**Test:** `CESI[t]` and `ΔCESI[t] over 5/10/21d` → 5/10/21-day forward sector returns,
panel-tested per #0. Prior: cyclicals (XLI, XLB, XLE, KRE, XRT) load positive, defensives
(XLP, XLU) negative — and the *level* should matter more than the change, since CESI is
mean-reverting by construction (forecasters adapt).

**Free cross-check, and a good signal in its own right:** Atlanta Fed **GDPNow**
(FRED `GDPNOW` — verify with your key, FRED 403'd my unauthenticated fetch). Use
`surprise[t] = GDPNow[t] − GDPNow[t−k]`, k ∈ {5,10,21}. The nowcast only moves when a release
differs from what its model expected, so its *revision* is a release-weighted surprise.
Critically it is **vintage-safe by construction** — a published forecast is never restated. It
starts 2011 (~15 years, one recession), so it's underpowered alone but is an excellent
independent validation of a CESI you built yourself.

**Why this is #2 and not #1:** it needs new data plumbing, and the FF "Forecast" is
ForexFactory's consensus as displayed *today*, not a true point-in-time Bloomberg consensus.
That's a real caveat — but it is the only free path to the variable, and it is untested.

### 3. Credit-spread *state* (level percentile), not credit *change*
You tested `HYG/IEF` ratio *change*. The literature's variable is the spread **level** relative
to its own history, used as a slow state variable — a different object.

- Series: `BAMLH0A0HYM2` (HY OAS, from 1997-01) and `BAMLH0A3HYC` (CCC OAS). **Market-based,
  therefore unrevised — no ALFRED needed.**
- Signal: `state[t] = expanding_percentile(spread[t], min_periods=756)` — expanding, past-only,
  never a fixed bps threshold and never a full-sample z-score.
- Rule to test: long-only sector tilt conditioned on `state` terciles, rebalanced weekly
  (≈5-day hold) and monthly (≈21-day hold), with the **expanding-window mean-absolute-deviation
  zn-score** from `make_zn_scores` rather than a raw z.
- Test the *interaction* too: does `state` change the sign of your rate betas? (i.e. is KRE's
  +1.09 conditional on credit being tight?) That is a conditional-beta question your current
  test cannot see.
- Cost: free data, one new series. **Test this third.**

### 4. Vintage-correct slow macro at swing horizon — the genuinely untested hypothesis
This is the one nobody has run cleanly. It is also the most expensive.

- Lift `brianbeals/sector-rotation-screener/data.py` (MIT) —
  `fetch_macro_vintage()` + `value_as_of()` — and fix the chunk-boundary `realtime_start`
  clamping described in A3.
- Series where revisions actually bite: `ICSA` (weekly claims, ~5d lag), `INDPRO`, `PAYEMS`,
  `CPIAUCSL`, `UNRATE`. Add `T10Y2Y`, `DGS10`, `BAMLH0A0HYM2` unchanged (no vintage needed).
- Transform per `marcellekostic`: level, `.diff(21)`, `.diff(63)`, expanding z
  (`min_periods=252`) — but compute YoY **only on release dates** before forward-filling, per
  `build_asof_yoy_series`.
- Horizon: 21-day forward return. Universe: your existing 18.
- Statistics: panel test per #0, purge 21 days at every train/test boundary
  (`eslazarev/purged-cross-validation`), DSR with an honestly-counted `n_trials`.
- **Run the A/B that no repo has run:** the same pipeline on vintage vs latest-revision data.
  The gap between them is a publishable-quality result on its own, and it tells you exactly how
  much of the macro-backtest literature is artifact.
- Prior: still null at 5–21 days. But it is the last clean version of the question, and the
  A/B has value regardless of the sign.

### 5. PEAD — real effect, real horizon, but gated on earnings dates
The only 5–21 day anomaly in this sweep with an independent literature behind it. Build it
**only** with the overlapping-portfolio construction from A6:

- Signal: SUE = (actual EPS − consensus) / σ(recent surprises), cross-sectionally
  **decile-ranked per date** (`groupby('date')`), never pooled.
- Entry the **next** trading day after announcement; hold 20 trading days; long decile 10,
  short decile 1, equal-weight.
- Accumulate all open positions into a **single daily** long/short return series
  (`long_sum[start:end] += r`), so each calendar day is counted once.
- Report Sharpe and a **Newey-West t-stat with ≥20 lags** on that daily series. Do not report
  per-event IC.
- Costs: commission + slippage + borrow bps on turnover.
- Data constraint: consensus EPS history is the blocker. Your Robinhood MCP
  `get_earnings_calendar`/`get_earnings_results` is the cheapest path you already have wired;
  every serious PEAD repo in this sweep used paid WRDS/IBES.

### 6. Do NOT rebuild these
- Macro-regime → sector-map rotation (Expansion/Slowdown/Recovery/Contraction quadrants). Six
  repos, six variants, and the two implemented correctly both report a null. Consistent with
  your own 1,512-config sector-momentum null. Closed.
- HMM/KMeans regime detection as an equity overlay. The genre's clean implementations
  (`ItsSawhill`) produce nothing once costs exist; the dirty ones fit on all data.
- Nowcasting DFMs as a signal source, unless you re-estimate recursively on vintages — which
  is a multi-week project to test a hypothesis that #2 approximates for free.

---

## FREE DATA — verified this sweep

Marked **[v]** where the endpoint/file was actually fetched and read, **[d]** where only the
vendor's own doc text was read, **[?]** where blocked by bot protection and taken from prior
knowledge. Several vendor sites (spglobal, tiingo, FMP docs, norgate, simfin) hard-403 or
return JS shells, so prices below are worth re-checking before you commit.

### Vintage / real-time macro — the thing you actually need

**ALFRED via the FRED API** — free key at `https://fredaccount.stlouisfed.org/apikeys`. **[v]**
Three call shapes, in order of usefulness to you:

```
# 1. "What was known as of date D" — the primitive for a backtest loop
GET /fred/series/observations?series_id=PAYEMS&api_key=KEY&file_type=json
    &realtime_start=D&realtime_end=D&observation_start=1990-01-01

# 2. Every value ever published (1776-07-04 / 9999-12-31 are FRED's documented sentinels)
    &realtime_start=1776-07-04&realtime_end=9999-12-31
# then per as-of date D: rows where realtime_start <= D <= realtime_end

# 3. First print only, in ONE call — cheapest way to get an unrevised series
    &realtime_start=1776-07-04&output_type=4
```
`output_type`: 1 = by real-time period (default), 2 = by vintage date all obs, 3 = new-and-revised
only, 4 = **initial release only**.

**Two more endpoints that matter:**
- `GET /fred/series/vintagedates?series_id=X` — **use this to auto-classify your whole series
  list.** Unrevised series return effectively one date (or the client raises "No vintage date
  exists"). One cheap call per series tells you which need vintage handling and which don't.
- `GET /fred/releases/dates?realtime_start=…&realtime_end=…&include_release_dates_with_no_data=true`
  (and `/fred/release/dates?release_id=…`; 53 = GDP, 50 = Employment Situation, 10 = CPI) —
  **[v]** the best free source of actual historical US release *dates*. Note these are dates,
  not times; overlay the 08:30/10:00 ET convention yourself.

**Python client: use `pyfredapi`, not `fredapi`.** **[v, read both sources]**
`pyfredapi` (v0.10.2, 2025-07) exposes `get_series_vintagedates`, `get_series_all_releases`,
`get_series_initial_release` (correctly uses `output_type=4`), `get_series_asof_date`, and
passes `vintage_dates` through. Two real bugs in `fredapi` (v0.5.2, 2024-05) to know about if
you use it or lift `brianbeals`' code, which does:
- 🔴 `get_series_as_of_date()` returns **every revision up to** the date — it is literally
  `df[df['realtime_start'] <= as_of_date]`, a long revision stack, **not** an as-of snapshot.
  You must `.groupby('date').tail(1)` yourself. Skipping that silently leaks revisions into
  your backtest, and it looks like it works.
- 🔴 `get_series_all_releases()` **drops `realtime_end`** (the line is commented out in the
  source). Without it you can't distinguish "superseded" from "still current." This is exactly
  why `brianbeals/data.py` has to reconstruct `realtime_end` via
  `groupby("date")["realtime_start"].shift(-1) - 1 day`.
- Also: FRED caps `get_series_all_releases` at **2,000 vintages**, which daily series like
  `DGS10` blow through instantly — chunk by realtime window (see A3).
- ❌ `pandas_datareader.DataReader(..., 'fred')` and Nasdaq Data Link's `FRED/` tables give
  **latest release only**. Never use either for PIT.

**Philadelphia Fed RTDSM** — free, no key, no registration. **[v]**
`https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-full-time-series-history`
Each variable is one spreadsheet where **each column is a vintage** — exactly the shape you
want. **Vintage depth back to 1965:Q4 for real output**, far deeper than ALFRED (which mostly
starts 1990s–2000s). Coverage: full NIPA, CPI/PCE deflators, **RUC (unemployment), EMPLOY
(payrolls), IPT/IPM (industrial production), CUT/CUM (cap util), HSTARTS**, hours, productivity,
M1. Verified URL patterns:
```
.../data-files/xlsx/ROUTPUTQvQd.xlsx              # quarterly vintages
.../data-files/xlsx/routput_first_second_third.xlsx  # first/2nd/3rd release per obs — ideal for surprise work
```
Downsides: monthly refresh, xlsx, no API. Use it for deep history; ALFRED for everything else.

**Which series actually need vintage handling:**

| Category | Series | Handling |
|---|---|---|
| 🔴 Heavily revised | GDP/GDPC1 (3 estimates + annual + 5-yr comprehensive), **PAYEMS** (2 monthly revisions + a benchmark revision that has recently moved hundreds of thousands), INDPRO, RSAFS, PCE/PCEPI, housing starts, JOLTS | **Vintages mandatory** |
| 🔴 The silent killer | **Anything seasonally adjusted.** SA factors are re-estimated annually, so the entire history changes even when no source data does. `CPIAUCSL` is revised every year for this reason; `UNRATE`'s annual SA update revises ~5 years of history. | Vintages mandatory, or use NSA |
| 🟢 Revision-proof trick | **`CPIAUCNS` (NSA index level) is essentially never revised.** Use NSA levels and compute your own YoY. | No vintages needed |
| 🟢 Unrevised (market-based) | `DGS1MO/3MO/2/5/10/30`, `T10Y2Y`, `T10Y3M`, `DFII10`, `T5YIE`, `BAMLH0A0HYM2`, `BAMLC0A0CM`, `BAMLH0A3HYC`, `VIXCLS`, `SP500`, `DFF`/`EFFR`/`SOFR`, `DTWEXBGS`, `DCOILWTICO` | No vintages — **but still lag 1 day.** They're unrevised in value yet published with a lag and back-filled; ICE BofA OAS lands ~1 business day late. |

That last row is why your existing test is vintage-clean: everything you used lives in it.

### Economic calendar with consensus — the CESI input

| Source | Consensus field? | History | Access | Verdict |
|---|---|---|---|---|
| **`spoluan/forex-factory-scraper`** ⭐ | ✅ `Forecast` | **2010–2023, 14 yrs** | Free CSVs in-repo, ~410 KB/yr **[v: downloaded and parsed]** | **The find of the sweep.** See verification + the timezone trap directly below. |
| ForexFactory weekly JSON | ✅ `forecast`, `previous` | **This week only** | Free, no key: `https://nfs.faireconomy.media/ff_calendar_thisweek.json` **[v]** | Zero-cost forward PIT. `_nextweek`/`_lastweek`/`_thismonth` all **404** despite what blogs claim **[v]**. Cron it daily and in a year you own a clean PIT calendar. |
| **EODHD economic-events** | ✅ `estimate` | **2020→** **[d]** | `eodhd.com/api/economic-events?api_token=&from=&to=&country=US` | Most credible cheap API with a real estimate field. **Gotcha: `offset` is capped at 1000**, so you must window by date and dedupe. `demo` token is Forbidden **[v]**. |
| FMP economic calendar | ✅ `estimate` **[?]** | ~2018→ **[?]** | `financialmodelingprep.com/stable/economic-calendar` | **Unverifiable** — FMP validates the key *before* routing, so a bogus endpoint returns the identical error as a real one **[v]**. Premium tier ($29–69/mo), **not** on the free 250/day tier. Trial a key before building on it. |
| MQL5 Economic Calendar | ✅ | **~2007→**, the deepest free | `CalendarValueHistory()` via MetaTrader5 terminal + Python pkg | Best free deep history, worst dependency (needs MT5 running, Windows/Wine). Pull once, dump to parquet, done. Worth a weekend if CESI becomes central. |
| Finnhub | ✅ **[?]** | — | Premium only; free keys 403 on this route | Skip unless you already pay. |
| **Trading Economics** | — | — | ☠️ **`guest:guest` DISCONTINUED** **[v]** — returns "the guest account has been discontinued" | **Dead.** Dozens of tutorials and the official Python package are now broken. $100+/mo. |
| **Investing.com / investpy** | — | — | ☠️ **HTTP 403** on both the page and the `getCalendarFilteredData` AJAX endpoint **[v]**. `investpy` last released 2022-01, README opens with its own ⚠️ "not working fine" **[v]** | **Dead. Cloudflare won.** Do not spend a day here. |
| Alpha Vantage | ❌ actuals only **[v]** | — | 25 req/day free | Useless for surprises. |
| DBnomics / econdb | ❌ actuals only | — | DBnomics free no-key **[v]**; econdb now requires auth **[v]** | Fine as a FRED alternative for non-US; irrelevant to CESI. |

**I downloaded and parsed the 2023 file myself to confirm it's real and usable:**
```
$ curl -sL https://raw.githubusercontent.com/spoluan/forex-factory-scraper/master/datasets/forex_factory_calendar_2023.csv
http=200 bytes=419244
Date,Time,Currency,Event,Impact,Actual,Forecast,Previous,Combined DateTime
2023-01-04,11:00pm,USD,ISM Manufacturing PMI,High,48.4,48.5,49.0,2023-01-04 23:00:00
2023-01-06,9:30pm,USD,Non-Farm Employment Change,High,223K,200K,256K,2023-01-06 21:30:00
```
**370** USD/High rows in 2023, **318** with both `Actual` and `Forecast` populated — ~1.3 per
business day, ample for a daily CESI.

🔴 **Timezone trap — this will silently corrupt the index if you miss it.** The `Time` and
`Combined DateTime` columns are **not ET**. NFP prints at 08:30 ET and is stamped `9:30pm`;
ISM Manufacturing prints at 10:00 ET and is stamped `11:00pm`. That's **UTC+8** (the scraper
ran on an Asia-timezone box). So `Combined DateTime` is **one calendar day ahead** for every US
morning release. Convert with `tz_localize("Asia/Singapore").tz_convert("America/New_York")`
before you join to price dates, or every surprise will be attributed to the wrong session.

🟠 Two more: values are **strings with unit suffixes** (`223K`, `10.46M`, `0.3%`, `2.50T`) —
parse per event type, not globally. And the `Forecast` is FF's consensus *as displayed today*,
not a true point-in-time Bloomberg consensus, so back-edits would be inherited silently.
Cross-check the 2020–2023 overlap against EODHD to size that risk.

### Index rebalance / constituent changes

**🔴 Breaking change, 2026-08-11 — three days ago.** The "Selected changes to the list of S&P 500
components" table was **removed from `List_of_S%26P_500_companies`** and moved. **[v, via
revision history]** Any code doing `pd.read_html(".../List_of_S&P_500_companies")[1]` is
**broken as of this week**. (`[0]`, the constituents table, still works.)

New pages **[v]**: `Historical_components_of_the_S%26P_500` (and `_400`, `_600`).

**🔑 The trick for free ANNOUNCEMENT dates.** Wikipedia's date column is labelled *Effective
Date*. But the `Refs` column holds the S&P DJI announcement PDF, and **the announcement date is
in the URL path**:
```
https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20260731-1484374/1484374_ea5-rezi6.pdf
                                                                    ^^^^^^^^ announcement = 2026-07-31
Effective Date column                                                        = 2026-08-05
```
Parse `/announcements/(\d{8})-\d+/` out of the ref URL and you get **announcement and effective
date on the same row** — exactly the pair an index-flow strategy needs. The ~5-day gap is
typical. Fetch the **wikitext**, not rendered HTML (which strips ref URLs into footnotes):
```
https://en.wikipedia.org/w/api.php?action=parse&page=Historical%20components%20of%20the%20S%26P%20500&prop=wikitext&format=json
```
⚠️ Backtest caveat, from the editors' own HTML comment **[v]**: the changes table intentionally
contains **announced-but-not-yet-effective, future-dated rows**. Filter them out.
Coverage reaches 1976 but is **sparse before ~2000** (1,186 replacements occurred 1963–2014;
far fewer are tabulated). spglobal.com itself is Akamai-403 to scripts **[v]** — harvest the
URLs from Wikipedia instead.

**`fja05680/sp500`** — 908★, updated today **[v]**. Best free survivorship-free S&P 500
membership panel. `sp500_ticker_start_end.csv` is the most directly usable file and **correctly
handles re-entry** (verified: `AAL,1996-01-02,1997-01-15` and `AAL,2015-03-23,2024-09-23` as
separate rows). Delisted names carry a `-YYYYMM` suffix. Starts 1996-01-02. **Effective dates
only, no announcement column** — join to Wikipedia for the announce leg.
`hanshof/sp500_constituents` (28★) is a smaller sibling; keep as a cross-check.

**🔴 Russell reconstitution changed regime in 2026.** **[v]**
`https://www.lseg.com/en/ftse-russell/russell-reconstitution` (the old
`ftserussell.com/index-reconstitution` URL now 404s). **Russell US Indexes moved from ANNUAL to
SEMI-ANNUAL reconstitution starting 2026.** Any recon-flow strategy calibrated on the old
once-a-year June event needs re-specification — the second window changes the turnover profile
and probably dampens the classic June effect. 2026 calendar: rank day **Apr 30** → prelim lists
**May 22**, updated **May 29 / Jun 5 / Jun 12 / Jun 18** → effective after the close **Jun 26**.
Those staged prelim dates *are* the announcement dates, and unlike S&P they're pre-scheduled —
which is the whole point of the Russell trade. Free historical add/delete PDFs follow a stable
pattern, so **prior years are likely still on the CDN**:
```
https://www.lseg.com/content/dam/ftse-russell/en_us/documents/other/ru3000-additions-20260626.pdf
                                                               .../ru3000-deletions-20260626.pdf
```
Walk historical recon dates against that template to assemble a multi-year history for free
(you'll be parsing tables out of PDF).

### Survivorship-free prices / PIT fundamentals

| Source | Delisted? | History | Cost | Verdict |
|---|---|---|---|---|
| **Tiingo** | ✅ retains delisted — unusual at this price | 1962→ many US names | ~$10/mo **[?]** | **Best $/value for prices.** You already use it (per `MEMORY.md`, it solved survivorship for the insider work). |
| **Sharadar SF1 + SEP** (Nasdaq Data Link) | ✅ explicitly | 1998→ | ~$150/mo bundle **[?]** | **Best cheap PIT fundamentals.** The `datekey` field = SEC filing date is what makes it genuinely PIT; most cheap vendors give fiscal-period-end only, leaking 40–90 days. |
| **EODHD** | ✅ dedicated delisted API | 30+ yrs | ~$20–100/mo **[?]** | Best single-vendor answer if you want prices + fundamentals + index constituents + econ calendar under one key. Quality a notch below Sharadar. |
| **Norgate** | ✅ | 1950→ | ~$70–90/mo **[?]**; ⚠️ pricing URL 404s, site restructured **[v]** | **The right answer if PIT index membership is the core signal** — historical constituent membership is a first-class feature. Desktop-updater model, Windows-centric, not REST. |
| SimFin | ⚠️ weak on dead names | ~2007→ | ~€20–50/mo **[?]**, pricing page 500s **[v]** | Nice bulk CSVs; survivorship coverage is the weak point. |
| Alpaca | ⚠️ weak | **2016→ only**; free tier IEX-only + 15-min delay **[d]** | free / $99 SIP | Fine as broker + live data, poor as a research DB — the 2016 start kills a decade-scale swing backtest. |
| polygon.io → **rebranded "Massive"** **[v]** | reference API lists inactive tickers, no PIT membership | ~2003→ paid; free = 2yr EOD, 5 req/min | ~$29–199 **[?]** | Overkill for 5–21 day holds. Note the rebrand — old doc links are drifting. |
| WRDS (CRSP + Compustat) | ✅ definitively, with delisting returns | 1925→ | institutional only | If you have *any* university/alumni affiliation, use this and ignore the rest of this table. |

**Two fundamentals-side PIT traps, vendor-independent:**
1. Use the **filing date** (Sharadar `datekey`, Compustat `RDQ`, SimFin `publish_date`), never
   fiscal period end. A Dec-31 period end wasn't knowable until late February.
2. **Restatements.** Almost no cheap vendor stores the *originally filed* figure — they
   overwrite with restated values. This is the fundamentals-side analogue of the macro-vintage
   problem, and only Compustat Point-in-Time truly solves it.

### Landmines this sweep found (things that broke recently)
- Wikipedia S&P changes table **relocated 2026-08-11** → breaks `read_html(...)[1]`.
- Russell recon **annual → semi-annual, from 2026**.
- Trading Economics **`guest:guest` discontinued** → the official Python package and every
  tutorial using it are dead.
- Investing.com **hard-403**; `investpy` unmaintained since 2022.
- polygon.io **rebranded to Massive**.
- `fredapi.get_series_as_of_date()` returns an **un-deduplicated revision stack** — leaks
  revisions unless you `.groupby('date').tail(1)`.
- EODHD econ-events **`offset` capped at 1000** — window by date or you'll silently truncate.

---

## WHAT I'D DO NEXT, IN ORDER

1. **Signal #0** — re-run the existing macro panel as a date-grouped panel regression with
   Newey-West at ≥h lags. One day. Converts a soft null into a hard one and fixes the
   instrument for everything after.
2. **Signal #1** — rate-residual sectors and the β-neutral KRE/XLRE pair. Uses only data you
   have. This is the one that exploits your *strongest* measured result rather than discarding it.
3. **Fork `spoluan/forex-factory-scraper` today** (it's 11★ and unmaintained) and start the
   ForexFactory weekly-JSON cron. Costs an hour; the cron only accrues value with time.
4. **Signal #2** — build the CESI. This is the genuine open gap: zero public replications, and
   it is the one macro variable that is neither a market price you've already falsified nor a
   revised series you can't trust.
5. **Signal #3** — credit-spread *state* percentiles, including the conditional-beta question.
6. Only then **Signal #4** (vintage-correct slow macro), and run it as an **A/B against
   latest-revision data** so the effort produces a methodological result regardless of sign.

Adopt `eslazarev/purged-cross-validation` for the statistics before starting #4, and lift
`brianbeals/sector-rotation-screener/data.py` (MIT) for the ALFRED layer.
