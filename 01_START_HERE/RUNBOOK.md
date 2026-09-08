# Runbook

Everything runs through one command. `idt --help` lists it.

## First run, on any machine

```bash
python3 -m venv venv
venv/bin/pip install -e ".[dev]"
idt bootstrap          # creates the state dir, then says what is still missing
idt serve              # http://127.0.0.1:8094
```

`idt bootstrap` prints an honest inventory: which API keys are set, and whether the
16 GB of market data is installed. **None of it is required to render the dashboard.**
Each missing key switches off one panel, which then says so on screen instead of
showing a blank.

The market data is not in git by design (see [../06_data_guide/DATA.md](../06_data_guide/DATA.md)).
Every backtest in `05_studies/` needs it; the live dashboard does not. If you have a
copy elsewhere, point at it:

```bash
export IDT_DATA_ROOT=/path/to/index-daytrading/data
venv/bin/python scripts/bootstrap_data.py     # reports what is present and what is not
```

## The dashboard

Four views, each a real URL, each answering one stated question:

| URL | answers |
|---|---|
| `/today` | Is there anything to do right now, and how much should I trust it? |
| `/evidence` | How much of this is measured, and how much is a guess? |
| `/markets` | What is the tape doing? Context only, no recommendations. |
| `/risk` | What may I risk, what is switched off, what is stale? |

Only the decision card on `/today` ever states an action. If a panel elsewhere starts
issuing one, `test_only_the_answer_panel_may_issue_an_action` fails.

```bash
idt serve                # the dashboard
idt serve --legacy       # the pre-Phase-4 single-file page, for one release, to
                         # check a number that looks wrong against the old one
```

The page refreshes its panels in place every 60 seconds. Your view, scroll position and
open disclosures survive it; a failed refresh says so in the status bar rather than
looking like fresh data.

## Health check, before trusting any number on screen

```bash
idt audit                # exits 1 on any hard failure or unrunnable check
idt audit --strict       # also fails on warnings
```

23 checks against independent sources: spot accuracy, data freshness, gamma sanity, UW
API health, weight registry integrity, stale-data guards, scorecard consistency,
template render and HTTP reachability. It checks **values, not exit codes**, because
the bugs in this repo's history were data that was returned but not correct, displayed
as if live.

It reports three outcomes, and the third matters: a check that FAILED and a check that
COULD NOT RUN are different problems. "SPX spot is 0.4% off" is a data bug; "no
reference quote to compare against" is a network or install problem.

**It used to always exit 0**, so nothing could gate on it. That is fixed, but if you see
an old cron or launchd job calling it, check that job reads the exit code.

## Refresh signals manually

```bash
idt refresh                                  # one full cycle
venv/bin/python 04_live_system/scorecard.py  # per-tab hit rate and calibration
```

A cycle writes `04_live_system/data/cycle_report.json`: every step, what it returned,
what failed and why, and how long it took. The dashboard's status bar reads it. A step
that throws does not stop the later steps, but it can no longer look like a quiet day.

## Verify before claiming anything works

```bash
venv/bin/python scripts/verify.py    # 7 offline checks
venv/bin/python -m pytest test/ -q   # 47 offline tests
venv/bin/ruff check .
```

All three are in `.tars/profile.json`, so `tars verify .` runs the set, and CI runs the
same three commands. None needs the network or the market data.

If you add a file, regenerate the index or the manifest check will fail:

```bash
venv/bin/python scripts/build_manifest.py
```

## Unusual Whales

```bash
venv/bin/python -c "import sys; sys.path.insert(0,'04_live_system'); import uw_endpoints as ue; print(ue.profile('SPY'))"
venv/bin/python 04_live_system/uw_calibrate.py     # re-fit weights from logged outcomes
```

83 endpoints are catalogued in `uw_endpoints.py`. Quota is 30,000 calls a day, and the
per-name loop costs about 4, which is why scaling the swing universe past ~100 names
needs the server-side `/api/screener/stocks` endpoint rather than a client-side loop.

**A lapsed subscription is not a missing key.** It returns 401 with a valid key still
present, which once made `available()` report healthy and then crashed the page on
null-valued fields. Every outward-facing module now reports which of the two it is; see
the Service health panel on `/risk`.

## Re-running a study

Everything in `05_studies/` is standalone and needs `IDT_DATA_ROOT` to point at real
data:

```bash
venv/bin/python 05_studies/scripts/structure_lab.py    # 26 structures on real quotes
venv/bin/python 05_studies/scripts/blackswan_test.py   # 10.5M far-OTM purchases
venv/bin/python 05_studies/scripts/bigmove_hunt.py     # tail-move predictors
venv/bin/python 05_studies/scripts/swing_lab.py        # swing signal harness
```

Several take 10+ minutes and hit the 14 GB Dolt database. If the data is absent they
now fail with a message naming the fix, rather than a traceback three frames inside
pandas.

Read [../02_findings/METHODOLOGY_TRAPS.md](../02_findings/METHODOLOGY_TRAPS.md) before
writing a new one. Four of the twelve traps in it produced fake winning strategies in
this repo before being caught.

## Known constraints

- **Contract budget: $1,000 to $3,000.** Sizing assumes about half the account is
  deployed. The advisor filters out anything outside that range.
- **Recommendations are gated on backtested positive expectancy.** If the numbers say a
  trade loses, the dashboard will not surface it, even if you ask for that structure.
- **Paper only.** `risk_gates.DRY_RUN` is `True`, `LIVE_AGENT` is `False`, and no
  order-placement code exists anywhere in this repo. A test asserts the second part
  rather than taking it on faith.
- **A missing or stale `data/events.json` BLOCKS trading.** FOMC and CPI dates are hand
  entered. The gate used to pass on any read failure, so an absent calendar looked
  exactly like a clear day. Its age is on the `/risk` view.
