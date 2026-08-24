# Repo audit — 2026-08-24

Full read of all 212 tracked files (168 Python, 28,435 lines; 43 markdown). Every
count below was measured, not estimated. Nothing was changed except the TARS
adoption recorded in §6.

---

## 1. What this repo is

An archived research bundle for an SPX/NDX index-options day-trading system, moved
here from `~/index-daytrading` as a **single commit** with no prior history.

| layer | contents | lines |
|---|---|---:|
| `01_START_HERE/` | rules, runbook, engine design, handoff | 5 docs |
| `02_findings/` | current verdicts, including the failures | 5 docs |
| `03_research/` | 26 literature + GitHub + API sweeps | 26 docs |
| `04_live_system/` | the dashboard and its 53 engines | 11,584 |
| `05_studies/` | 115 backtest and hunt harnesses | 16,851 |
| `06_data_guide/` | inventory of 16 GB of market data held outside git | 1 doc |

**The system it describes.** A local `http.server` dashboard on port 8094 (not
FastAPI, despite the README) renders five CSS-only tabs — 0DTE & Gamma, Gap & Go,
Swing, Account & Risk, Black Swan. Behind it, an LLM proposes trades and a stack of
deterministic gates decides whether any reach a paper book: `risk_gates.check_entry`
(time window, event blackout, regime, daily caps, conviction floor) →
`option_pricer.price_trade` (live bid/ask, two-sided market, open interest, package
spread) → `sizing.size_trade` (max loss vs a hard per-trade cap) → `committee.review`
(a bear advocate plus a risk officer with a veto). Exits run every cycle without the
LLM. `risk_gates.DRY_RUN = True`, `LIVE_AGENT = False`, and no order-placement code
exists anywhere in the repo.

**What the research actually concluded.** The honest headline is negative, and that
is the repo's real value. On 147,350 de-duplicated real-quote structure-trades,
every credit structure tested is negative (|t| up to 24). Far-OTM lottery buying
lost 45–90%. There is no reliable intraday directional edge — 56 features, 220
conditions and thousands of combinations produced **zero** that clear 55% on both
train and validate. Three things survived: short interest (IC −0.107 at 63 days,
and the sign is the *opposite* of the squeeze thesis), VIX backwardation (t =
+3.9/+2.8/+2.1 across all three splits), and low dealer gamma as a regime filter
(8 of 8 directional structures pay more there).

`02_findings/METHODOLOGY_TRAPS.md` is the single best file here: twelve ways a
backtest lies, four of which produced fake winners in this repo before being caught.

---

## 2. The biggest problem: three research verdicts coexist as current

The conclusions were overturned twice and **nothing was retracted, only annotated**.
All three layers are still shipped, still linked, and still rendered by the live UI.

| layer | claim | status |
|---|---|---|
| `01_START_HERE/STRATEGY_0DTE.md` | "below the gamma flip = buy premium" | **refuted** — −7.2% straddle, −19.1% strangle |
| `01_START_HERE/RULES.md`, `ENGINE.md` | 0DTE condor on high gamma, +3.7%/trade, t=+7.4, "VALIDATED & ROBUST" | **refuted** — the P&L came from a pricing model; on 1,919 sessions of real SPXW bid/ask it is break-even, and the 11:00 entry actually used is −1.70% |
| `02_findings/` | three surviving signals, no condor edge | **current** |

Both refuted documents carry a correction banner at the top and then continue,
unedited, to teach the retired rule. `STRATEGY_0DTE.md` says at line 3 that the rule
"is WRONG and has been retired", then at line 38 states "**Rule:** above the gamma
flip = pin (sell premium / spreads); below the flip = trend (buy premium)." That
document is what `gap_dashboard.strategy_page()` serves when a user clicks
**"📖 How it works"**.

This is not a documentation nit. It is the direct cause of the dashboard being
confusing, and it must be resolved before any UI work — a clearer presentation of
three contradictory answers is still three contradictory answers.

---

## 3. Defects found

### 3.1 The dashboard contradicts itself on a single page — CONFIRMED · RESOLVED 2026-08-24

> **Resolved.** The page, both desktop notifications, and the two engines that
> manufactured the advice (`gex_periscope`, `gex_signal`) were rewritten to report a
> range regime rather than a side. `tldr_card()` is deleted. `scripts/verify.py`
> check 6 now fails the build if imperative directional advice reappears in the live
> system, and `test_only_the_answer_panel_may_issue_an_action` fails if any panel
> other than the decision card states an action.


`04_live_system/gap_dashboard.py`:

- **:724–770** `rules_panel()` renders a red correction: *"Rejected and now
  hard-blocked: ... 'below the flip = buy premium' (−7.2%)"*.
- **:1344** the glossary, on the same page, teaches it: *"BELOW it = amplify/trend
  (naked options have fuel). The single most useful intraday level — it's your
  call-vs-put trigger."*
- **:1381** the footer, on the same page, instructs it: *"**GO** to buy naked
  calls/puts on low/neg-gamma (big-range) days"*.

Additionally `tldr_card()` (**:403**) is documented in its own docstring as the
"LEGACY directional read … the strategy out-of-sample testing measured at −10% to
−11% per trade" — and is still rendered, into the **Account & Risk** tab (`:1374`).
A retired losing signal is displayed inside the risk panel.

The code knows about this. `master_panel()`'s docstring (:314) says the dashboard
"used to shout several conflicting headlines at once — a green BUY CALLS above a
periscope reading 'price is FALLING' above a desk brief saying 'sit out'." A master
call was added on top; the conflicting sources underneath were never removed.

### 3.2 Four live modules cannot run — CONFIRMED · RESOLVED 2026-08-24

> **Resolved.** `mes_signals` moved into `04_live_system/`, `sizing_curve` and
> `final_system` moved out to `05_studies/`. The verify gate's bundle-split ratchet
> is now empty and fails if a live module imports a study module again.


The bundling split a flat directory into `04_live_system/` and `05_studies/` and
broke the imports across the seam:

| module | imports | which lives in |
|---|---|---|
| `signals_all.py` | `mes_signals` | `05_studies/` |
| `mes_dashboard.py` | `mes_signals` | `05_studies/` |
| `sizing_curve.py` | `backtest_daily` | `05_studies/` |
| `final_system.py` | `multi_edge` | `05_studies/` |

`signals_all.py`'s own docstring says it is where "launchd + /refresh point". So
`04_live_system/` is **not** a runnable copy of the live system, and nothing in the
docs says so.

### 3.3 The health check can never fail a gate — CONFIRMED · RESOLVED 2026-08-24

> **Resolved.** `audit_dash.py` exits 1 on any hard failure or unrunnable check, and
> gained `--strict` plus a third outcome bucket so a failed check and an unrunnable
> one are distinguishable. Two live bugs inside it were fixed at the same time.


`04_live_system/audit_dash.py` runs 23 value-level checks and prints
`n pass / n warn / n fail`, but `main()` has no `sys.exit`, so the process **always
exits 0**. Any cron, launchd job or CI step gating on it passes while the dashboard
is broken. This is the exact failure mode the file's own docstring was written to
prevent: "data that was RETURNED but not CORRECT, displayed as if live."

### 3.4 Failure is silent almost everywhere — CONFIRMED · RESOLVED 2026-08-24

> **Resolved.** The `except: pass` blocks are gone from the live system. Panels return
> one of four explicit states and a raising panel becomes a visible error card rather
> than blanking the page. A cycle writes `cycle_report.json` naming every step that
> failed. Eight gates that returned "allow" on an exception now block.


`04_live_system/` has 229 `try:` blocks and **78** `except …: pass`. The HTTP
handler swallows every exception in `/refresh`, in position tracking and in account
setting, then issues a 302 redirect regardless — a user clicking "🔄 Update" gets an
identical response whether the refresh worked or every engine threw. Combined with
§3.3, the system's default behaviour under failure is to look fine.

### 3.5 The studies are unrunnable on any other machine — CONFIRMED · RESOLVED 2026-08-24

> **Resolved, and it was larger than reported.** Beyond the 53 hardcoded paths there
> were 50 more resolving to a directory that never existed here and 34 more that were
> cwd-relative. All route through `idt.paths`. The ratchet baseline is 0.


**53 hardcoded `/Users/sahilmajmudar/...` paths across 26 files** in `05_studies/`.
No environment variable, no fallback. Every one of those scripts fails on line ~15
of any clone.

### 3.6 Import-time execution — CONFIRMED · RESOLVED 2026-08-24

> **Resolved for `05_studies/`:** all 117 modules import without running work, and the
> verify gate holds it there. Doing so exposed two scripts that could not run at all
> (`UnboundLocalError` from a shadowed `paths` and from module-level accumulators),
> both found by `ruff` and fixed.


Modules that do real work at import rather than under `if __name__ == "__main__"`:
**15 of 53** in `04_live_system/`, 24 of 45 in `05_studies/`, 57 of 70 in
`05_studies/scripts/`. `gex_regime.py` raises `FileNotFoundError` on a bare
`import`. `option_pricer.py` — a core pricing module — is on the list. `scan_all.py`
is a script masquerading as a module, which the runbook notes "caused several silent
no-op edits".

### 3.7 Duplication of things that must not diverge

- `_key()` — the API-key loader — is copy-pasted in `ai_desk.py`, `analyst.py`,
  `uw_client.py` and `fetch_minutes.py`, each hardcoding the original author's
  `.env` path first.
- At least three independent Black-Scholes implementations (`condor._bs`,
  `gex_periscope.bs_gamma`, `bt_options.bs`, `scripts/option_edge.bs`) with
  different default risk-free rates (0.04 vs 0.045).

### 3.8 Operational fragility

- 11 `sqlite3.connect` sites, none setting WAL mode or a busy timeout. The dashboard
  renders while `scan_all` writes the same DBs; the default 5-second lock is the
  only thing between them.
- 40 `yfinance` call sites in the live system against 4 sleep/retry mentions total.
  yfinance is unofficial, rate-limited and delayed; there is no backoff.
- `MANIFEST.md` claims "200 files total" and is stale by 7 (`RUNBOOK.md`,
  `WHAT_WORKS.md`, `WHAT_FAILED.md`, `METHODOLOGY_TRAPS.md`, `DATA.md`, `INDEX.md`,
  `build_indexes.py`).
- README says "FastAPI dashboard"; it is `http.server` from the standard library.

---

## 4. What is missing

| missing | consequence |
|---|---|
| **Any dependency manifest** | no `requirements.txt`, `pyproject.toml`, `setup.py` or lockfile shipped. Reconstructed during this audit from imports. |
| **Any unit test** | the 20 files matching `test` are research harnesses needing 16 GB of data and network. Nothing verifies a single function offline. |
| **Any CI** | no `.github/`, no pre-commit, no linter config. |
| **A data bootstrap** | `DATA.md` inventories 16 GB but no script reconstructs it. The Dolt clone command exists only as prose in `HANDOFF.md`. |
| **Git history** | one squashed commit. No provenance for any decision, no way to bisect when a number changes. |
| **The launchd plist** | `com.gapscan.dashboard.plist` is referenced by README and RUNBOOK, shipped by neither. |
| **`.env.example`** | four modules need three different API keys; none are documented in one place. |
| **A changelog for the verdicts** | see §2 — there is no ordered record of what superseded what. |

---

## 5. How to improve — in priority order

**P0 — resolve the contradiction (blocks the UI work).**
Pick one source of truth. `02_findings/` is the only layer measured on real quotes,
so it wins. Then: move `STRATEGY_0DTE.md` and `RULES.md` into an `07_superseded/`
directory with a one-line pointer at the top of each; delete the retired claims from
`gap_dashboard.py:1344` and `:1381`; delete `tldr_card()` and its call site (`:1374`); and
point "📖 How it works" at `WHAT_WORKS.md` instead. Add `docs/VERDICT_LOG.md` — one
dated line per overturned claim — so the next reversal replaces rather than accretes.

**P1 — make failure visible.** Add `sys.exit(1 if FAIL else 0)` to `audit_dash.py`.
Replace the `except: pass` blocks in the HTTP handler with a rendered error banner.
The system's current default under failure is silence, and §3.1 shows silence is
already costing correctness.

**P2 — make it run anywhere.** One `paths.py` resolving `DATA_ROOT` from an
environment variable with a repo-relative default; mechanically replace the 53
hardcoded paths. Fix the four cross-seam imports in §3.2 by adding `05_studies/` to
the path in a shared `conftest`-style shim, or by moving the four shared modules.
Commit `requirements.txt` and a `.env.example`.

**P3 — the dashboard rewrite (the work you flagged).** The confusion is structural,
not cosmetic. `gap_dashboard.py` is 1,533 lines: ~350 lines of CSS inside a single
f-string, 30+ panel functions each concatenating their own HTML and emoji, one
`render()` that returns the whole page, and a `<meta http-equiv=refresh content=60>`
that reloads everything every 60 seconds. Five tabs are CSS-only radio buttons, so
the tab you were on resets on every refresh. There is no template layer, no
component boundary, no client-side state, and no way to change a colour without
editing a Python string.

The information architecture is the deeper issue: the page currently presents a
master call, a legacy retired call, a desk analyst brief, a scorecard, a freshness
banner, a slide-out scalp tab and five tabs of panels — several of which answer the
same question differently. Before any redesign, decide what one question each tab
answers and delete anything that answers it a second way.

**P4 — housekeeping.** Regenerate `MANIFEST.md` from `05_studies/scripts/build_bundle.py`
and make it a verify check. Fix the FastAPI claim in the README. Consolidate `_key()`
and the Black-Scholes implementations.

---

## 6. TARS adoption — record

Adopted with `tars adopt` on 2026-08-24. Kit 0.1.0.

- `.tars/profile.json`, `structure.json`, `routing-policy.json` created
- 8 hooks vendored to `.tars/hooks/` and wired in `.claude/settings.json`
- 5 commands, 1 skill vendored to `.claude/`
- `CLAUDE.md` and `AGENTS.md` generated, then filled in with this repo's real
  description, verify manifest and project notes
- the six numbered directories and `MANIFEST.md` registered in `structure.json`,
  so `tars tidy` reports **0 stray files, 0 unregistered dirs**
- `tars doctor` reports clean

**Verify manifest** — `venv/bin/python scripts/verify.py`, wired into
`.tars/profile.json`. It is offline by design: the 16 GB of data is not in git, so a
gate needing it would be skipped on every clone, and a skipped gate is not a gate.
Four checks, all passing:

| check | what it guards |
|---|---|
| `compile` | all 168 tracked `.py` files parse |
| `import-smoke` | 21 live modules import with no data dir and no network |
| `bundle-split-ratchet` | the 4 broken modules in §3.2 cannot become 5 |
| `portability-ratchet` | the 53 hardcoded paths in §3.5 cannot become 54 |

The two ratchets turn discovered debt into a guard: the count may fall freely, and
fixing an item means deleting it from the baseline, but new instances fail the gate.
