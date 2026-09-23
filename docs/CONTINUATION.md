# Continuation log — say **"continue edge hunt"** and start here

This file is the hand-off. It is rewritten at the end of every working block so a fresh
session can pick up exactly where the last one stopped. Read it top to bottom, then the
three findings files it points at, and do the "next" list in order.

## Where things stand (2026-09-22, 22:00 ET)

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

## Next, in order

1. **Score the overnight recorders** (needs ~8 h of data; do this first):
   `05_studies/polymarket_score.py` and `05_studies/memecoin_score.py`. If the Polymarket
   `resolved` column is still NULL for old windows, the Gamma `closed` flag lags: add a
   fallback in the scorer that resolves `up` when `last_spot >= first_spot`. Write the numbers
   into `online_methods.md` and the map. If both are null, `launchctl unload` the recorders
   job; if Polymarket shows a last-30-second mispricing larger than 1.56% + spread, build the
   Polymarket-vs-Kalshi recorder next (both APIs answered; see the map).
2. **Wire the index overlay into the paper agent** (`ai_trader.py` / `risk_gates.py`): hold
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
