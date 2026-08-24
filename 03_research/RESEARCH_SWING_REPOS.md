# Swing-Horizon Edge Sweep: Public GitHub Repos

Scope: US equities/ETFs, 2-day to 8-week holds. Themes: sector rotation, market regime
detection, factor timing, options overlays. Date of sweep: 2026-08-06.

Method: GitHub repo-search API + web search, then **reading the actual source** (raw
file fetches) for every repo I make a claim about. Where I could not read the code I say
so explicitly. README performance claims are treated as marketing until the code says
otherwise.

Headline: **the two most rigorously-built repos in this space both publish a NULL
result on the exact strategy most people want to trade (sector momentum rotation).**
That is the single most valuable finding here — it saves a full replication cycle. The
things that *do* survive scrutiny are all regime/defense overlays, not return-seeking
rotation signals.

---

## TIER A — Defensible methodology, worth replicating

### A1. `hadan-aslan/quant-edge` — 12-1 sector momentum, published NULL
- URL: https://github.com/hadan-aslan/quant-edge
- Stars: 0 (pushed 2026-07-22). Ignore the star count; this is the best-built
  backtest I found in the whole sweep.
- **Signal (read from `src/quant_edge/signals.py`):** at month `m`, rank the 9 original
  SPDR sector ETFs (XLB XLE XLF XLI XLK XLP XLU XLV XLY) by compounded return over
  months `[m-12, m-1]` (log-returns summed then `expm1`). Long the top 3, equal weight.
  `n_short` long-short variant exists but is not the reported run.
- **Backtest period:** 2000-03 to 2026-07, 317 months. Monthly rebalance.
- **Costs:** yes — 10 bps per unit of *one-way turnover*, and turnover is computed
  against **drifted** prior weights (`_drift_weights`), not a naive weight diff. That is
  the correct way and most repos get it wrong (understates cost).
- **Train/test:** IS/OOS split at 2013-01-01, but explicitly used as a *stability check
  only* — parameters are identical on both sides and come from Jegadeesh & Titman, not
  from a grid search. `NOTES.md` says the author considered grid-searching and reporting
  only OOS, and rejected it as "data-snooping with extra steps." I believe them; there is
  no sweep artifact in the repo.
- **Look-ahead:** deliberately over-conservative. `signals.py` builds `weights.loc[m]`
  from data through `m-1`, then `backtest.py` shifts weights forward *again* one month.
  `tests/test_no_lookahead.py` re-runs the pipeline on truncated prefixes and demands
  bit-identical historical output — a hidden `.shift(-1)` would fail the test.
- **Result:** momentum net Sharpe **0.53** vs equal-weight-9-sectors **0.56** vs SPY
  **0.50**. Fama-French+Mom alpha = **-0.20%/yr, t = -0.15** (Newey-West 3 lag, n=315).
  Momentum loading 0.215, market beta 0.930, R² 0.799.
- **Red flags (disclosed by the author, and I agree):** universe is today's surviving
  SPDR sectors (not point-in-time GICS); benchmarks are gross of costs while the strategy
  is net (a disclosed asymmetry, and note it makes the strategy look *worse*, so it does
  not flatter); no slippage/impact model; 9 assets is a thin cross-section.
- **Verdict:** REPLICATE THIS AS YOUR BASELINE, not as a strategy. It is the honest
  null you should have to beat before you spend time on any sector-rotation idea.

### A2. `27donworthp/sector-momentum` — same null, independently, plus a param sweep
- URL: https://github.com/27donworthp/sector-momentum
- Stars: 0 (pushed 2026-08-01).
- **Signal (`momentum/backtest.py`):** `signal_t = P_{t-skip} / P_{t-lookback} - 1`,
  equal-weight top-N, monthly, on **11** sector ETFs (adds XLRE, XLC) 2000-2026.
  Optional `abs_momentum` overlay (hold only names with positive momentum, else cash).
  Timing is standard and correct: `gross = (weights.shift(1) * returns).sum(axis=1)`;
  costs from turnover vs *drifted* weights, charged to month `t+1`.
- **Costs:** 10 bps one-way. **Train/test:** none, but a 40-cell parameter sweep is
  committed (`results/parameter_sweep.csv`) which is more useful than a split.
- **Result (`results/summary.csv`):** momentum net Sharpe **0.635**, gross 0.671,
  equal-weight sectors **0.658**, SPY 0.612. Ann. turnover 545%.
- **The sweep is the real content.** Across 40 (lookback, skip, top_n) combos:
  median Sharpe **0.625**, best **0.732** (lookback=12, skip=0, top_n=5), worst 0.402
  (lookback=3). The equal-weight benchmark is 0.658. **Most of the parameter space loses
  to equal-weight, and the best cell beats it by 0.07 Sharpe on 40 trials — that is
  noise.** This is the cleanest possible demonstration that sector momentum is not a
  real edge.
- **One genuine, replicable nuance worth keeping:** at the sector-ETF level, `skip=0`
  beats `skip=1` consistently (12-0 Sharpe 0.732 vs 12-1 ~0.63). The short-term reversal
  that motivates the skip in single-stock momentum does **not** appear in sector indices.
  If you build anything sector-momentum-flavored, do not skip the last month.
- **Red flags:** same survivorship caveat (today's 11 SPDRs); `results/` are committed
  from a single full-sample run; no formal multiple-testing correction on the sweep.
- **Verdict:** replicate the sweep, then stop chasing sector momentum.

### A3. `Morwane/vix-vol-carry` — VIX term-structure carry with a crash gate
- URL: https://github.com/Morwane/vix-vol-carry
- Stars: 1 (pushed 2026-06-07).
- **Signal (`src/strategy.py`, read in full):**
  - `contango = VIX3M/VIX - 1` (>0 = contango)
  - `calm = 1 if VIX <= VIX3M else 0`  ← this is the crash filter
  - `exposure = -min(contango / 0.10, 1) * calm`, i.e. short the VIX front future,
    sized linearly in contango, capped at full size when contango >= 10%, and **flat
    whenever the curve inverts**
  - `exposure.shift(1)` applied to a roll-aware front-future log return; 5 bps cost on
    exposure change; PnL vol-targeted to 10% annual.
- **Backtest:** 2010-01 to 2026-05 (4088 days), daily.
- **Costs:** yes, 5 bps on `|Δexposure|`. **Look-ahead:** signals `shift(1)`; an
  automated `quant_checks` asserts the first return is NaN. Clean.
- **Result:** gated carry Sharpe **1.26**, CAGR 12.8%, maxDD -10.4%. Naive always-short
  Sharpe 1.37, maxDD -18.2%. Subperiods: 1.44 / 1.36 / 1.05 / 1.07. Block bootstrap
  (2000x, 21-day blocks) 90% CI on Sharpe **[0.81, 1.65]**.
- **Red flags — read these before you get excited:**
  1. **The filter does not raise Sharpe.** Naive short-vol beats it 1.37 vs 1.26. The
     filter buys drawdown reduction (-18% → -10%) and crisis containment
     (COVID -12.6% → -2.3%), not return. The author says this plainly.
  2. **Sample starts 2010** — excludes 2008. A short-vol book with no GFC in sample is
     structurally flattered.
  3. **Fitted parameter:** the roll/splice detector thresholds (`r_normal > 0.05 &
     |r_splice| < 0.03`) are, per the code comment, "CALIBRATED so the detector fires
     ~once a month." That is a full-sample calibration on the return series itself.
     `contango_full = 0.10` is also a chosen constant.
  4. **Data is LSEG (paid).** VXc1/VXc2 continuation series are committed to the repo
     though, so it is reproducible as-is even if you can't refresh it.
  5. Daily skew stays -1.1 to -1.6 with fat tails either way — the filter manages the
     *path*, not the single-day tail.
- **Verdict:** do not replicate the short-VIX-futures book. **Do lift the `VIX <= VIX3M`
  gate** as a standalone, zero-parameter, free-data regime filter and test it on
  everything else you trade (see Signal #1 below).

### A4. `toddaerickson/dual-momentum` — 3-stage TAA with a credit-spread regime overlay
- URL: https://github.com/toddaerickson/dual-momentum
- Stars: 0 (pushed 2026-04-08). Streamlit dashboard + launchd-style scheduled runs.
- **Signal (read `signals.py`, `config.py`, `backtest.py`):**
  - **Stage 1 gate:** if `max(12m return of SPY, EFA) <= 12m return of BIL` → 100% SHY, stop.
  - **Stage 2 selection:** rank SPY EFA EEM VNQ DBC GLD by **vol-adjusted 12-1**
    momentum (normalize each to 10% target vol before ranking). Terciles: top 2 → 30%
    each, middle 2 → 20% each, bottom 2 → 0%. Hysteresis: don't trade on a 1-rank change.
  - **Stage 3 risk budget:** credit regime from FRED. Primary =
    `BAMLH0A3HYC - BAMLH0A1HYBB` (CCC OAS minus BB OAS). Secondary = `BAMLH0A2HYB`
    (single-B OAS). Both converted to **expanding-window percentile ranks**. Regime:
    <25 TIGHT, 25-60 NORMAL, 60-85 STRESSED, >=85 CRISIS. Single-B >= 75th pct escalates
    one step (never de-escalates). If single-B widens >100bps in 3 months →
    WIDENING_FAST → 100% SHY override. Risk budget: TIGHT/NORMAL 100% risky;
    STRESSED 70% risky + 30% SHY; CRISIS 50% risky + 30% SHY + 20% ANGL.
- **Costs:** `TRANSACTION_COST_BPS = 5` per changed position, each way. Monthly, last
  business day.
- **Whole-dataset normalization:** **correctly avoided.** `_expanding_percentile_rank()`
  slices `series[series.index <= as_of]` before ranking. This is the single most common
  way credit-regime backtests break and this repo gets it right.
- **Inception honesty:** `config.py` hardcodes ETF inception dates and explicitly falls
  back to GEM-only before 1997 (HY OAS start) and before 2001 (EFA). No fake pre-history
  for EEM/VNQ/DBC/GLD/ANGL. The "1980-present" claim in the README is index-proxy
  (^GSPC + FRED rates) for the Stage-1-only variant, not the full model.
- **Red flags:** the percentile thresholds (25/60/85, 75/90) and the risk budgets
  (100/70/50, 30% SHY, 20% ANGL) are hand-chosen with no stated derivation, and the
  dashboard ships a "Parameter Sensitivity" sweep view — meaning they *did* sweep, and
  no OOS split is reported. No committed backtest results file, so I could not verify
  any performance number; the repo publishes signals, not a validated equity curve.
  ANGL inception 2012 means the CRISIS branch has effectively one live observation (2020).
- **Verdict:** the **CCC-BB expanding-percentile credit regime** is the reusable piece
  and it is built correctly. Extract it, ignore the rest of the stack until you've
  tested it standalone.

### A5. `oronimbus/tactical-asset-allocation` (pyTAA) — best *spec catalog* in the sweep
- URL: https://github.com/oronimbus/tactical-asset-allocation
- Stars: 51 (pushed 2024-12-23). Author labels it WIP.
- `src/pytaa/strategy/README.md` is a precise, formula-level spec for **16** published
  TAA strategies (Ivy, Robust AA, Diversified GEM, VAA-G4/G12, Kipnis DAAA, Generalized
  Protective Momentum, Trend is Our Friend, Meb Faber GTAA, DAA, PAA, Adaptive AA, GEM,
  Quint Switching, Composite Dual Momentum, HMM Regime Switching, Robeco DSAA). Each
  gives universe, weights, and the exact rule. This is the highest-value *reference*
  document I found.
- `src/pytaa/strategy/signals.py` code checked: `classic_momentum`, `momentum_score`
  (the 13612W: `12·P/P₋₁ + 4·P/P₋₃ + 2·P/P₋₆ + P/P₋₁₂ - 19`), `sma_crossover`,
  `protective_momentum_score`. All computed on `resample("BME").last()` monthly prices
  with backward-looking shifts only — no look-ahead in the signal layer.
- **RED FLAG, important:** the Sharpe/MaxDD figures quoted next to each strategy in that
  README (SR 0.8-1.1, MDD 9-19%) are **not** produced by this repo. They are the
  published/AllocateSmartly numbers, i.e. the strategy authors' own in-sample results for
  rules that were designed with full knowledge of the 2000-2015 sample. Treat every one
  of them as in-sample. The repo itself commits no backtest output.
- **Verdict:** use as a spec source, never as an evidence source.

### A6. `penny-vault/vigilant-asset-allocation` + `penny-vault/defensive-asset-allocation`
- URLs: https://github.com/penny-vault/vigilant-asset-allocation ,
  https://github.com/penny-vault/defensive-asset-allocation
- Stars: 0 each (pushed 2026-07-15). Go, not Python — but the `README.md` in each is the
  cleanest unambiguous statement of Keller's rules I found anywhere, including the exact
  breadth-momentum arithmetic and the binding ETF inception constraints.
- VAA README even flags the honest cost: "Allocate Smartly reports ~700% annual turnover
  for the aggressive variant" and notes the 13612W signal weights the 1-month return
  **12x** the 12-month return, i.e. VAA is far more reactive (and more expensive) than
  it looks.
- No backtest output committed. Use for spec only.

### A7. `lambdaclass/options_portfolio_backtester` — the serious options engine
- URL: https://github.com/lambdaclass/options_portfolio_backtester
- Stars: **256** (pushed 2026-07-28). Rust compute core, Python API.
- Contract-level inventory, Greeks-aware risk, explicit `execution/cost_model.py`,
  `execution/fill_model.py`, `execution/sizer.py`. Presets include Spitznagel-style
  deep-OTM put tail hedge and near-ATM put protection, with two distinct budget framings
  (external budget vs allocation-reducing) documented separately — a distinction most
  options backtests botch.
- Reproducibility is unusually strong: canonical SPY parquets are **pinned by SHA-256**
  in `scripts/fetch_data.py` and `fetch_data.py verify` proves byte-identity.
- **This is also the best free options data source in the sweep — see Data section.**
- **Red flag:** the sample `results.summary()` in the README shows `sharpe: 0.72,
  max_drawdown: -46.4` for the Spitznagel framing — i.e. the tail hedge does not fix
  drawdown in that configuration. Read the framings doc before drawing conclusions.
- **Verdict:** use as the execution layer for any options overlay you build on top of a
  regime signal. Do not use it as a source of a validated strategy.

---

## TIER B — Interesting, but you must rebuild the evidence yourself

### B1. `brianbeals/sector-rotation-screener`
- URL: https://github.com/brianbeals/sector-rotation-screener — 0 stars, pushed 2026-08-02.
- **Signal (`scoring.py`, `backtest.py` read):** composite score =
  `0.25·seasonality + 0.40·cycle_fit + 0.35·relative_strength`, monthly, hold equal-weight
  top-3 among sectors scoring >= 65, park in SPY if none qualify. Relative strength is a
  weighted blend of trailing sector-minus-SPY returns across several windows, squashed
  through `50 + 50·tanh(diff/0.10)`, plus an "RS inflection" term (last 21d RS minus prior
  21d RS) — explicitly designed to reward early rotation over momentum chasing.
- **Genuinely good:** the backtest uses **FRED ALFRED vintage macro** to classify the
  economic-cycle phase as it was *published* at each historical month-end. Almost nobody
  does this. Price frames are truncated to `<= asof` at every step. Costs: 1 bp turnover.
- **Red flags:**
  1. **Seasonality is 25% of the score and is almost certainly noise.** It is the mean
     return of a single calendar month across ~15-25 observations per sector. n=20 monthly
     returns has a standard error of ~1.2%/month; the score can't distinguish signal from
     nothing.
  2. `CYCLE_FAVORED` — the map of which sectors do well in which cycle phase — is textbook
     lore hardcoded as a prior. It is hindsight in the strategy's DNA even though the
     phase *classification* is point-in-time.
  3. Weights (25/40/35) and thresholds (Buy 65 / Avoid 40) are hand-picked with no
     disclosed derivation and no OOS split.
  4. 1 bp cost is optimistic even for SPDRs once you include spread crossing.
  5. Only 15 years, monthly → ~180 observations, ~60 rebalances of substance.
- **Verdict:** steal the ALFRED vintage-macro pattern (that is a real methodological
  asset). Do not trust the composite score.

### B2. `aladinbouddat/PEAD-Strategy`
- URL: https://github.com/aladinbouddat/PEAD-Strategy — 0 stars, single commit 2025-06-22.
  Bachelor thesis code (thesis PDF included).
- **Signal (`src/pead_strategy.py`, 724 lines, read):** IBES `suescore` (standardized
  unexpected earnings). Long if SUE > **0.635**, short if SUE < **-3.78**. Hold longs
  **85 calendar days**, shorts **9 calendar days**. S&P 500 constituents from CRSP,
  1994-01 to 2023-12, 95,748 announcements / 1,337 stocks.
- **Costs: genuinely good.** Real CRSP bid-ask spread median, IB commissions, third-party
  + pass-through fees, SEC regulatory selling fees on shorts, and a 25bps/yr stock borrow
  cost prorated over the short holding period. This is the most realistic cost model in
  the whole sweep.
- **RED FLAGS — this one is tuned:**
  1. Thresholds `+0.635 / -3.78` are wildly asymmetric and absurdly precise. No
     theoretical basis; these are optimizer output.
  2. Holding periods 85d long / 9d short, also asymmetric and precise. A commented-out
     `days_short = 10` sits right next to the live `days_short = 9` — direct evidence of
     a parameter search.
  3. **No train/test split at all.** Everything is full-sample.
  4. The engine is **cash-constrained and sequential** (`if self.cash >= order_value +
     cost`), so which trades get taken depends on path and on the arbitrary $100k starting
     capital. That is not a clean signal test.
  5. The headline "Sharpe Ratio portfolio: 0.0488" is a **daily** Sharpe presented without
     annualization (×√252 ≈ 0.77). Easy to misread as catastrophic or to misquote.
  6. Requires WRDS (IBES + CRSP + Compustat) — not free, and the `data/` dir ships empty.
- **Verdict:** the PEAD *effect* is real and well-documented academically. This *repo's*
  parameters are fitted. If you build PEAD, use symmetric deciles/quintiles of SUE and a
  fixed 60-day hold, and split your sample. Do borrow the cost model.

### B3. `0x596173736972/MarketRegimeTrader`
- URL: https://github.com/0x596173736972/MarketRegimeTrader — 16 stars, pushed 2025-05-27.
- The only regime repo I found with a **real** walk-forward harness:
  `backtesting/walk_forward_analyzer.py` fits the HMM on a rolling 12-month training
  window and predicts on the following 3-month test window, stepping 1 month. Features are
  prepared separately per window. That is the correct structure and it is rare.
- **RED FLAG that kills it as an evidence source:** it ships 8 regime strategy types plus
  an `auto_strategy_generator.py` (35KB) and Optuna hyperparameter optimization with
  `n_trials=50` *inside* each walk-forward window. The multiple-testing surface is
  enormous and there is no deflated-Sharpe / PBO correction anywhere. It also bolts on
  topological data analysis (`tda/`), which multiplies the search space again.
- No committed backtest results to evaluate. `_regime_momentum_strategy` iterates rows and
  I could not confirm a signal lag on the regime series within the strategy layer (the lag
  may exist only at the engine boundary).
- **Verdict:** harvest the walk-forward scaffolding pattern. Do not believe any number it
  produces without running your own PBO.

### B4. `roymoon0122-commits/HMM-regime-alpha-longshort-trading-system`
- URL: https://github.com/roymoon0122-commits/HMM-regime-alpha-longshort-trading-system
  — 1 star, pushed 2026-07-10.
- Best backtest *hygiene writeup* of any regime repo: explicit train/test dates, warm-up
  bars excluded from OOS stats, `signal at bar t → executed at open[t+1]`, rolling CAPM
  beta from **prior daily closes only**, SPY used as benchmark not as a traded hedge,
  slippage sensitivity table (0/2/5/10bp), and a second Sharpe column at rf=4.5%.
  Signal is continuous: `P(Bull) - P(Bear)` from a logistic meta-model over HMM posteriors.
- **RED FLAGS that make the result unusable:**
  1. **Universe is "49 liquid U.S. equities" chosen in 2026.** No point-in-time selection
     rule is given. That is a hindsight-picked universe — the single most powerful way to
     manufacture a long-short Sharpe.
  2. **Period is 2024-01 to 2026-05 — 2.4 years.** Sharpe 3.41 over 2.4 years on a
     hand-picked 49-name basket is not evidence.
  3. 30-minute bars — below your swing horizon anyway.
  4. Author labels the numbers "gross research diagnostics, not deployable net
     performance," which is honest, but the README leads with Sharpe 3.41.
- **Verdict:** copy the hygiene checklist, discard the result.

---

## TIER C — Broken. Do not waste replication time.

### C1. `taylorjmellon/market-regime-detection` — TEXTBOOK DOUBLE LOOK-AHEAD
- URL: https://github.com/taylorjmellon/market-regime-detection — 2 stars.
- `src/hmm_model.py`:
  ```python
  model = GaussianHMM(n_components=n_states, covariance_type='full', ...)
  model.fit(data)               # fit on the ENTIRE sample
  hidden_states = model.predict(data)   # Viterbi path over the ENTIRE sample
  ```
  The regime label at date *t* is decided with knowledge of every observation after *t*.
- `src/backtest.py` then does:
  ```python
  df["Strategy_Return"] = df["Return"] * df["Exposure"]
  ```
  **No `.shift()`.** Exposure on day *t* multiplies day *t*'s own return, on top of the
  full-sample Viterbi labels. Two independent look-aheads stacked. No costs. No train/test.
- This is the canonical broken-HMM pattern. **Any repo whose HMM equity curve looks
  beautiful is doing this** — check for `fit(all_data)` + missing `shift(1)` first, it
  takes 30 seconds and disqualifies most of the category.

### C2. `garroshub/Quant_Sector_Rotation_Strategy` — hindsight universe + parameter soup
- URL: https://github.com/garroshub/Quant_Sector_Rotation_Strategy — 11 stars, Streamlit
  demo, README claims 18.5% CAGR / Sharpe 1.45 / IR 0.82 for 2010-2024.
- `model.py` read. Findings:
  1. **Universe is 6 sector ETFs: XLK, XLV, XLE, XLF, XLI, XLY.** XLP, XLU, XLB, XLRE and
     XLC are simply absent. Dropping the defensive laggards from a long-only momentum
     universe *after* observing 2010-2024 is a hindsight-selected universe, and it alone
     can explain the entire claimed outperformance.
  2. **~8 free parameters, none justified, no split:** `WINDOW=120`, `MA_WINDOWS=[10,40,140]`,
     `BASE_THRESHOLD=0.1`, `VOL_WINDOW=30`, `TRAILING_STOP=0.05`,
     `MAX_DRAWDOWN_STOP=0.20`, `VIX_HIGH_THRESHOLD=25`, `VIX_EXTREME_THRESHOLD=50`.
     An `optimize.py` sits in the repo.
  3. The "MA Energy" proprietary indicator is just `(price - SMA(120)) / SMA(120)`.
  4. `vix_level = data.loc[current_date, 'VIX']` — the same-day VIX close drives the
     same-day target weights; no lag is applied at the signal level.
  5. Dead code in the stop-loss loop (`if drawdown < -MAX_DRAWDOWN_STOP: continue` inside
     a loop that does nothing after it) — the stop is not actually implemented.
  6. `START_DATE = '2000-01-01'` in code vs "2010-2024" in the README. The claimed numbers
     do not correspond to the committed configuration.
  7. No transaction costs anywhere in `model.py`.
- **Verdict:** discard entirely.

### C3. Category warning — the HMM regime-detection genre
I sampled `Sakeeb91`, `taylorjmellon`, `vigp17`, `francescodemarte`, `yorch`,
`shortthirdman`, `theo-dim`, `tanmaya-lodhia`, `KabirUberoi` variants. Every one that
publishes an equity curve either (a) fits the HMM on the full sample, (b) applies the
regime to the contemporaneous return with no lag, or (c) both. `francescodemarte` ships a
`99_validation.ipynb` which suggests some self-awareness, but the repo is notebooks-only
with a 1.9MB output-laden `.ipynb` and no committed backtest module. The one structural
exception is B3 above. **Assume broken until you've grepped for `shift`.**

### C4. Others checked and rejected quickly
- `Dreeseaw/Sector-Rotation-RNN` — RNN predicting next-week sector returns; no cost model,
  no OOS discipline, tiny sample. Skip.
- `ShauryaTathgir/RelativeRotationSwingTrading` — RRG visualization + TD Ameritrade API;
  the "backtest" is a plot, and asset inclusion is gated on VIX thresholds chosen after
  the fact. Skip.
- `AleksLi1/Accelerating_Dual_Momentum` (4 stars) — `functions.py` is 374 bytes; the whole
  thing runs off a committed `final.csv`. Not auditable. Skip.
- `alexjansenhome/GEM` (60 stars, last touched 2017) — the most-starred GEM implementation,
  but it is a monthly signal calculator, not a validated backtest, and it is 9 years stale.
  Use pyTAA's spec instead.
- `segobooking-finanz/momentum-sector-rotation` — momentum vs mean-reversion on sector ETFs,
  results committed as PNGs only, no metrics CSV. Redundant with A1/A2 which are better built.

### C5. Ghost repo — do not chase
`philippdubach/options-data` ("Historical Options Chain Data for 100+ US Equities,
2008-2025") appears in search results and is cited widely, but **it no longer exists** —
the GitHub repo and its CDN both went down in 2026 (confirmed: the user's repo list has no
such repo, and lambdaclass's `data/DATA_NOTICE.md` documents the disappearance). The data
survives only as the lambdaclass mirror below.

---

## FREE DATA useful for swing backtesting

| Source | What | Notes |
|---|---|---|
| **`lambdaclass/options_portfolio_backtester`** (256★) | **EOD US options chains: SPY 2008-2025, QQQ 2011-2025, IWM 2008-2025**, as parquet, SHA-256 pinned | The best free options history I found. Fetch with `python scripts/fetch_data.py all --symbols SPY`. Redistributed mirror of the now-dead philippdubach dataset; provenance and takedown posture documented in `data/DATA_NOTICE.md`. Known gap: IWM `underlying.parquet` has all-NaN `adjClose`. |
| **OptionsDX** (free registration) | EOD option chains 2010+ for major ETFs/indices | The clean-license alternative. lambdaclass ships `scripts/convert_optionsdx.py` to convert into its schema. No 2008-2009 (no GFC). |
| **FRED / ALFRED** (free API key) | `BAMLH0A3HYC` (CCC OAS), `BAMLH0A1HYBB` (BB OAS), `BAMLH0A2HYB` (single-B OAS), `BAMLH0A0HYM2` (HY composite, from 1997-01), T10Y2Y, plus **ALFRED vintages** | ALFRED is the one that matters — it gives you macro data *as published at the time*, which is the only way to backtest a cycle/recession overlay without look-ahead. `brianbeals/sector-rotation-screener/data.py` has a working ALFRED vintage fetcher you can lift. |
| **Ken French Data Library** | Mkt-RF, SMB, HML, Mom monthly factors | Free, and `hadan-aslan/quant-edge/src/quant_edge/data.py` has a live fetcher that raises rather than silently fabricating on failure — copy that error handling. |
| **Yahoo (`yfinance`)** | `^VIX`, **`^VIX3M`**, `^VIX9D`, `^VVIX`, all sector ETFs | `^VIX3M` is free and is all you need for the term-structure gate (Signal #1). You do **not** need the LSEG futures data to run the regime filter, only to run the futures carry book. |
| **`Morwane/vix-vol-carry/data/raw_prices/`** | Committed CSVs: `_VIX`, `_VIX3M`, `_VIX9D`, `_VVIX`, `VXc1`-`VXc3`, SPY, 2010-2026 | The VIX **futures continuation series** (VXc1-3) are the hard-to-get part and they are committed to the repo. Static, won't refresh, but instantly usable. |
| **`27donworthp/sector-momentum/results/`** | `monthly_returns.csv`, `weights.csv`, `parameter_sweep.csv` | Pre-computed sector momentum monthly returns 2000-2026 — useful as a ready-made benchmark series to test any new signal against without re-running anything. |
| **`aladinbouddat/PEAD-Strategy/src/pead_strategy.py`** | Not data, but a real cost model | CRSP-derived median spread + IB commissions + SEC fees + 25bp/yr borrow. Lift the `get_transaction_cost()` function. |
| Earnings dates | **No good free source found in this sweep.** | Every PEAD repo worth anything uses WRDS/IBES. The Robinhood MCP `get_earnings_calendar` you already have wired is probably your cheapest path. |
| Breadth (% above 200dma, A/D) | **No good free US source found.** | `BennyThadikaran/eod2` has a `market_breadth_sync.py` computing A/D line, % above 50/200dma, McClellan, net 52wk highs — but it is **NSE India only**. You'd need to rebuild it on a US universe yourself. |

---

## RANKED: signals worth backtesting, stated precisely enough to code

Ordered by (evidence quality × implementability with free data × fit to 2d-8wk horizon).

### 1. VIX/VIX3M term-structure regime gate — zero parameters, free data
```
calm_t = 1 if VIX_t <= VIX3M_t else 0        # ^VIX, ^VIX3M from yfinance
position_t = base_strategy_t * calm_{t-1}     # note the lag
```
Backwardation (VIX > VIX3M) marks the stress regime. Evidence (A3): as an overlay on a
short-vol book 2010-2026 it cut maxDD -18% → -10% and turned COVID -12.6% → -2.3%, without
adding return (Sharpe 1.37 → 1.26). **Test it as a gate on every book you run, not as a
strategy.** The honest question to answer: does it improve Calmar on your existing
equity/sector positions, or does it just cost you re-entry? Free, no fitting, one line.

### 2. Keller 13612W breadth momentum with a canary universe (DAA)
```
Z(asset) = 12·(P₀/P₁) + 4·(P₀/P₃) + 2·(P₀/P₆) + (P₀/P₁₂) - 19    # P₃ = price 3 months ago
canary = {VWO, BND};  n = count(Z(canary) < 0)
risky  = {SPY,IWM,QQQ,VGK,EWJ,VWO,VNQ,GSG,GLD,TLT,HYG,LQD}
protective = {SHY, IEF, LQD}
n = 2 → 100% best-Z protective
n = 1 → 50% best-Z protective + 50% equal-weight top-6 risky by Z
n = 0 → 100% equal-weight top-6 risky by Z
Rebalance last trading day of month; hold to next month-end.
```
Spec verified across two independent sources (A5, A6). **Backtest window is capped at
~2007 by HYG/GSG inception — do not let anyone show you a longer one.** Expect high
turnover: the 1-month term carries 12× the weight of the 12-month term. VAA-G12 is the
same machinery with `CBF = min(1, n_bad / 4)` blending instead of the canary. Note every
published Sharpe for these (0.9-1.1) is the authors' in-sample number.

### 3. CCC-BB credit-spread regime, expanding-percentile
```
spread_t   = FRED BAMLH0A3HYC - FRED BAMLH0A1HYBB        # CCC OAS - BB OAS
pctl_t     = percentile_rank(spread_t within spread[:t])  # EXPANDING, never full-sample
regime: <25 TIGHT | 25-60 NORMAL | 60-85 STRESSED | >=85 CRISIS
escalate one step if BAMLH0A2HYB pctl >= 75 (never de-escalate)
override: if BAMLH0A2HYB widens > 100bps over 3 months → 100% cash
risk budget: TIGHT/NORMAL 1.0 | STRESSED 0.7 | CRISIS 0.5
```
Free (FRED), daily, available from 1997. The expanding-window percentile is the correct
construction and A4 implements it correctly — the whole point is that a fixed bps threshold
drifts as HY index composition changes over decades. **The thresholds are the untested
part**: 25/60/85 and the 1.0/0.7/0.5 budgets are hand-set. Test threshold sensitivity
before trusting it, and test the credit gate against the simpler VIX gate (#1) — they may
be the same trade.

### 4. Generalized Protective Momentum — correlation-penalized momentum
```
r_i  = mean over t ∈ {1,3,6,12} months of (P₀/P_t)
ρ_i  = 12-month correlation of asset i's daily returns with the equal-weight
       basket of all risky assets
M_i  = r_i · (1 - ρ_i)
n    = count(M_i > 0)
n <= 6  → 100% into the safety asset with the largest M (BIL or IEF)
n >  6  → (12-n)/6 into safety, remainder equal-weight into the top-M assets
risky = {SPY,QQQ,IWM,VGK,EWJ,EEM,VNQ,DBC,GLD,HYG,LQD}; safety = {BIL, IEF}
```
Least-crowded idea in the sweep. The `(1-ρ)` penalty is doing something structurally
different from every other momentum variant here — it downweights assets that are just
levered beta. Verified implementable: `pytaa/strategy/signals.py::protective_momentum_score`
computes it with a rolling 252-day correlation against the EW basket, no look-ahead. All
tickers are free on Yahoo.

### 5. Sector momentum — code it ONLY to reproduce the null, then move on
```
signal_m = P_{m-skip} / P_{m-lookback} - 1        # use skip=0, NOT skip=1
weights  = equal-weight top-N by signal
returns  = (weights.shift(1) * monthly_returns).sum(axis=1)
turnover = |new_weights - drifted_prior_weights|   # drift matters, ~10% of the cost
cost     = 10 bps × turnover
benchmark = equal-weight ALL sectors (not SPY — SPY is too easy a bar)
```
Two independent, well-built repos agree: **net Sharpe 0.53 / 0.635 vs equal-weight
0.56 / 0.658**, FF alpha t = -0.15. Across 40 parameter cells the median beats nothing and
the best cell beats EW by 0.07 Sharpe. Turnover is 280-545%/yr. The one durable finding is
that `skip=0` > `skip=1` at the sector level — short-term reversal does not contaminate
sector indices the way it does single stocks. Budget half a day for this, as a benchmark,
not a strategy.

### 6. PEAD — real effect, but rebuild the parameters from scratch
```
SUE = (actual EPS - consensus mean) / stdev of analyst estimates
Long  top quintile of SUE, short bottom quintile   # SYMMETRIC — not 0.635/-3.78
Enter at close of announcement day + 1
Hold 60 trading days, symmetric long and short
Cost: median bid-ask spread + commissions + SEC fees + borrow (25bp/yr × holding days/360)
```
The academic effect is robust; the one public implementation I found (B2) has thresholds
and holding periods that are transparently fitted (85d long vs 9d short, +0.635 vs -3.78,
no train/test, cash-constrained sequential engine). **Rebuild with symmetric quintiles and
a real IS/OOS split.** Data is your binding constraint — WRDS is the only clean source;
the Robinhood `get_earnings_calendar` MCP tool you already have is the cheap approximation.

### 7. Options overlay on a regime signal — only after #1 or #3 clears
Do not build this until a regime gate has independently earned its keep on the underlying.
When you do: use `lambdaclass/options_portfolio_backtester` (256★, contract-level inventory,
Greeks-aware, explicit fill/cost models) with its free SPY 2008-2025 EOD chains. Two framings
it distinguishes correctly and most people conflate:
- **external budget** — 100% SPY plus a separate 0.5%/yr premium budget (Spitznagel);
- **allocation-reducing** — 99% SPY / 1% options (AQR).
They produce materially different results, and the repo's own Spitznagel sample output is
Sharpe 0.72 / maxDD -46.4%, i.e. the tail hedge is not free. Put-writing / covered-call
overlays gated on `calm_t` from #1 are the natural first test.

---

## What I'd actually do next, in order

1. **One day:** reproduce A1/A2's null on sector momentum with your own engine. It gives
   you a validated benchmark series and a costed, drift-aware turnover routine you'll
   reuse everywhere. Cheap, and it permanently closes a tempting dead end.
2. **One day:** test the `VIX <= VIX3M` gate (#1) as an overlay on things you already
   hold. Zero parameters, free data, no fitting risk — if it doesn't improve Calmar with
   zero degrees of freedom, nothing with more parameters will.
3. **Two days:** build the CCC-BB expanding-percentile regime (#3) and check whether it is
   materially different from #1 or just a lagged copy. Rank correlation between the two
   regime series answers this before you build any strategy on top.
4. **Only then:** Keller DAA (#2) and Generalized Protective Momentum (#4) as full
   strategies, with turnover costed honestly (DAA turnover is brutal) and the backtest
   window truncated to real ETF inception dates.

## Cross-cutting red flags this sweep confirmed
- **Full-sample HMM fit + `predict()` over the whole series** — disqualifies most of the
  regime-detection genre. Grep for `fit(` on the full frame before reading anything else.
- **Missing `.shift(1)` between signal and return** — check `df["signal"] * df["return"]`.
- **Hindsight-trimmed universe** — C2 dropped 5 of 11 sectors; B4 hand-picked 49 names.
  Always ask "how was this list chosen, and when?"
- **Naive turnover** (diff of target weights, ignoring price drift between rebalances)
  understates cost every single month. A1 and A2 both do it correctly; copy them.
- **Fixed-threshold macro/credit signals** need expanding-window percentiles, not
  full-sample z-scores or fixed bps levels.
- **Benchmark inflation** — beating SPY buy-and-hold is a low bar for a multi-sector
  strategy. Equal-weight the same universe. A1 makes this point best: momentum beat SPY,
  but so did naive equal-weighting, and equal-weighting beat momentum.
- **Author-published Sharpes** (Keller, Antonacci, Faber, AllocateSmartly) are in-sample
  for rules designed with knowledge of the sample. pyTAA's spec table quotes them; they
  are not that repo's results.
