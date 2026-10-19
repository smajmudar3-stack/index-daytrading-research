#!/bin/zsh
# The edge hunt as a tree that grows on its own. Once a week a headless Claude session reads
# the strategy tree (every hypothesis this repo has tested, with its verdict), picks the
# most promising UNTESTED branch, writes the study that tests it the way everything here is
# tested (real prices, real costs, three splits, the noise bar), runs it, records the verdict
# as a new node, and proposes the next branches under it. Dead branches stay on the tree
# with their numbers so they are never re-tested by accident.
#
# Departments the tree covers: stocks long and short, puts and calls bought and sold,
# covered calls, debit and credit spreads, condors and flies, index overlays, futures and
# FX via ETFs, prediction markets, crypto and memecoins. A branch is ANY rule with an entry,
# an exit, a universe and a cost model; nothing is out of scope and nothing is in the tree
# without a measurement.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)" || exit 1      # resolve before any cd: $0 may be relative
REPO="$(dirname "$HERE")"
cd "$HERE" || exit 1
[ -f "$REPO/local.env" ] && . "$REPO/local.env"
export IDT_STATE_ROOT="${IDT_STATE_ROOT:-$REPO/04_live_system/data}"
export IDT_DATA_ROOT="${IDT_DATA_ROOT:-$REPO/data}"
export PYTHONPATH="$REPO:$REPO/04_live_system:$REPO/05_studies"
export PATH="/opt/homebrew/bin:$PATH"
if [ -n "${IDT_PYTHON:-}" ]; then PY="$IDT_PYTHON"
elif [ -x "$REPO/venv/bin/python3" ]; then PY="$REPO/venv/bin/python3"
else PY="$(command -v python3)"; fi
CLAUDE="${CLAUDE_BIN:-/opt/homebrew/bin/claude}"
LOG="$REPO/logs/branch_hunt.out"
mkdir -p "$REPO/logs"
echo "--- branch hunt $(date '+%Y-%m-%d %H:%M:%S %Z') ---" >>"$LOG"

read -r -d '' PROMPT <<PROMPT_END
You are the research desk of this repo. Grow the strategy tree by ONE measured branch.

1. Read docs/strategy_tree.json (every hypothesis tested here, with verdicts and children),
   02_findings/METHODOLOGY_TRAPS.md (the sixteen ways a backtest lies here) and
   02_findings/WHAT_WORKS.md. Then read 02_findings/online_methods.md for the full inventory.
2. Choose the single most promising node whose status is "untested" or "proposed" — prefer
   one whose parent measured positive, whose data is ON THIS MACHINE (DATA_ROOT/opt_panel:
   daily OHLCV 2018-2026 for 2,300 names, option chains 2019-05..2026-08 by month, earnings,
   EPS history, quarterly statements; signal_panel.parquet with 68 weekly factors; GMGN and
   pump.fun recorders; SPY/QQQ minute bars), and that can be measured with real costs.
3. Write 05_studies/<slug>_test.py in the house style (docstring stating the claim, the
   data, the costs, the splits A 2019-21 / B 2022-23 / C 2024-26, the noise bar sqrt(2 ln N)
   for the N cells scored; entries at the NEXT open or at the ask; every number per $ of
   risk). Run it with: $PY 05_studies/<slug>_test.py  (use IDT_DATA_ROOT=$IDT_DATA_ROOT).
   Fix it until it runs; keep it under ~20 minutes of compute (load chain months one year at
   a time).
4. Write 02_findings/<slug>.md: the verdict in one line, the table, what it rules in or out,
   and two or three child branches it suggests (each with the exact rule to test next).
5. Update docs/strategy_tree.json: set this node's status to "measured", add verdict,
   numbers, the study and findings paths, the date; append the child nodes as "proposed".
   Append one verdict row to the table in 02_findings/online_methods.md.
6. Run $PY scripts/build_manifest.py and $PY scripts/verify.py and $PY -m ruff check . ;
   fix what fails. Do NOT commit. Print the node slug, its verdict line, and the children.

Rules: nothing places an order; no non-public information; a result that looks too good
(t > 4, Sharpe > 2) is checked against trap 6 (measuring from before the signal is known)
and trap 5 (one day driving a matrix) before it is written down; "not measurable from
here" is a valid verdict and is recorded as one.
PROMPT_END

"$CLAUDE" -p "$PROMPT" --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch" >>"$LOG" 2>&1
STATUS=$?
echo "claude exit: $STATUS" >>"$LOG"
if [ "$STATUS" -ne 0 ] && tail -c 4000 "$LOG" | grep -q "Failed to authenticate"; then
  osascript -e 'display notification "Claude login expired: the weekly branch hunt did not run. Run /login in Claude Code." with title "Branch hunt failed" sound name "Basso"' 2>/dev/null || true
fi
tail -3 "$LOG"
exit 0
