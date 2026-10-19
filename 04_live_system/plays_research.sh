#!/bin/zsh
# The research desk: every morning, read what is out there on every name the measured books
# hold, and write it down with sources, so the Plays desk can show WHY beside each play.
#
# WHY A HEADLESS CLAUDE SESSION. The Anthropic API account is out of credit and the Claude
# Code login is not; the desk-note ingest already runs this way. The session reads the
# candidate list the engine wrote, searches and fetches primary sources for each name
# (news, the last filing's tone, analyst changes, the catalyst calendar, the options
# market's read), and writes ONE JSON file. It never picks a play and never changes a
# number the engine computed: research is the reasoning stack, not the signal.
set -u
cd "$(dirname "$0")" || exit 1
REPO="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$REPO/local.env" ] && . "$REPO/local.env"
export IDT_STATE_ROOT="${IDT_STATE_ROOT:-$REPO/04_live_system/data}"
export IDT_DATA_ROOT="${IDT_DATA_ROOT:-$REPO/data}"
export PYTHONPATH="$REPO:$REPO/04_live_system"
export PATH="/opt/homebrew/bin:$PATH"
if [ -n "${IDT_PYTHON:-}" ]; then PY="$IDT_PYTHON"
elif [ -x "$REPO/venv/bin/python3" ]; then PY="$REPO/venv/bin/python3"
else PY="$(command -v python3)"; fi
CLAUDE="${CLAUDE_BIN:-/opt/homebrew/bin/claude}"
LOG="$REPO/logs/plays_research.out"
OUT="$IDT_STATE_ROOT/plays_research.json"
mkdir -p "$REPO/logs"
echo "--- plays research $(date '+%Y-%m-%d %H:%M:%S %Z') ---" >>"$LOG"

# the names: every open play plus the top candidates the engine is considering
NAMES="$("$PY" - <<'PY'
import json, os
from idt import snapshots
p, _ = snapshots.read("plays_snapshot.json")
names = []
for x in (p or {}).get("open") or []:
    if x.get("status") == "open": names.append(x["ticker"])
for x in ((p or {}).get("considered") or [])[:12]:
    names.append(x["ticker"])
seen = []
for n in names:
    if n not in seen: seen.append(n)
print(" ".join(seen[:15]))
PY
)"
if [ -z "$NAMES" ]; then
  echo "no candidates in plays_snapshot.json; nothing to research" >>"$LOG"
  exit 0
fi
echo "names: $NAMES" >>"$LOG"

read -r -d '' PROMPT <<PROMPT_END
Research these stocks for a swing-options desk and write ONE JSON file. Names: $NAMES

For EACH name, find and cite (WebSearch first, WebFetch the primary page; if search is unavailable, fetch the company's investor-relations news page, the SEC EDGAR filing index https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<TICKER>&type=8-K and a finance news page):
  1. the last earnings print: date, beat/miss vs consensus, guidance change, the stock's reaction, one-line why (from the release or call coverage);
  2. news in the last 14 days that could move it (deals, guidance, regulation, product, litigation, management, index changes), each with a date and a URL;
  3. the next dated catalysts in the next 90 days (next earnings date, investor day, FDA/regulatory dates, product launches, lock-ups), with dates and URLs;
  4. analyst actions in the last 30 days (upgrades/downgrades/target changes) with the source;
  5. anything that argues AGAINST owning it for the next 1-3 months, stated plainly;
  6. a one-sentence "what moves this stock" (its main driver: rates, oil, AI capex, consumer, FX...).
Be specific and sourced. Where you cannot verify, write "not verified". Do not invent dates or numbers. Do not give trading advice; the engine decides.

Write the result with the Write tool to: $OUT
Shape (strict JSON):
{"as_of": "<YYYY-MM-DD HH:MM ET>", "names": {"<TICKER>": {
   "last_print": {"date": "...", "result": "beat|miss|inline", "reaction_pct": <number or null>, "summary": "...", "url": "..."},
   "news": [{"date": "...", "headline": "...", "why_it_matters": "...", "url": "..."}],
   "catalysts": [{"date": "...", "label": "...", "url": "..."}],
   "analysts": [{"date": "...", "firm": "...", "action": "...", "url": "..."}],
   "against": ["..."],
   "driver": "...",
   "sources_checked": <int>}}}
Then print one line per name: ticker, number of news items, next catalyst date. Do not edit any other file. Do not commit.
PROMPT_END

"$CLAUDE" -p "$PROMPT" --allowedTools "WebSearch,WebFetch,Write,Read,Bash" >>"$LOG" 2>&1
STATUS=$?
echo "claude exit: $STATUS" >>"$LOG"
if [ "$STATUS" -ne 0 ] && tail -c 4000 "$LOG" | grep -q "Failed to authenticate"; then
  osascript -e 'display notification "Claude login expired: the plays research is not running. Run /login in Claude Code." with title "Plays research failed" sound name "Basso"' 2>/dev/null || true
fi
# rebuild the plays snapshot so the research shows on the cards within the hour
"$PY" -c "import plays; plays.issue()" >>"$LOG" 2>&1
tail -1 "$LOG"
exit 0
