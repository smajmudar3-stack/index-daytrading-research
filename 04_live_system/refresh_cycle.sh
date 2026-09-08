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

# PATHS ARE DERIVED, NEVER TYPED. Everything below resolves from this script's own location,
# so the repo runs from any directory on any machine. Hardcoding an absolute home directory is
# what stops a working system from being installable by anyone else, and the `portability-
# ratchet` in verify.py only inspects .py files, so a shell script could carry one unnoticed.
#
# Each can still be overridden by the environment, which is how a second checkout or a
# different data location is pointed at without editing the file.
REPO="$(cd "$(dirname "$0")/.." && pwd)"

# A machine-specific override, git-ignored, for anything that differs per install -- chiefly
# IDT_DATA_ROOT, since the 16 GB of market data lives outside the repo and in a different place
# on every machine. Sourced before the defaults so it wins, and absent on a fresh clone, which
# is why the defaults below have to be sane on their own.
[ -f "$REPO/local.env" ] && . "$REPO/local.env"

export IDT_STATE_ROOT="${IDT_STATE_ROOT:-$REPO/04_live_system/data}"
export IDT_DATA_ROOT="${IDT_DATA_ROOT:-$REPO/data}"
export PYTHONPATH="$REPO"

# The interpreter: an explicit IDT_PYTHON wins, then the repo's own venv, then whatever is on
# PATH. A missing venv is reported rather than silently falling back to a system python that
# has none of the dependencies installed.
if [ -n "${IDT_PYTHON:-}" ]; then PY="$IDT_PYTHON"
elif [ -x "$REPO/venv/bin/python3" ]; then PY="$REPO/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then PY="$(command -v python3)"
else echo "no python3 found; run ./install.sh" >&2; exit 1
fi

echo "--- cycle $(date '+%Y-%m-%d %H:%M:%S %Z') ---"
# SELF-MAINTENANCE FIRST. Checks the age of the index universe and the macro calendar and
# renews them if they have aged out. Almost always a no-op -- it reads a date and returns --
# but it is the reason a stale asset gets replaced instead of quietly continuing to answer.
"$PY" maintenance.py 2>&1 | tail -3

"$PY" scan_all.py 2>&1 | tail -5
"$PY" build_snapshot.py 2>&1 | tail -2
