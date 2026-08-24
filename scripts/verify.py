#!/usr/bin/env python3
"""Offline verify gate for this repo — the TARS verify manifest points here.

Deliberately needs NO network and NO `data/` directory. The 16 GB of market data
is not in git (see 06_data_guide/DATA.md), so a gate that required it would be
skipped on every fresh clone, and a skipped gate is not a gate.

What it checks:
  1. every tracked .py file compiles
  2. the live modules that have no data/network dependency still import
  3. the set of live modules broken by the bundle split does not grow
  4. the count of hardcoded foreign-home paths does not grow

Run:  venv/bin/python scripts/verify.py
"""
import ast
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "04_live_system")

# Modules that import cleanly with no data/ dir and no network call at import
# time. Anything that reads a parquet/csv at module level is deliberately absent
# — see the "runs work at import" finding in the audit.
SMOKE = [
    "dashboard", "gap_dashboard", "rules", "risk_gates", "sizing", "sizing_curve",
    "option_pricer", "scorecard", "session", "sleeves", "positions", "ticket",
    "growth_plan", "graduation", "signal_weights", "uw_client", "uw_endpoints",
    "swing_signals", "committee", "condor", "blackswan_panel", "edge_panel",
]

# Known-broken by the bundle split: these live under 04_live_system/ but import
# modules that were filed under 05_studies/, so they cannot run from either
# directory. Ratchet — fixing one means deleting it from this set, and a NEW
# break fails the gate rather than being absorbed silently.
BUNDLE_BROKEN = {
    "final_system": "multi_edge",
    "mes_dashboard": "mes_signals",
    "signals_all": "mes_signals",
    "sizing_curve": "backtest_daily",
}

# Ratchet, not a target. 05_studies/ hardcodes the original author's home
# directory; every one of those files is unrunnable on any other machine. The
# number may go DOWN freely. It may not go up.
FOREIGN_HOME = re.compile(r"/Users/(?!sholo/)[a-z0-9._-]+/")
FOREIGN_HOME_BASELINE = 53

failures = []


def check(name, ok, detail):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        failures.append(name)


def tracked_py():
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [os.path.join(ROOT, p) for p in out]


def main():
    print("VERIFY — index-daytrading-research")

    # 1. syntax ------------------------------------------------------------
    files = tracked_py()
    bad = []
    for p in files:
        try:
            ast.parse(open(p, encoding="utf-8").read(), filename=p)
        except SyntaxError as e:
            bad.append(f"{os.path.relpath(p, ROOT)}:{e.lineno} {e.msg}")
    check("compile", not bad, f"{len(files)} tracked .py files" if not bad
          else "; ".join(bad[:5]))

    # 2. import smoke ------------------------------------------------------
    sys.path.insert(0, LIVE)
    broke = []
    smoke = [x for x in SMOKE if x not in BUNDLE_BROKEN]
    for m in smoke:
        try:
            __import__(m)
        except Exception as e:
            broke.append(f"{m}: {type(e).__name__} {str(e)[:70]}")
    check("import-smoke", not broke, f"{len(smoke)} live modules import"
          if not broke else "; ".join(broke[:5]))

    # 3. bundle-split breakage ratchet -------------------------------------
    live_mods = {f[:-3] for f in os.listdir(LIVE) if f.endswith(".py")}
    study_dirs = [os.path.join(ROOT, "05_studies"),
                  os.path.join(ROOT, "05_studies", "scripts")]
    elsewhere = set()
    for d in study_dirs:
        elsewhere |= {f[:-3] for f in os.listdir(d) if f.endswith(".py")}
    found = {}
    for f in sorted(os.listdir(LIVE)):
        if not f.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(LIVE, f), encoding="utf-8").read())
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                names.add(n.module.split(".")[0])
        stray = (names & elsewhere) - live_mods
        if stray:
            found[f[:-3]] = sorted(stray)[0]
    new = {k: v for k, v in found.items() if k not in BUNDLE_BROKEN}
    check("bundle-split-ratchet", not new,
          f"{len(found)} known-broken live module(s), no new ones" if not new
          else "newly broken: " + ", ".join(f"{k}->{v}" for k, v in new.items()))

    # 4. portability ratchet ----------------------------------------------
    n = 0
    for p in files:
        n += len(FOREIGN_HOME.findall(open(p, encoding="utf-8").read()))
    check("portability-ratchet", n <= FOREIGN_HOME_BASELINE,
          f"{n} hardcoded foreign-home path(s), baseline {FOREIGN_HOME_BASELINE}"
          + ("" if n <= FOREIGN_HOME_BASELINE else " — new ones were added"))

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
