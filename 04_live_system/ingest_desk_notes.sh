#!/bin/zsh
# Pull any NEW Crown Macro Letter desk notes out of Gmail and fold them into the macro
# overlay, then rebuild the weekly book from the updated read.
#
# WHY A HEADLESS CLAUDE SESSION RATHER THAN THE GMAIL API. Reading the mailbox needs
# OAuth credentials this repo does not have and should not carry. The Gmail connector is
# already authenticated for this account inside Claude Code, so the cheapest correct
# path is to let a short headless session do the read, structure the note, and hand the
# JSON to `desk_notes.py --merge-json`. The session does the parsing it is already
# holding the text for; no second model call re-reads it.
#
# IDEMPOTENT BY DESIGN. `merge_note` refuses a (subject, date) pair it has already
# ingested, so running this five times a day costs nothing after the first hit of each
# note. It is safe to run more often than the notes arrive.
#
# FAILS VISIBLY. If the session cannot reach Gmail, the overlay simply does not advance,
# it ages, and `weekly_swing` starts refusing to produce cards once it passes two
# sessions old. That is the intended behaviour: no macro read means no macro-conditioned
# trades, not stale ones.
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
CLAUDE="${CLAUDE_BIN:-/opt/homebrew/bin/claude}"
LOG="$PWD/data/desk_notes_ingest.log"

echo "--- desk-note ingest $(date '+%Y-%m-%d %H:%M:%S %Z') ---" >>"$LOG"

# The full list of what has already been read, not a high-water date. Forward times run
# 1-5 hours behind the notes' own send times and do NOT preserve order, so a cutoff can
# skip an earlier-sent note that arrived late. See desk_notes.py --ingested-list.
SEEN="$("$PY" desk_notes.py --ingested-list 2>/dev/null)"
echo "already ingested:" >>"$LOG"
echo "${SEEN:-  (none)}" >>"$LOG"

# WHO SENDS THE NOTES IS CONFIGURATION, NOT SOURCE. The address of the person forwarding
# them is a third party's personal information; committing it to a public repository
# publishes their address for anyone to scrape, and they never agreed to that. It lives in
# .env instead, which is git-ignored.
DESK_NOTE_SENDER="${DESK_NOTE_SENDER:-$("$PY" -c 'import sys; sys.path.insert(0, "'"$REPO"'"); from idt import keys; print(keys.get("DESK_NOTE_SENDER") or "")' 2>/dev/null)}"
DESK_NOTE_SUBJECT="${DESK_NOTE_SUBJECT:-Desk note}"
if [ -z "$DESK_NOTE_SENDER" ]; then
  echo "DESK_NOTE_SENDER is not set in .env — nothing to search for, skipping ingest" >>"$LOG"
  exit 0
fi

read -r -d '' PROMPT <<PROMPT_END || true
Ingest any new macro desk notes into this repo's macro overlay.

1. Search Gmail for threads matching:
     from:${DESK_NOTE_SENDER} subject:"${DESK_NOTE_SUBJECT}" newer_than:4d
   Ignore anything that is not a "${DESK_NOTE_SUBJECT}".

2. These notes are ALREADY in the overlay (tab-separated, note send time then subject):
${SEEN:-   (none yet - ingest everything you find)}

   Skip a note only if its own send time AND subject match a line above. Do NOT use the
   newest of those as a cutoff: the forwards arrive out of order relative to the notes'
   send times, so an earlier-sent note can turn up after a later-sent one and must still
   be ingested. If every note found is already listed, print "no new notes" and stop
   without writing anything.

3. For each new note, OLDEST FIRST by the note's OWN send time (the "Date:" inside the
   forwarded body, not the time the forward arrived), read the full plain-text body and structure it into
   the JSON shape documented in PARSE_SYSTEM inside 04_live_system/desk_notes.py. Follow
   those rules exactly:
     - "stance" is one of favour / avoid / dispersion / watch
     - "favours"/"against" hold TICKERS only, and only ones the note actually implies.
       Omit the key rather than invent a name. Where a ticker list is your inference
       rather than the note's own words, say so in the theme's "basis" field.
     - "key" is a stable snake_case slug so a theme merges with the same theme from an
       earlier note instead of appending a duplicate.
     - Quote levels verbatim ("4.80%", "\$95"). Never round or update a number.
     - Only include a catalyst the note actually dates.

4. Write each note's JSON to a temp file and merge it:
     "$PY" desk_notes.py --merge-json <file> --subject "<subject>" --date "<YYYY-MM-DD HH:MM>"
   Use the note's own send time as --date, not today's.

5. Then rebuild the weekly book:
     "$PY" weekly_swing.py

6. Print a two-line summary: which notes were ingested, and how many cards resulted.

Do not edit any other file. Do not commit. Do not place any trade.
PROMPT_END

"$CLAUDE" -p "$PROMPT" \
  --allowedTools "Bash,Read,Write,mcp__claude_ai_Gmail__search_threads,mcp__claude_ai_Gmail__get_thread" \
  >>"$LOG" 2>&1
STATUS=$?

echo "claude exit: $STATUS" >>"$LOG"

# Rebuild regardless: if the ingest added nothing the overlay is unchanged and this just
# refreshes the live strikes on the existing cards, which is worth doing on its own.
"$PY" weekly_swing.py >>"$LOG" 2>&1
"$PY" desk_notes.py --show >>"$LOG" 2>&1
tail -1 "$LOG"
exit 0
