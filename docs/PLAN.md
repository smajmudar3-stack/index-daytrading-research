# Plan — make this repo easy to use, easy to understand, and better as a platform

Written 2026-08-24, after the full audit in [AUDIT.md](AUDIT.md). Every problem cited
here was reproduced, not inferred.

**The through-line.** This repo's research is unusually honest and its engineering is
unusually confusing, and those two facts are connected. The research changed its mind
twice; the code and the UI kept every version. So the dashboard shows several answers to
the same question, the reader cannot tell which is current, and the fix for "the UI is
confusing" is mostly not a UI change. Phases 1–3 remove the contradictions. Phase 4
rebuilds the interface on top of a repo that finally has one answer. Phases 5–7 make the
platform better than it was.

Phases are ordered by dependency, not by size. Do not start Phase 4 before Phase 1.

---

## Phase 0 — done

Cloned, Python 3.13 venv, `requirements.txt` reconstructed from imports, TARS adopted,
offline verify gate wired (`scripts/verify.py`) with two debt ratchets. `tars doctor` and
`tars tidy` are clean.

---

## Phase 1 — one answer per question

**Why.** Three research verdicts ship as current and the UI renders all three. Until this
is fixed, every other improvement is polish on a contradiction.

The live proof, all on one page:

- `gap_dashboard.py:724` renders a red box: *"Rejected and now hard-blocked: … 'below the
  flip = buy premium' (−7.2%)"*
- `gap_dashboard.py:1344` (glossary) teaches that rule as *"the single most useful
  intraday level — it's your call-vs-put trigger"*
- `gap_dashboard.py:1381` (footer) instructs it: *"**GO** to buy naked calls/puts on
  low/neg-gamma days"*
- `scan_all.py:74` **fires a macOS desktop notification** reading *"RECOMMENDED: BUY PUTS
  (downside amplifies)"* — pushing the −7.2%-to-−19.1% trade to the user unprompted
- `scan_all.py:59` fires *"BUY CALLS"* / *"BUY PUTS"* alerts on a conviction transition —
  the strategy measured at −10% to −11% per trade
- `gap_dashboard.py:1374` still renders `tldr_card()`, whose own docstring calls it the
  legacy read *"measured at −10% to −11% per trade"*, into the **Account & Risk** tab

**Do.**

1. `docs/VERDICT_LOG.md` — one dated line per claim, its status, and the file that
   killed it. This is the file a reader consults when two documents disagree. Ordered
   newest first. It is the only place a verdict may be recorded.
2. `07_superseded/` — move `STRATEGY_0DTE.md` and `RULES.md` there, each with a single
   pointer line at the top. They are valuable as a record of how the conclusion moved;
   they are dangerous as instructions. Both currently carry a correction banner and then
   continue, unedited, to teach the retired rule — `STRATEGY_0DTE.md` says at line 3 that
   the rule "is WRONG and has been retired" and states it again at line 38.
3. Repoint **"📖 How it works"** at `02_findings/WHAT_WORKS.md`. It currently serves the
   retired `STRATEGY_0DTE.md`.
4. Delete the retired claims from the code: the glossary entry, the footer, `tldr_card()`
   and its call site, and both notification blocks in `scan_all.py`.
5. Fix the stat drift. The 0DTE section header says the range read is "validated, t=−16";
   the corrected figure measured against real VIX9D-implied vol is t=−13.2. Two t-stats
   for one claim on one page. Pick the real-quote number everywhere.
6. Rename the "📐 Validated rule" panel. Its badge says *Validated* and its body says
   *"Size this as unproven, not as a validated edge."* Call it **"0DTE condor — unproven"**.

**Done when.** A grep for the retired claims returns nothing outside `07_superseded/` and
`VERDICT_LOG.md`, and no code path can emit "BUY CALLS" or "BUY PUTS" as a recommendation.
Add that grep to `scripts/verify.py` as a fifth check so it cannot come back.

---

## Phase 2 — make failure visible

**Why.** The system's default behaviour when something breaks is to look fine. That is
the most expensive property a trading dashboard can have, and it is how the Phase 1
contradictions survived this long.

Measured: `04_live_system/` has 229 `try:` blocks and **78** `except …: pass`. The HTTP
handler swallows every exception in `/refresh`, in position tracking and in account
setting, then returns an identical 302 either way — clicking **🔄 Update** looks the same
whether every engine ran or every engine threw.

And the one place they did *not* catch takes the whole page down. On a fresh clone the
dashboard returns **HTTP 000, zero bytes**: `scorecard.panel()` raises
`sqlite3.OperationalError: unable to open database file` because `data/` does not exist,
`render()` has no guard, and the connection dies. Creating an empty `data/` directory
alone takes it to HTTP 200 and 37 KB.

**Do.**

1. `sys.exit(1 if FAIL else 0)` in `audit_dash.py`. It runs 23 real value-level checks and
   **always exits 0**, so no cron or CI step can gate on it.
2. Wrap each panel call in `render()` individually. A panel that throws renders a red
   error card naming the panel and the exception; the rest of the page still loads. One
   bad panel must never blank the page.
3. Replace the `except: pass` blocks in the HTTP handler with a status banner that reports
   what ran and what failed on the last refresh.
4. Sweep the remaining 78. Each becomes one of: a logged warning, a rendered "unavailable"
   state, or a real raise. Silence is not one of the options.
5. **The event blackout gate is enforced but inert.** `risk_gates._events()` returns `[]`
   on any exception, so a missing, empty or stale `data/events.json` makes
   `event_blackout` — which is listed in `ENFORCED` — pass every single day while
   reporting as enforced. FOMC and CPI dates are hand-entered per `ENGINE.md`. Make a
   stale or absent file a **hard fail of the gate**, not a pass, and surface the file's
   age in the risk panel.

**Done when.** Deleting `data/` still yields a page that loads and says exactly what is
missing, `audit_dash.py` returns 1 on any failure, and an empty `events.json` blocks
trading rather than permitting it.

---

## Phase 3 — make it run anywhere, in one command

**Why.** A fresh clone runs nothing. There is no dependency manifest, no bootstrap, and
26 files hardcode another machine's home directory.

**Do.**

1. `04_live_system/paths.py` — one module resolving `DATA_ROOT` from an environment
   variable with a repo-relative default. Mechanically replace the **53 hardcoded
   `/Users/sahilmajmudar/…` paths across 26 files**. The verify gate already ratchets this
   count; drive it to zero and drop the baseline to 0.
2. Fix the four modules the bundle split broke — `signals_all`, `mes_dashboard`,
   `sizing_curve`, `final_system` import modules filed under `05_studies/`.
   `signals_all.py` is where launchd and `/refresh` point, so the documented entry point
   does not import. Move the four shared modules into `04_live_system/` rather than adding
   path shims. Then delete them from `BUNDLE_BROKEN` in the verify gate.
3. `pyproject.toml` and a real console script. One command, four verbs:
   `idt bootstrap` (create `data/`, seed empty snapshots, check keys, report what is
   missing and how to get it), `idt serve`, `idt refresh`, `idt audit`.
4. `.env.example` listing all three keys — `ANTHROPIC_API_KEY`, `UNUSUALWHALES_API_KEY`,
   `POLYGON_API_KEY` — and consolidate the four copy-pasted `_key()` loaders into one that
   reads the repo `.env` first and the environment second. All four currently hardcode the
   original author's home directory as the first candidate.
5. Ship `com.gapscan.dashboard.plist` as a template. README and RUNBOOK both reference it;
   neither ships it.
6. `scripts/bootstrap_data.py` — fetch what is fetchable (the Dolt clone, the swing panel,
   minute bars) and print a clear inventory of what it cannot reconstruct. `DATA.md`
   documents 16 GB with no script that acquires any of it.

**Done when.** `git clone && idt bootstrap && idt serve` produces a working page on a
machine that has never seen this project, and the page states plainly which panels are
empty for want of data.

---

## Phase 4 — the interface

Do not start this before Phase 1. Most of what reads as "confusing" is contradictory
content, and a cleaner presentation of contradictory content is still contradictory.

**Why it is confusing, measured.** `gap_dashboard.py` is 1,533 lines: roughly 350 lines of
CSS inside a single f-string, 30-plus panel functions each concatenating their own HTML and
emoji, one `render()` returning the entire page, and `<meta http-equiv=refresh content=60>`
reloading everything every 60 seconds. The five tabs are CSS-only radio buttons, so **the
tab you were reading resets on every refresh**. There is no template layer, no component
boundary, no client-side state, and no way to change a colour without editing a Python
string.

The information architecture is the deeper problem. The page renders **26 slots across
about 22 distinct panels**, five of them stacked above the tab bar before you reach any
tab. Between them the UI can emit at least **17 different action verbs** — BUY CALLS, BUY
PUTS, SELL PREMIUM, ENTER, EXIT, HOLD, SIT OUT, STAND DOWN, WAIT, AVOID, TRADE ON,
APPROVE, REJECT, BLOCKED, PROTECT, RESIZE, LOTTERY — produced by independent panels with no
arbitration except a master call bolted on top. `master_panel()`'s own docstring records
why it was added: the dashboard *"used to shout several conflicting headlines at once — a
green BUY CALLS above a periscope reading 'price is FALLING' above a desk brief saying 'sit
out'."* The master call was added. The shouting underneath was never removed.

**Decisions taken.**

- **Keep server-rendered Python on localhost.** This is a single-user tool on one machine;
  an SPA would add a build step and a second language for no gain.
- **Adopt Jinja2.** One pure-Python dependency, and it is the lever that gets 350 lines of
  CSS and every HTML fragment out of Python. Templates in `04_live_system/templates/`,
  stylesheet in `04_live_system/static/`. This is worth breaking the current zero-dependency
  posture; nothing else about the repo is dependency-light anyway (pandas, scipy, torch).
- **One decision, one place.** The master call is the answer. Everything else is evidence
  and is visually subordinate — smaller, collapsed by default, and explicitly labelled as
  input rather than instruction. No second panel may render an action verb.
- **One question per tab**, written at the top of the tab in one sentence. If two panels
  answer the same question differently, one of them is deleted, not restyled.
- **Replace meta-refresh** with a small fetch that swaps panel bodies. Tab state, scroll
  position and open disclosures survive. This alone removes a large share of the felt
  confusion.

**Do.**

1. Extract the CSS to one stylesheet with named design tokens. Serve `/static/`.
2. Convert each panel to a function returning a **dict**, rendered by a template. Panels
   stop producing markup. This is what makes them testable.
3. Redesign the page around a fixed spine: **what to do now → why → what it costs →
   what happened last time**. The first screen answers only the first.
4. Cut the panel count. Concrete removals: `tldr_card` (retired), the scalp slide-out
   (its own text says the edge is "locally suggestive not yet significant" — it does not
   belong in a persistent fixed-position tab), and the second dashboard `mes_dashboard.py` (a whole separate server on port 8093).
5. Rewrite the empty states. A fresh clone currently shows four bare "missing" lines and no
   instruction. Every empty state names the file, why it is empty, and the command to fill it.
6. Promote the honest uncertainty the repo already computes but buries. `graduation.stats()`
   knows the measured-versus-modelled split; the credit log knows it needs 60 sessions and
   has 0. Those belong on the first screen, not in a footnote — they are the most decision-
   relevant numbers on the page.
7. Rename the product. The title is "Day + Swing Signals", the README calls it a trading
   dashboard, the plist calls it `gapscan`, the entry point is `gap_dashboard.py` and gaps
   are one of five tabs. Pick one name and use it everywhere.

**Done when.** A person who has never seen it can open the page and correctly state, in one
sentence, what the system thinks they should do today and how confident it is — without
scrolling and without reading a glossary.

---

## Phase 5 — a test suite that runs offline

**Why.** There is no unit test in the repo. The 20 files matching `test` are research
harnesses needing 16 GB of data and a network. Nothing verifies a single function offline,
which is why a page-killing exception and six contradictory recommendations both shipped.

**Do.**

1. `test/fixtures/` — frozen snapshot JSONs captured from a real session: high-gamma day,
   low-gamma day, market closed, UW down, stale data, empty `data/`.
2. Render tests over those fixtures. After Phase 4 panels return dicts, so assert on values:
   the gate is closed on a low-gamma fixture, no action verb appears outside the master call,
   the stale fixture produces a stale banner.
3. Gate tests for `risk_gates` — every rule in `ENFORCED` gets a test proving it blocks. The
   `events.json` case from Phase 2 gets one proving absence blocks rather than permits.
4. Pricing tests for `option_pricer` against recorded chains: a crossed market is refused, a
   wide package is refused, a missing strike returns `None` rather than a number.
5. Consolidate the pricing maths. There are at least three independent Black-Scholes
   implementations (`condor._bs`, `gex_periscope.bs_gamma`, `bt_options.bs`,
   `scripts/option_edge.bs`) with different default risk-free rates — 0.04 versus 0.045.
   One implementation, one test, one rate.
6. Add `pytest` to the TARS verify manifest alongside `scripts/verify.py`.

**Done when.** `tars verify` runs the suite offline in seconds and fails on any Phase 1 or
Phase 2 regression.

---

## Phase 6 — the platform

The engineering above makes it trustworthy. This makes it better than it was.

1. **Schema the snapshots.** 26 JSON files in `data/` are the entire interface between the
   engines and the UI, with no schema and no versioning — which is exactly how a `None`
   from a lapsed subscription reached a `:+` format string and took the page down, a
   failure `uw_client.py`'s comments describe at length. One dataclass per snapshot,
   validated on write and on read, with a version field.
2. **Make the calibration loop first-class.** `signal_weights.py` already distinguishes
   *measured* from *fabricated prior* and pins measured nulls at zero — the best idea in
   the codebase. Surface the tier next to every number the UI shows, so a prior never reads
   like a result. `uw_calibrate.py` already blends priors toward measurements; show the
   blend.
3. **Finish the one open validation that matters.** `RULES.md` §6.1 names it: log real SPX
   0DTE condor credits for 60 sessions and compare against the model-free breakevens (4.2%
   of width on high-gamma days, 9.6% on low). The counter reads **0 of 60**. Everything
   else in the 0DTE sleeve is unresolved until that finishes, so it should be the most
   prominent progress indicator in the product.
4. **Retire yfinance from anything that gates a decision.** 40 call sites in the live
   system against 4 sleep/retry mentions total; it is unofficial, rate-limited and delayed,
   and `option_pricer.py`'s own docstring concedes its quotes "can be wider than a real
   broker's routable market" and that the spread thresholds are provisional. Keep it for
   context; a paid quote feed is a spend decision and is yours to make.
5. **SQLite durability.** 11 `sqlite3.connect` sites, none setting WAL mode or a busy
   timeout, while `scan_all` writes the same databases the dashboard reads. Set both in one
   shared connection helper.
6. **Give the repo a history.** One squashed commit means no provenance and no bisect. From
   here, one logical change per commit.
7. **CI.** No `.github/`, no pre-commit, no linter config. Run `tars verify` plus the Phase
   5 suite on push. Add `ruff`.

---

## Phase 7 — housekeeping

Regenerate `MANIFEST.md` from `05_studies/scripts/build_bundle.py` (it is stale by 7 files
and claims "200 files total") and make freshness a verify check. Fix the README: it calls
the dashboard FastAPI, and it is `http.server` from the standard library. Fold the 26
research sweeps into `03_research/INDEX.md` with a one-line verdict each, so the reader
learns which sweeps produced surviving findings without opening 26 documents.

---

## Sequencing

```
Phase 1 (truth) ─┬─> Phase 4 (interface) ──> Phase 5 (tests) ──> Phase 6 (platform)
Phase 2 (visible failure) ─┘                        │
Phase 3 (portability) ──────────────────────────────┘
Phase 7 (housekeeping) — any time
```

Phases 1, 2 and 3 are independent of each other and can run in parallel. Phase 4 depends on
1. Phase 5 is far cheaper after 4, because panels returning dicts are assertable.

## As TARS missions

TARS is adopted, so this runs as missions, not as a to-do list. Each becomes
`missions/<slug>.md` with the phase's *Done when* as its acceptance contract, and each
build node is gated by the repo's verify manifest and reviewed by an opposite-vendor critic.

| mission | phase |
|---|---|
| `retire-superseded-verdicts` | 1 |
| `no-silent-failure` | 2 |
| `runs-anywhere` | 3 |
| `dashboard-information-architecture` | 4 |
| `offline-test-suite` | 5 |
| `snapshot-schemas` | 6 |

Start with `retire-superseded-verdicts`. It is the smallest, it unblocks Phase 4, and it is
the one where being wrong currently costs money.
