#!/bin/zsh
# One refresh cycle for the DEV dashboard.
#
# The dev clone reads its snapshots from its OWN state root, but the only
# scheduled job on this machine (com.daytrading.snapshot) writes to the MAIN
# repo's data dir. So the dev page swapped its HTML every 60s and rendered the
# same numbers every time -- live-looking and frozen. This gives dev its own
# cycle.
#
# scan_all writes the ~26 panel snapshots; build_snapshot writes the aggregate
# the header reads. Order matters: the aggregate summarises the panels.
set -u
cd "$(dirname "$0")" || exit 1

export IDT_STATE_ROOT="$PWD/data"
export IDT_DATA_ROOT="/Users/sahilmajmudar/index-daytrading/data"
export PYTHONPATH="$HOME/index-daytrading-dev"
PY="/Users/sahilmajmudar/index-daytrading/venv/bin/python3"

echo "--- cycle $(date '+%Y-%m-%d %H:%M:%S %Z') ---"
"$PY" scan_all.py 2>&1 | tail -5
"$PY" build_snapshot.py 2>&1 | tail -2
