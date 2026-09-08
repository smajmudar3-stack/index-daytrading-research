#!/bin/bash
# install.sh — set this repo up on a machine that has never seen it.
#
# WHY AN INSTALLER AND NOT A README STEP LIST. The scheduled jobs are launchd plists, and a
# plist cannot contain a variable: every path in it is absolute. Shipping them with one
# person's home directory baked in is what makes a working system uninstallable by anyone
# else. So the plists are GENERATED here from wherever the repo actually sits.
#
# Everything is idempotent. Run it again after a pull and it will re-generate the jobs and
# leave your .env and local.env alone.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()  { printf '  \033[32mok\033[0m   %s\n' "$*"; }
warn(){ printf '  \033[33mwarn\033[0m %s\n' "$*"; }
die() { printf '  \033[31mfail\033[0m %s\n' "$*"; exit 1; }

say "1. Python"
# SEARCH, do not assume `python3`. macOS still ships 3.9 as `python3`, which cannot run this
# repo, and a machine that has a newer Python installed alongside it usually exposes that one
# only under a versioned name. Failing with "python 3.9 is too old" when 3.12 is sitting right
# there is a bad first impression and an avoidable support message.
suitable() {
  [ -x "$(command -v "$1" 2>/dev/null)" ] || return 1
  "$1" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)' 2>/dev/null
}
PYBIN=""
for cand in ${PYTHON:-} python3.13 python3.12 python3.11 python3 \
            /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  [ -n "$cand" ] || continue
  if suitable "$cand"; then PYBIN="$cand"; break; fi
done
if [ -z "$PYBIN" ]; then
  have="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo none)"
  die "need Python 3.11 or newer; the best found was $have.
       macOS ships 3.9 and it is not enough (this repo uses zoneinfo and modern typing).
       Install one:  brew install python@3.12
       Then re-run:  ./install.sh"
fi
PYVER="$("$PYBIN" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
ok "python $PYVER at $(command -v "$PYBIN")"

say "2. Virtual environment and dependencies"
if [ ! -x "$REPO/venv/bin/python3" ]; then
  "$PYBIN" -m venv "$REPO/venv" || die "could not create venv"
  ok "created venv/"
else
  ok "venv/ already exists"
fi
"$REPO/venv/bin/pip" install --quiet --upgrade pip
"$REPO/venv/bin/pip" install --quiet -r "$REPO/requirements.txt" || die "dependency install failed"
ok "installed $(grep -cve '^\s*#' -e '^\s*$' "$REPO/requirements.txt") runtime packages"
# The test tooling too: a recipient who cannot run the suite cannot confirm the install, and
# "it seems to start" is a much weaker claim than "141 tests pass".
"$REPO/venv/bin/pip" install --quiet -r "$REPO/requirements-dev.txt" || warn "dev tools failed to install; the suite will not run"
ok "installed the test tooling (pytest, ruff)"

say "3. Configuration"
if [ ! -f "$REPO/.env" ]; then
  cp "$REPO/.env.example" "$REPO/.env"
  warn "created .env from the example — YOU MUST ADD YOUR KEYS before the weekly book will produce anything"
else
  ok ".env already present (left untouched)"
fi
if [ ! -f "$REPO/local.env" ]; then
  cat > "$REPO/local.env" <<'LOCALEOF'
# Machine-specific paths. Git-ignored: every install has its own.
# IDT_DATA_ROOT is the 16 GB of market data that is not in the repo. Leave it unset if you do
# not have that data — everything except the historical backtests still runs.
# export IDT_DATA_ROOT="/path/to/market/data"
LOCALEOF
  ok "created local.env (paths default to this repo)"
else
  ok "local.env already present (left untouched)"
fi
mkdir -p "$REPO/logs" "$REPO/04_live_system/data"
ok "logs/ and 04_live_system/data/ ready"

say "4. Repository metadata"
# `scripts/verify.py` enumerates files with `git ls-files`, so it needs a repository even
# though it never talks to a remote. A recipient who receives a ZIP rather than a clone has no
# .git, and verify then reports "0 .py files in the working tree" plus several hundred phantom
# manifest failures — alarming, and entirely an artefact of the delivery method.
if [ ! -d "$REPO/.git" ]; then
  if command -v git >/dev/null 2>&1; then
    git -C "$REPO" init --quiet
    git -C "$REPO" add -A
    git -C "$REPO" -c user.email=install@local -c user.name=install \
        commit --quiet -m "Initial import from archive" || true
    ok "initialised a local git repo (verify.py enumerates files through git)"
  else
    warn "no git and no .git — verify.py will under-report. Install git and re-run."
  fi
else
  ok "git repository present"
fi

say "5. Verification"
PYTHONPATH="$REPO" "$REPO/venv/bin/python3" "$REPO/scripts/verify.py" || die "verify.py failed — do not proceed"
if PYTHONPATH="$REPO" "$REPO/venv/bin/python3" -m pytest "$REPO/test" -q 2>&1 | tail -3; then
  ok "test suite ran"
else
  warn "the test suite did not complete — see the output above"
fi

say "6. Scheduled jobs"
# GENERATED, not shipped. This is the whole reason install.sh exists.
if [ -n "${SKIP_LAUNCHD:-}" ]; then
  # For CI and for verifying an install without disturbing jobs already running on the machine.
  warn "SKIP_LAUNCHD set — not installing or touching any scheduled job"
elif [ "$(uname)" != "Darwin" ]; then
  warn "not macOS — skipping launchd. Run 04_live_system/refresh_cycle.sh from cron every 5 minutes instead."
else
  AGENTS="$HOME/Library/LaunchAgents"
  mkdir -p "$AGENTS"
  gen_plist() {  # label, script, extra-xml
    cat > "$AGENTS/$1.plist" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$1</string>
  <key>ProgramArguments</key>
  <array><string>/bin/zsh</string><string>$REPO/04_live_system/$2</string></array>
  <key>WorkingDirectory</key><string>$REPO/04_live_system</string>
$3
  <key>StandardOutPath</key><string>$REPO/logs/$1.out</string>
  <key>StandardErrorPath</key><string>$REPO/logs/$1.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key><string>$HOME</string>
  </dict>
</dict>
</plist>
PLISTEOF
    launchctl unload "$AGENTS/$1.plist" 2>/dev/null || true
    launchctl load  "$AGENTS/$1.plist" && ok "loaded $1"
  }

  # Every 5 minutes: maintenance, then the panel scans.
  gen_plist "com.daytrading.refresh" "refresh_cycle.sh" \
    "  <key>StartInterval</key><integer>300</integer>"

  # Monthly: re-read the BLS and Fed release schedules. Needs the claude CLI.
  gen_plist "com.daytrading.calendar" "refresh_calendar.sh" \
    "  <key>StartCalendarInterval</key>
  <array><dict><key>Day</key><integer>2</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>10</integer></dict></array>"

  # The dashboard itself is a plain server, not a script.
  cat > "$AGENTS/com.daytrading.dashboard.plist" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.daytrading.dashboard</string>
  <key>ProgramArguments</key>
  <array><string>$REPO/venv/bin/python3</string><string>$REPO/04_live_system/dashboard_app.py</string></array>
  <key>WorkingDirectory</key><string>$REPO/04_live_system</string>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$REPO/logs/dashboard.out</string>
  <key>StandardErrorPath</key><string>$REPO/logs/dashboard.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONPATH</key><string>$REPO</string>
    <key>IDT_STATE_ROOT</key><string>$REPO/04_live_system/data</string>
    <key>HOME</key><string>$HOME</string>
  </dict>
</dict>
</plist>
PLISTEOF
  launchctl unload "$AGENTS/com.daytrading.dashboard.plist" 2>/dev/null || true
  launchctl load  "$AGENTS/com.daytrading.dashboard.plist" && ok "loaded com.daytrading.dashboard"
fi

say "Done"
cat <<'DONEEOF'
  Next, in order:

    1. Put your Unusual Whales key in .env   (UNUSUALWHALES_API_KEY=...)
       Without it the weekly book produces NOTHING. Four of its seven inputs come from
       that one vendor, and the engine refuses a card with fewer than three inputs.
       Measured with the key disabled: 0 cards, 32 names refused.

    2. Open http://127.0.0.1:8095/markets

    3. The first weekly scan takes 2-4 minutes (it downloads a year of history for ~1,550
       names in batches). Until it finishes the cards panel will say so rather than lie.

  The weekly book also needs a macro read, which comes from emailed desk notes. Without
  those it stays empty by design — that is the engine refusing to trade on technicals
  alone, not a failure. See CLAUDE.md.
DONEEOF
