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
  6. no live module recommends a strategy this repo's own research refuted

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
    # Phase 4: the new dashboard. gap_dashboard stays in the list because it is still
    # reachable via `idt serve --legacy` for one release.
    "dashboard_app",
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


# ---------------------------------------------------------------------------
# Check 6: the retired-advice guard.
#
# Phase 1 of docs/PLAN.md removed the refuted trades from the dashboard, both
# desktop notifications and both engines that manufactured them. Without a gate,
# one edit puts any of it back, and the failure is silent: the page still renders,
# it just tells you to take a trade measured at -10% to -11% per trade.
#
# The hard part is that REFUTING a claim requires NAMING it. The glossary explains
# why "below the flip = buy premium" is wrong, the footer says what is rejected,
# and docs/VERDICT_LOG.md is nothing but retired claims. A naive grep fails on its
# first run and then gets ignored, which is worse than no gate.
#
# So this matches the IMPERATIVE, not the mention. Two rules:
#   1. Only files that PRODUCE operator-facing output are scanned. The record of
#      what was wrong lives in docs/ and 07_superseded/ and is exempt.
#   2. A line is exempt when it carries a refutation marker on the same line: a
#      measured loss, a retired/refuted/rejected word, or a pointer to the verdict
#      log. That is how the glossary and the footer legitimately say the words.
RETIRED_ADVICE = re.compile(
    r"\bbuy\s+(?:a|an|the)?\s*(?:naked\s+|atm\s+|otm\s+|itm\s+|0dte\s+|long\s+)*(?:call|put)s?\b"
    r"|\bBUY\s+(?:CALLS|PUTS)\b"
    r"|\bnaked\s+(?:call|put)s?\s+(?:have|has)\b"
    r"|\bpremium\s+has\s+fuel\b"
    r"|\bhas\s+the\s+most\s+fuel\b"
    r"|\bpress\s+size\b"
    r"|\bIDEAL\s+naked\b"
    r"|\bgo\s+naked\b|\bnaked\s+is\s+fine\b"
    r"|below\s+(?:the\s+)?flip\s*=\s*(?:puts|calls|buy)"
    r"|\bfavor\s+(?:CALLS|PUTS)\b",
    re.I)

# Comments and docstrings are EXEMPT, computed from the AST rather than guessed.
#
# This is not a loophole, it is the risk model. The guard exists to stop the product
# telling the operator to take a refuted trade. A comment cannot reach the operator,
# and the comments that quote the retired wording are the most valuable lines in these
# files: they record what was removed and why, which is exactly what stops someone
# putting it back. A gate that forced their deletion would destroy the institutional
# memory it exists to protect.
#
# What is NOT exempt is any string a running program can print, render or send to a
# model. That includes LLM system prompts, which is how the trading agent's own HARD
# RULES were found still instructing the refuted trade.
#
# For the rare executable line that must contain the wording (this file's own patterns,
# and the renderer's filter), the opt-out is explicit and greppable: `# allow: retired-advice`.


def _exempt_lines(path):
    """Line numbers that are comment-only or inside a docstring."""
    exempt = set()
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return exempt
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or "allow: retired-advice" in line:
            exempt.add(i)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return exempt
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            for i in range(first.lineno, (first.end_lineno or first.lineno) + 1):
                exempt.add(i)
    return exempt


# A line saying the words in order to refute them is the point of the exercise.
REFUTATION_MARKER = re.compile(
    r"refut|retired|rejected|REJECTED|superseded|VERDICT_LOG"
    # The repo writes a minus as U+2212 in prose and as ASCII in code. Matching only
    # ASCII meant a line that DID carry its refutation number was flagged as advice,
    # which is the false positive that makes a gate get switched off.
    r"|measured\s+at|tested\s+at|lost\s+\d|[-−]\d+(?:\.\d+)?%\s*(?:per\s+trade|/trade|to\s)"
    r"|used\s+to\s+(?:say|return|read|end|be)|no\s+longer|must\s+not|never\s+again"
    r"|hard-blocked|not\s+a\s+signal|is\s+WRONG",
    re.I)

# Only what the operator can end up reading or acting on. The history is exempt.
ADVICE_SCAN_DIRS = ("04_live_system", "idt", "scripts")


def advice_files():
    for d in ADVICE_SCAN_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames
                           if x not in ("data", "__pycache__", "templates", "static")]
            for f in sorted(filenames):
                if f.endswith(".py"):
                    yield os.path.join(dirpath, f)


def retired_advice_hits():
    hits = []
    for p in advice_files():
        if os.path.abspath(p) == os.path.abspath(__file__):
            continue                      # this file defines the patterns
        exempt = _exempt_lines(p)
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            if i in exempt or REFUTATION_MARKER.search(line):
                continue
            if RETIRED_ADVICE.search(line):
                hits.append(f"{os.path.relpath(p, ROOT)}:{i}: {line.strip()[:100]}")
    return hits


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

    # 6. retired advice -----------------------------------------------------
    hits = retired_advice_hits()
    check("retired-advice", not hits,
          f"{len(list(advice_files()))} live/shared modules recommend nothing this repo refuted"
          if not hits else f"{len(hits)} instance(s): " + " | ".join(hits[:4]))

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
