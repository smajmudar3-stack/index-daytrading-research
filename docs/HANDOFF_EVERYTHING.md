# Everything, in one place: the index-daytrading project as of 2026-10-28

Written so a fresh Claude (Desktop, Code, or anyone) can pick up the whole body of work
without this conversation. Read this file first, then `CLAUDE.md` (the standing rules and
every lesson, one bullet each), then `docs/CONTINUATION.md` (the running hand-off), then
`02_findings/WHAT_WORKS.md` and `02_findings/METHODOLOGY_TRAPS.md` before touching any
backtest.

## 1. What this is

Sholo (sole developer, trades a small account, aims to grow it) has had Claude run an
"edge hunt" since August 2026: test every way to make money in markets that a retail
account can reach, measure each one honestly on real prices with real costs, keep what
survives, and build a dashboard that turns what survives into plays. The code word
"continue edge hunt" means: read `docs/CONTINUATION.md` and carry on.

Nothing here places an order. `risk_gates.DRY_RUN = True`, `LIVE_AGENT = False`, and a
test fails if order-placement code appears. Every book is paper, every fill is at the next
open or at the ask/bid, every entry is frozen when recorded, and losers stay on the page.

## 2. Where everything lives

| What | Where | Size |
|---|---|---|
| The repo (code, findings, docs, tests) | `/Users/sahilmajmudar/index-daytrading-dev` (dev checkout, branch `main`, pushed to origin) | 2.3 MB packed |
| Production checkout and interpreter | `/Users/sahilmajmudar/index-daytrading` (`venv/bin/python3` is `$IDT_PYTHON`) | |
| Market data, not in git | `/Users/sahilmajmudar/index-daytrading/data` (`$IDT_DATA_ROOT`), incl. `opt_panel/` (2.5 GB: option chains 2019-05→2026-08 by month, OHLCV 2018→, earnings, EPS, statements, signal panels) and `dolt/` | 18 GB |
| Live state: snapshots and ledgers | `/Users/sahilmajmudar/index-daytrading-dev/04_live_system/data` (22 sqlite ledgers incl. `plays.db`, `prices.db`, `gmgn.db`, `pumpfun.db`; JSON snapshots) | 6.8 GB |
| Logs of every scheduled job | `/Users/sahilmajmudar/index-daytrading-dev/logs` | |
| Claude's memory for this project | `/Users/sahilmajmudar/.claude/projects/-Users-sahilmajmudar-index-daytrading-dev/memory/` (`MEMORY.md` is the index) | |
| The full Claude Code transcript | same folder, `*.jsonl` (75 MB); a readable extract is `CONVERSATION_LOG.md` in the Desktop package | |
| Secrets | `<repo>/.env` via `idt.keys`; never elsewhere. Unusual Whales key, FRED (optional), GMGN public read-only key in `~/.config/gmgn/.env` | |

Folders inside the repo: `01_START_HERE/` runbook and the retired rules; `02_findings/` the
current verdicts (25 files); `03_research/` literature and repo sweeps (30 files);
`04_live_system/` the dashboard and its engines (83 modules); `05_studies/` the backtest
harnesses (79 studies); `06_data_guide/DATA.md` the data inventory; `docs/` the hand-offs,
the strategy tree, 36 research briefs in `docs/briefs/`; `idt/` the shared package; `test/`
the offline suite (208 tests); `scripts/verify.py` the gate.

## 3. The method, in one paragraph

Real bid and ask, never mid. Entry at the next open or at the ask. Excess return over SPY.
Three time splits (A 2019–21, B 2022–23, C 2024–26) and a result must hold in all three.
A noise bar of sqrt(2 ln N) for N cells scored. "Not measurable from here" is a valid
verdict and is written down as one. `02_findings/METHODOLOGY_TRAPS.md` lists the seventeen
ways a backtest here has lied, with the date each one was caught; trap 6 (measuring from
before the signal is known) was caught twice this autumn, trap 17 (a phantom Presidents'
Day session blanking the 2020 crash weeks) on 2026-10-24.

## 4. What was measured, and the verdict

Real, running in paper:

| Signal | Rule | Measured | Where |
|---|---|---|---|
| Earnings surprise (the stock book) | top 25 surprises among names inside their 63-session drift window, held 63 sessions in shares | +4.24%/quarter over SPY, t 2.3, hit 0.49, all splits; +7.4% hit 0.60 on names with chains | `signal_accuracy.md`, `swing_stock.py` |
| Swing ranker | surprise + residual momentum + 12-1, equal ranks, top 25, 21 sessions | +0.84%/hold over SPY, hit 0.49, +9.3%/yr, all splits; per-name weights tested and lost | `signal_accuracy.md`, `swing_ranker.py` |
| Stress reversal | bottom 40 by 1m/1w/Bollinger composite, 10 sessions, while VIX > 25 | +2.59%/hold (restated +1.88% on a clean calendar), hit 0.56, all splits; flat to negative out of regime; sector-neutral version weaker | `stress_reversal.md`, `stress_sector_neutral.md`, `stress_reversal.py` |
| Index overlay | long the index 1x, 2x while VIX > VIX3M inside a golden cross | 15.3%/yr vs 11.5%, DD 59%, 2006–2026 | `goal_feasibility.md`, `index_overlay.py` |
| Earnings variance premium | rich implied into prints is sold | +3.6 pt seller edge in points; not reproduced in straddle P&L | `earnings_vrp.md` |

Weak: value/buyback factors (strong 2022–23, flat since), monthly SPY put-write (4–5%/yr,
Sharpe 2.1), covered calls (7.6% vs SPY 10%), Kalshi/Polymarket same-event pairs.

Null or dead, with the numbers: 0DTE index credit structures (147,350 real trades, all
negative); weekly single-name direction (214,803 name-weeks, best composite 52%); a
14-DTE vertical costs 8–15% of risk in bid-ask alone; every option structure on the
measured stock signals (23,521 real-fill trades: all negative, shares positive on the same
dates, `play_structures.md`); information diffusion (null); stat-arb (negative net of
5 bp); opening-range direction (null; width forecasts range); memecoins at every horizon
(copying GMGN smart money −17% net at 5 min; birth-tape rules all negative; paper books
−9% and −23%); Polymarket 5-minute crypto (fee-taxed); cross-exchange crypto gaps (0 net);
68 factors scored for single-stock direction, none above ~50%. `02_findings/online_methods.md`
is the full inventory with one row per method; `docs/briefs/` are the 36 deep briefs.

## 5. What is live right now

**The dashboard** (`04_live_system/dashboard_app.py`, launchd `com.daytrading.dev-dashboard`,
http://127.0.0.1:8095, restart with `launchctl kickstart -k gui/$(id -u)/com.daytrading.dev-dashboard`
after panel changes). Views: Plays / Books / Tape / Research / System. Refreshed every five
minutes by `refresh_cycle.sh` → `scan_all.py`.

**The Plays desk** (`04_live_system/plays.py`): names the measured books hold → the
expression that measured best (shares; option legs printed beside with their measured
number) → sized at $500 notional → dated timeline, reasoning stack (signal / structure /
macro theme / catalysts / research) → at most 3 new plays a week, Mon and Wed → ledger
`plays.db` scored against the promise. `plays.book_manual()` records a play asked for by
hand (confidence "unmeasured"). Ledger at 2026-10-28:

| Issued | Play | Promised | Now |
|---|---|---|---|
| 10-19 | SMCI shares (surprise + ranker) | +7.4% | +11.5% |
| 10-19 | AEO shares | +7.4% | +9.6% |
| 10-19 | AFRM shares | +7.4% | +0.6% |
| 10-21 | TSLA Oct-23 385/360 put debit, hand-asked, Q3 print | +35% of risk | **closed +61.8% (+$488)**: stock −3.1% day one, 372.22 at expiry |
| 10-26 | DK, EC, TEN shares (ranker) | +1.9% | −11.1%, +1.0%, −2.8% |

**The books** (Books view): quarterly stock book (60 open), swing ranker (60 open), stress
book (40 open, out of regime), the emails as trades (65 open, 17 closed, 41% hit, −0.9%),
index overlay (1x), weekly options cards (empty most weeks), memecoin book (1,112 closed,
−10%). All read `price_cache.py` (`prices.db`, 2,350 names, two years).

**Scheduled headless Claude sessions** (launchd, plists in `04_live_system/`):
`com.daytrading.desknotes` (reads the Crown Macro Letter from Gmail three times a day →
`desk_notes.json`, the macro overlay), `com.daytrading.plays-research` (weekdays 07:40,
researches every held and considered name with sources → `plays_research.json`; failed on
10-26 and 10-27 on the Claude usage limit, ran 10-23 and 10-28), `com.daytrading.branch-hunt`
(Saturdays 09:00, grows `docs/strategy_tree.json` by one measured branch; first run 10-24
measured `stress-sector-neutral` and found trap 17), `com.daytrading.calendar` (monthly
macro calendar). **Recorders** (`com.daytrading.recorders`, keep-alive, `run_recorders.sh`):
Polymarket, crypto venues, memecoins, Kalshi, pump.fun curves and trades, GMGN tape
(sol/bsc/base), memecoin paper book.

**The strategy tree** (`docs/strategy_tree.json`, 53 nodes): every hypothesis tested across
every department (equities long and short, every option shape, index, crypto, prediction
markets, income), its verdict and numbers, and the waiting branches the Saturday hunt
takes next.

## 6. What Sholo asked for, in order, and what came of it

1. Find anything profitable → the method, the 0DTE verdicts, the online-methods audit.
2. Build an information-diffusion model → built, measured null.
3. Stop optimising $5k→$50k, get signals right (hit rate or big wins), test every factor
   and every earnings-day pattern → 68 factors scored; the quarterly stock effects are the
   only real ones; nothing calls single-stock direction above ~50%.
4. Put the stress book on the swing panel, make the swing produce picks with weights per
   stock → ranker built; per-name weights measured and rejected.
5. Make the emails help with trades → `desk_trades.py`, three paper books from the notes.
6. Test opening ranges on SPX/NDX → direction null; width forecasts the day's range.
7. Test memecoins on GMGN like the options, then automate → recorders, ten briefs,
   copy-trade replay, two paper books: every retail-visible rule negative; the swap skill
   stays keyless until a rule nets positive in paper in both halves.
8. Rewrite the dashboard into a product that gives plays with reasoning, timeline and
   expected profit, with agents and schedules, as an evolving tree → the Plays desk, the
   research and branch-hunt sessions, the tree, two readability passes.
9. A directional Tesla Q3 earnings play with heavy research → the 385/360 put debit,
   called 54/46 down; it made +62%. The call was explicitly a thin lean on a coin flip.

## 7. Standing rules

- Nothing places live orders; no non-public information is sought; secrets only via `.env`.
- Verify before claiming done: `scripts/verify.py`, `pytest test/`, `ruff check .`,
  `scripts/build_manifest.py` after adding files. Use `$IDT_PYTHON` from `local.env` and
  `PYTHONPATH=<repo>:<repo>/04_live_system`.
- Only the Plays desk and Today's decision may name a trade; a test walks every view.
- A panel reads a snapshot; it never calls a vendor. A snapshot from an older engine is
  refused, not shown. Every issued card is recorded once and never re-priced.
- The research session is context, never a signal: it can demote or veto a play, never
  raise it. The ranks were measured; the research was not.
- Plain English to Sholo: what happened, what broke, what is left, real error output.

## 8. Known open items

- `test_credit_structure_thresholds_are_positive` fails on a date-dependent fixture
  (pre-existing, not from any recent change); fix the test's clock.
- The signal panel's 2020 crash weeks are blank for 92% of names (trap 17); the stress
  book's house number restates from +2.59% to +1.88% on a clean calendar. First child
  branch on the tree: rebuild the panel on the names' calendar.
- The Anthropic API account is out of credit (the headless sessions use the Claude Code
  login instead); the Unusual Whales key throttles under load; GMGN API key not yet
  created by Sholo; Sholo has not reacted to the "options lose, shares win" verdict.
- Web search in the Claude Code session is capped at 200 per session; the Tesla research
  ran on direct page fetches after the cap.

## 9. How to resume

In Claude Code, from the repo: "continue edge hunt". In any other Claude: open this file,
`CLAUDE.md`, `docs/CONTINUATION.md`, then the findings named above. The dashboard is the
state of the world; the ledgers in `04_live_system/data/*.db` are the record.
