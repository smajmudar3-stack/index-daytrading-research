#!/bin/zsh
# Refresh the dated macro calendar from the official schedules.
#
# WHY A CLAUDE SESSION AND NOT A SCRIPT. `maintenance.py` refreshes everything a plain script
# can. The BLS release schedule is the exception: bls.gov returns HTTP 403 to any scripted
# request, custom user-agent and browser user-agent alike. `macro_calendar.refresh()` can use
# FRED instead, but that needs an API key which is not configured.
#
# So this uses the pattern the desk-note ingest already proves out: a headless Claude session
# reads the pages and writes the result through the module's own save(). Same shape, same
# reason: a source a script cannot read, read by something that can.
#
# Monthly is the right cadence. BLS publishes a year ahead and the Fed further still, so the
# dates rarely move; what changes is the window rolling forward. The module refuses anything
# unverified past 45 days, so monthly keeps a wide margin.
set -u
cd "$(dirname "$0")" || exit 1

# Derived, never typed — see the note in refresh_cycle.sh.
REPO="$(cd "$(dirname "$0")/.." && pwd)"

# A machine-specific override, git-ignored, for anything that differs per install -- chiefly
# IDT_DATA_ROOT, since the 16 GB of market data lives outside the repo and in a different place
# on every machine. Sourced before the defaults so it wins, and absent on a fresh clone, which
# is why the defaults below have to be sane on their own.
[ -f "$REPO/local.env" ] && . "$REPO/local.env"

export IDT_STATE_ROOT="${IDT_STATE_ROOT:-$REPO/04_live_system/data}"
export IDT_DATA_ROOT="${IDT_DATA_ROOT:-$REPO/data}"
export PYTHONPATH="$REPO"

if [ -n "${IDT_PYTHON:-}" ]; then PY="$IDT_PYTHON"
elif [ -x "$REPO/venv/bin/python3" ]; then PY="$REPO/venv/bin/python3"
else PY="$(command -v python3)"
fi

LOG="$REPO/logs/refresh_calendar.log"
mkdir -p "$(dirname "$LOG")"
echo "--- calendar refresh $(date '+%Y-%m-%d %H:%M:%S %Z') ---" >> "$LOG"

# The keyed path first: if a FRED key ever gets configured this costs nothing and is more
# reliable than reading three government web pages.
if "$PY" macro_calendar.py --refresh 2>&1 \
     | tee -a "$LOG" | grep -q "refreshed from FRED"; then
  echo "FRED path succeeded; no Claude session needed" >> "$LOG"
  exit 0
fi

command -v claude >/dev/null 2>&1 || { echo "claude CLI not on PATH" >> "$LOG"; exit 0; }

# `-p "$PROMPT"` FIRST, and `--allowedTools` as ONE comma-separated argument. Written as
# `--allowedTools WebFetch Bash Read Edit "$PROMPT"` the flag consumed the prompt string as a
# fourth tool name, leaving no prompt at all: "Input must be provided either through stdin or as
# a prompt argument when using --print". Same shape as ingest_desk_notes.sh, which works.
read -r -d '' PROMPT <<'PROMPT'
Refresh the dated macro-release calendar for the index-daytrading-dev dashboard.

Read the CURRENT schedules from these official pages with WebFetch:
  https://www.bls.gov/schedule/news_release/cpi.htm      (CPI, monthly, 08:30 ET)
  https://www.bls.gov/schedule/news_release/ppi.htm      (PPI, monthly, 08:30 ET)
  https://www.bls.gov/schedule/news_release/empsit.htm   (Employment Situation, 08:30 ET)
  https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm  (FOMC, decision 14:00 ET)

Then write them into the calendar by running python in 04_live_system with
PYTHONPATH=$HOME/index-daytrading-dev and IDT_STATE_ROOT=$PWD/data, calling
macro_calendar.save({"verified_on": "<today, YYYY-MM-DD>", "sources": [...the four URLs...],
"events": [...]}).

Each event is a dict with:
  date        "YYYY-MM-DD"      the RELEASE date, not the reference month
  time        "08:30" or "14:00"
  label       e.g. "August CPI", "FOMC decision + projections"
  kind        "inflation" | "fed" | "jobs"
  importance  "high" for CPI, FOMC and the jobs report; "medium" for PPI
  moves       one short sentence on what the print actually moves

Rules that matter:
- Include every release from today through about four months out. Past dates are harmless
  (they are filtered on read) but do not omit anything upcoming.
- For a two-day FOMC meeting, the event date is the SECOND day, when the statement lands.
- Do NOT invent a date. If a page will not load or a month is missing from it, leave that entry
  out and say so in your final message. A wrong CPI date moves every expiry in the book, which
  is worse than a missing one.
- Do not change any other file.

Finish by printing the calendar (python macro_calendar.py) so the log shows what was written.
PROMPT

claude -p "$PROMPT" \
  --permission-mode acceptEdits \
  --allowedTools "WebFetch,Bash,Read,Edit" \
  >> "$LOG" 2>&1

echo "exit=$? $(date '+%H:%M:%S')" >> "$LOG"
