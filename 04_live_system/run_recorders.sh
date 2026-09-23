#!/bin/zsh
# The two market recorders, kept alive by launchd (com.daytrading.recorders.plist).
# Record only. Nothing here places an order. Paths derive from this file's location,
# exactly as refresh_cycle.sh does, so the job runs from any checkout.
set -u
cd "$(dirname "$0")" || exit 1
REPO="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$REPO/local.env" ] && . "$REPO/local.env"
export IDT_STATE_ROOT="${IDT_STATE_ROOT:-$REPO/04_live_system/data}"
export PYTHONPATH="$REPO:$REPO/04_live_system"
if [ -n "${IDT_PYTHON:-}" ]; then PY="$IDT_PYTHON"
elif [ -x "$REPO/venv/bin/python3" ]; then PY="$REPO/venv/bin/python3"
else PY="$(command -v python3)"; fi
mkdir -p "$REPO/logs"
"$PY" polymarket_recorder.py >> "$REPO/logs/polymarket_recorder.out" 2>&1 &
P1=$!
"$PY" crypto_venue_recorder.py >> "$REPO/logs/crypto_venue_recorder.out" 2>&1 &
P2=$!
trap 'kill $P1 $P2 2>/dev/null' TERM INT
wait
