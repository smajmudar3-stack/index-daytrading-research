#!/usr/bin/env python3
"""Offline verify gate for this repo — the TARS verify manifest points here.

Deliberately needs NO network and NO `data/` directory. The 16 GB of market data
is not in git (see 06_data_guide/DATA.md), so a gate that required it would be
skipped on every fresh clone, and a skipped gate is not a gate.

What it checks:
  1. every .py file in the working tree compiles
  2. the live modules that have no data/network dependency still import
  3. no live module imports a module that lives under 05_studies/
  4. no file hardcodes a foreign home directory
  5. no study module runs script work at import

Run:  venv/bin/python scripts/verify.py
"""
import ast
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "04_live_system")
STUDIES = os.path.join(ROOT, "05_studies")

# Modules that import cleanly with no data/ dir and no network call at import
# time. Anything that reads a parquet/csv at module level is deliberately absent
# — see the "runs work at import" finding in the audit.
SMOKE = [
    "dashboard", "gap_dashboard", "rules", "risk_gates", "sizing",
    "option_pricer", "scorecard", "session", "sleeves", "positions", "ticket",
    "growth_plan", "graduation", "signal_weights", "uw_client", "uw_endpoints",
    "swing_signals", "committee", "condor", "blackswan_panel", "edge_panel",
    # Fixed by the bundle split repair: mes_signals moved here from 05_studies,
    # so the documented launchd/refresh entry point imports again.
    "mes_signals", "mes_dashboard", "signals_all",
]

# The bundle split filed the live system and the research harnesses in separate
# directories and broke four modules across the seam. This set is now EMPTY and
# must stay that way: a live module that imports a study module cannot run from
# either directory, and the gate fails rather than absorbing it silently.
#
# How the four were fixed, for the next person who wonders where they went:
#   signals_all, mes_dashboard  <- mes_signals moved INTO 04_live_system (it is a
#                                  live engine: it writes the snapshot the live
#                                  dashboard reads)
#   sizing_curve, final_system  <- moved OUT to 05_studies (both are research
#                                  harnesses that rebuild a panel and print a
#                                  table; neither is part of the live system)
BUNDLE_BROKEN = {}

# Was 53. Every one of those files hardcoded the original author's home directory
# and was unrunnable on any other machine; they resolve through idt.paths now.
# The number may go DOWN freely. It may not go up.
#
# Docstrings and comments are exempt, because several of them name the old path
# on purpose to record what was wrong. The gate is about paths the code resolves,
# not about prose describing a defect that has been fixed.
FOREIGN_HOME = re.compile(r"/Users/(?!sholo/)[a-z0-9._-]+/")
FOREIGN_HOME_BASELINE = 0

failures = []


def check(name, ok, detail):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        failures.append(name)


def worktree_py():
    """Every .py in the working tree, tracked or not.

    `git ls-files` alone was wrong twice over: it lists a file that has been moved
    but not yet staged (and then the compile check dies on open()), and it misses
    a file that has been written but not yet added — which is exactly when a
    syntax error is most likely to be sitting in it.
    """
    def run(*args):
        return subprocess.run(["git", *args], cwd=ROOT,
                              capture_output=True, text=True).stdout.split()
    paths = set(run("ls-files", "*.py")) | set(run("ls-files", "--others", "--exclude-standard", "*.py"))
    return sorted(p for p in (os.path.join(ROOT, x) for x in paths) if os.path.isfile(p))


def _prose_lines(src, tree):
    """Line numbers that hold a docstring or a comment, and nothing else."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = n.body[0] if n.body else None
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) \
                    and isinstance(b.value.value, str):
                out |= set(range(b.lineno, b.end_lineno + 1))
    for i, line in enumerate(src.split("\n"), 1):
        if line.lstrip().startswith("#"):
            out.add(i)
    return out


def foreign_home_paths(src):
    """Foreign-home paths the code would actually resolve."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return FOREIGN_HOME.findall(src)
    prose = _prose_lines(src, tree)
    return [m.group(0) for i, line in enumerate(src.split("\n"), 1)
            if i not in prose for m in FOREIGN_HOME.finditer(line)]


def study_files():
    for d in (STUDIES, os.path.join(STUDIES, "scripts")):
        for f in sorted(os.listdir(d)):
            if f.endswith(".py"):
                yield os.path.join(d, f)


def main():
    print("VERIFY — index-daytrading-research")

    # 1. syntax ------------------------------------------------------------
    files = worktree_py()
    bad = []
    for p in files:
        try:
            ast.parse(open(p, encoding="utf-8").read(), filename=p)
        except SyntaxError as e:
            bad.append(f"{os.path.relpath(p, ROOT)}:{e.lineno} {e.msg}")
    check("compile", not bad, f"{len(files)} .py files in the working tree" if not bad
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
    elsewhere = {os.path.basename(p)[:-3] for p in study_files()}
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
          "no live module imports a 05_studies module" if not new
          else "newly broken: " + ", ".join(f"{k}->{v}" for k, v in new.items()))

    # 4. portability ratchet ----------------------------------------------
    n = 0
    hits = []
    for p in files:
        c = len(foreign_home_paths(open(p, encoding="utf-8").read()))
        if c:
            hits.append(os.path.relpath(p, ROOT))
        n += c
    check("portability-ratchet", n <= FOREIGN_HOME_BASELINE,
          f"{n} hardcoded foreign-home path(s), baseline {FOREIGN_HOME_BASELINE}"
          + ("" if n <= FOREIGN_HOME_BASELINE else " in " + ", ".join(hits[:4])))

    # 5. no script work at import ------------------------------------------
    # A bare `import` of a study used to hit the network or read a 600 MB parquet.
    # These are the unambiguous cases: a loop, a with/try block or a print at
    # module level is a script body, and it belongs under a main guard.
    loose = []
    for p in study_files():
        tree = ast.parse(open(p, encoding="utf-8").read())
        for s in tree.body:
            if isinstance(s, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)):
                loose.append(f"{os.path.relpath(p, ROOT)}:{s.lineno} {type(s).__name__.lower()} at module level")
            elif isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) \
                    and ast.unparse(s.value.func) == "print":
                loose.append(f"{os.path.relpath(p, ROOT)}:{s.lineno} print at module level")
    check("import-time-work", not loose,
          f"{len(list(study_files()))} study modules import without running"
          if not loose else "; ".join(loose[:5]))

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
