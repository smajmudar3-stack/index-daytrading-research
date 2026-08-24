# Runbook

## The dashboard

Runs on **http://localhost:8094**, kept alive by launchd.

```bash
cd ~/index-daytrading

# start / stop / restart
launchctl load   ~/Library/LaunchAgents/com.gapscan.dashboard.plist
launchctl unload ~/Library/LaunchAgents/com.gapscan.dashboard.plist

# run in the foreground instead (to see tracebacks)
venv/bin/python3 gap_dashboard.py

# logs
tail -f logs/gapdash.err
```

Note the plist invokes `~/quant-factory/venv/bin/python3`, not this repo's venv.
Both work; the quant-factory venv is what launchd is pinned to.

## Health check before trusting any number on screen

```bash
venv/bin/python3 audit_dash.py
```

23 checks: spot accuracy, data freshness, gamma sanity, UW API health, weight
registry integrity, stale-data guards, scorecard consistency, template render,
and HTTP reachability. Run this first whenever something looks wrong — most of
the bugs in this repo's history were caught by a check that already existed.

## Refresh signals manually

```bash
venv/bin/python3 refresh_signal.py     # recompute all tabs
venv/bin/python3 scan_all.py           # full universe scan (script, not a main())
venv/bin/python3 scorecard.py          # per-tab hit rate and calibration
```

`scan_all.py` is a **script, not a function** — it executes at import. Editing a
`def main():` in it does nothing. This caused several silent no-op edits.

## Unusual Whales

```bash
venv/bin/python3 -c "import uw_endpoints as ue; print(ue.profile('SPY'))"
venv/bin/python3 uw_calibrate.py       # re-fit weights from logged outcomes
```

API key lives in the environment. 83 endpoints are catalogued in
`uw_endpoints.py`. Quota is 30,000 calls/day — the per-name loop costs ~4 calls,
which is why scaling the swing universe past ~100 names requires the
server-side `/api/screener/stocks` endpoint rather than a client-side loop.

## Re-running a study

Everything in `05_studies/` is standalone:

```bash
venv/bin/python3 scripts/structure_lab.py     # 26 structures on real quotes
venv/bin/python3 scripts/blackswan_test.py    # 10.5M far-OTM purchases
venv/bin/python3 scripts/bigmove_hunt.py      # tail-move predictors
venv/bin/python3 scripts/swing_lab.py         # swing signal harness
```

These read from `data/` — see [../06_data_guide/DATA.md](../06_data_guide/DATA.md).
Several take 10+ minutes and hit the 14 GB Dolt database.

## Known constraints

- **Contract budget: $1,000–3,000.** Sizing assumes ~50% of account deployed.
  The advisor filters out anything outside that range.
- **Recommendations are gated on backtested positive expectancy.** If the
  numbers say a trade loses, the dashboard will not surface it, even if the
  structure is requested.
- **Paper-only execution.** Nothing in this repo places live orders.
