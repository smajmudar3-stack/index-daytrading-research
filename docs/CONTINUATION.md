# Continuation log — say **"continue edge hunt"** and start here

This file is the hand-off. It is rewritten at the end of every working block so a fresh
session can pick up exactly where the last one stopped. Read it top to bottom, then the
three findings files it points at, and do the "next" list in order.

## Where things stand (2026-09-23, 15:00 ET)

**Since the last hand-off:** seven swarm briefs filed in `docs/briefs/` (prediction-markets,
memecoins, crypto-derivatives, options-income, sports-betting, yields-altdata,
bot-claims-audit); nineteen agents were cut off by the session cap and three relaunches were
refused by the route gate. **To re-run them, Sholo's prompt must begin with "use claude for
everything this session"** (the gate reads the directive only from the prompt it arrives in).
Overnight recorders scored: Polymarket null at 3 s polling (191 windows), cross-venue null
(12,653 gaps, 0 net), memecoins strongly negative (137 launches). Pre-earnings straddle:
+3.2% at mid, −33% real, −4.6% even in the tightest-spread names. `index_overlay.py` built,
wired, seeded; stock book filled at the 09-23 open (TCOM, AEO, RH, TEN, ODD).

**2026-09-23 evening:** `engine_combo_test.py` (whole engine 15–18%/yr), `xsec_diffusion_test.py`
(null), `kalshi_recorder.py` + `kalshi_score.py` (fourth recorder in the keep-alive job),
`test_macro_calendar` clock pinned (suite fully green). Four recorders now run.

**2026-09-23 ~16:00 ET:** the nineteen missing briefs relaunched under Sholo's directive, each
agent instructed to WRITE its own `docs/briefs/<slug>.md` (so a cap cannot lose it) and to
compute with yfinance/public data where possible. On resume: `ls docs/briefs/` — any of the
26 slugs missing is a re-run; then copy each new brief's verdict row into
`02_findings/online_methods.md` and the map, and commit.

## Where things stood at the first hand-off (2026-09-22, 22:00 ET)

**Goal as stated by Sholo:** an automated system that turns $5,000 into $50,000, any market,
any method, no direction filters, with strong swing theses, without overfitting.

**Measured answer so far:** no fast path exists on any evidence collected; the slow path is
real and is roughly 15–20%/yr at 2× with a 50–60% drawdown. Every measurement is in
`02_findings/online_methods.md` (the table) and `03_research/RESEARCH_EVERY_MARKET.md` (the
tree with sources). Do not re-run what is already measured; extend it.

### Running unattended right now

| job | what | check |
|---|---|---|
| `com.daytrading.recorders` (launchd, keep-alive) | `polymarket_recorder.py`, `crypto_venue_recorder.py`, `memecoin_recorder.py` | `launchctl list \| grep recorders`; `tail logs/*_recorder.out` |
| `com.daytrading.dev-refresh` (launchd, 5 min) | the dashboard cycle: weekly options book (4h gate), stock book (24h), stock ledger (4h) | `tail logs/dev-refresh.out` |

### Committed and pushed (all on `main`, last `91adc2c`)

- Weekly options book: `REQUIRE_MEASURED_BASIS`, no debit price stop, cost on every card,
  `pead` voter, `flow_lean` zeroed, scan gate fixed (was 4 min, is 4 h), calibration fixed.
- Quarterly stock book `swing_stock.py` + ledger + panel (first picks TCOM, AEO, RH, TEN, ODD,
  filling at the 2026-09-23 open).
- Studies: `xsec_*` (predictors, composite, vertical, straddle, fundamentals, portfolio, uw),
  `spy_putwrite_test.py`, `statarb_test.py`, `uw_intraday_flow_test.py`, scorers
  `polymarket_score.py`, `memecoin_score.py`.
- Findings: `weekly_predictors.md`, `weekly_structure.md`, `fundamentals.md`, `uw_flow.md`,
  `online_methods.md`, `statarb.md`; research: `RESEARCH_WEEKLY_PREDICTORS.md`,
  `RESEARCH_EVERY_MARKET.md`.

### Added late 2026-09-22 (after the first hand-off)

- `05_studies/statarb_test.py` → `02_findings/statarb.md`: dead net of costs.
- Overnight-only holding: +12%/yr gross, −13%/yr net of 10 bp a day (in `online_methods.md`).
- `05_studies/gxz_straddle_test.py`: the pre-earnings straddle bought T-3, sold before the
  release, real fills, 2020–2026. Was still running at hand-off; result goes into
  `online_methods.md` and, if positive after the spread, into `weekly_structure.md`.
- `polymarket_recorder.py` fix: the Gamma API hides closed markets unless `closed=true`
  is passed, so resolutions never populated; fixed and the job restarted ~22:00 ET. The
  scorer also has a spot-proxy fallback and labels which rows use it.

### The research swarm (launched 2026-09-22 ~22:30 ET under Sholo's directive "use claude for everything this session")

Sixteen background agents, one per branch. Each brief is filed as `docs/briefs/<slug>.md`
when it lands and its verdict row is copied into `02_findings/online_methods.md` and the map.
If a slug below has NO file in `docs/briefs/`, that agent did not finish before the session
ended: re-run it (the prompts are the bullet text; ask for 1,200–2,000 words with sources).

| slug | topic |
|---|---|
| `prediction-markets` | Polymarket 5-min mechanics/fees/oracle latency, bot claims with receipts, Polymarket-vs-Kalshi gaps, US access |
| `memecoins` | launch survival/return distributions, sniping economics, verified wallet P&L, rug detection, scams |
| `crypto-derivatives` | funding carry, CME basis, crypto options VRP, cross-exchange/DEX arb latency, US access |
| `options-income` | CBOE PUT/BXM/CNDR records, VRP with defined risk, dispersion, 0DTE who-wins, earnings option plays, LEAPS leverage |
| `equity-anomalies` | OSAP post-2015 survivors, JKP replication, reversal, PEAD variants, momentum crash control, ML selection |
| `leverage-growth` | 2×/3× index with MA filters, vol targeting, Kelly/ruin, trend following, VIX overlays, the 58%/month arithmetic |
| `bot-claims-audit` | TRM drainer campaign, engagement-bait pattern, open-source bots' verified results, retail base rates, real 10× cases |
| `sports-betting` | value/arb betting ROI and limiting, promos, Kalshi/Polymarket sports, legality, DFS |
| `yields-altdata` | T-bills to stablecoin/staking/JEPI/SPAC/merger arb; free alt-data signals with OOS results |
| `retail-base-rates` | day-trader outcome studies, leverage/ruin, track-record survivorship, verified small-account 10× runs |
| `futures-fx` | CTA/trend records, micro futures, Turtle OOS, FX carry/momentum, prop-firm pass rates, seasonal spreads |
| `crypto-factors-mm` | Liu-Tsyvinski-Wu crypto factors realised 2021–26; retail market-making (Hummingbot) evidence |
| `informed-cloning` | congress trades (NANC/KRUZ), 13F cloning (GVIP), insider cluster buys, 13D activism, short reports |
| `calendar-macro` | pre-FOMC drift decay, turn-of-month, earnings premium, opex/pension flows, CPI/NFP days, overnight gap |
| `llm-news` | Lopez-Lira & Tang and replications, filing/transcript tone, Reddit sentiment, news-arrival speed, LLM portfolios |
| `special-situations` | merger arb, tenders/odd-lots, spinoffs, SPAC arb, index adds, splits; crypto airdrop/points farming |

## Next, in order

0. **Re-run the nineteen missing swarm briefs** (slugs with no file in `docs/briefs/`),
   which needs the operator directive in the prompt; file each and copy its verdict row.
1. **Re-score the recorders after a week** (Polymarket needs ~1,000 windows for the
   last-30-second cells; memecoins are decisive already). Then `launchctl unload` the
   recorders job if nothing changes. Originally:
   `05_studies/polymarket_score.py` and `05_studies/memecoin_score.py`. If the Polymarket
   `resolved` column is still NULL for old windows, the Gamma `closed` flag lags: add a
   fallback in the scorer that resolves `up` when `last_spot >= first_spot`. Write the numbers
   into `online_methods.md` and the map. If both are null, `launchctl unload` the recorders
   job; if Polymarket shows a last-30-second mispricing larger than 1.56% + spread, build the
   Polymarket-vs-Kalshi recorder next (both APIs answered; see the map).
2. **DONE 2026-09-23: the index overlay runs in paper** (`index_overlay.py`, Markets view).
   Next on it: a stock sleeve tilt toward the stock book's picks, and a monthly report of
   paper equity vs buy-and-hold. Originally: wire the index overlay into the paper agent (`ai_trader.py` / `risk_gates.py`): hold
   2× SPY, 3× when `market_signal()` says VIX backwardation inside a golden cross, stock
   sleeve tilted to the stock book's picks. Paper only. `DRY_RUN` stays True.
3. **Re-pull the vendor flow alerts in ~3 months** (`uw_history_pull.py`; delete
   `flow_alerts__*.parquet` first) and score them once forward returns exist.
4. **Live checks on the stock book** after a week: the ledger panel on Markets shows fills
   and marks; nothing should ever be re-entered at a fresh price.
5. The pre-existing test failure `test_expiry_on_a_high_importance_print_is_flagged` is a
   hard-coded 2026-09-11 expiry now in the past; fix the test's clock, not the code.

## Rules that stay on

- Nothing places an order. `risk_gates.DRY_RUN = True`, `LIVE_AGENT = False`, and a test
  fails if order-placement code appears. Robinhood reads were blocked by the permission layer;
  live trading needs Sholo's explicit written go and his own switch flip.
- No non-public information is sought, ever.
- Every new number goes through the same method: real prices, real costs, three time splits,
  the noise bar stated, and "not measurable from here" said out loud when true.
- Verify before claiming done: `scripts/verify.py`, `pytest test/`, `ruff check .`, and
  `scripts/build_manifest.py` after adding files. Use `$IDT_PYTHON` from `local.env`.

## How to resume in one line

> continue edge hunt — read docs/CONTINUATION.md, run the two scorers, write the numbers in,
> then do item 2.
