#!/usr/bin/env node
// TARS hook: sweep-report
// SessionStart: show what the scheduled sweep found and you have not seen yet.
//
// The sweep was built to speak only when something needs a decision. It does —
// into a log file that nothing reads. A report with no reader is the same defect
// as a silenced error: the system knows, and you do not. This closes that, and
// nothing else: it renders, it does not decide.
//
// Contract:
//   - prints ONLY report blocks appended since the last session that saw them
//   - prints nothing at all when the sweep was clean, so it stays worth reading
//   - never fails a session. A broken reporter must not cost you a session.
//
// State: a marker file holding the byte offset already shown. Offset, not
// timestamp, because the log is append-only and an offset cannot disagree with
// what is actually in the file.

'use strict';

const fs = require('fs');
const path = require('path');

// Standalone, like secrets-guard, and for the same reason: `tars adopt` vendors
// this file to `.tars/hooks/` and does NOT vendor `kit/orchestrator/`. A
// `require('../orchestrator/paths.js')` here resolved to `.tars/orchestrator/`,
// which never exists in an adopted repo, so the hook died with MODULE_NOT_FOUND
// on every SessionStart in every repo the kit has ever stamped. Nothing said so:
// the hook was wired, the file was on disk, and the report simply never appeared.
//
// The two helpers it needed are four lines. Keeping them here costs a duplicated
// constant; requiring across the vendoring boundary cost the whole feature.
const DIR = '.tars';
const ENV_PREFIX = 'TARS_';
const envVar = (name, fallback) => {
  const v = process.env[ENV_PREFIX + name];
  return v === undefined ? fallback : v;
};
const paths = {
  env: envVar,
  resolve: (repoRoot, ...segments) => path.join(repoRoot, DIR, ...segments),
};

const REPO = paths.env('REPO', process.env.CLAUDE_PROJECT_DIR || process.cwd());

function logPath() {
  // Follow the state-dir rename, but keep reading whichever one holds the log:
  // resolving to an empty new dir while the history sits in the old one would
  // silently report "nothing new" forever.
  const candidates = [
    paths.resolve(REPO, 'overnight', 'sweep.log'),
    path.join(REPO, '.tars', 'overnight', 'sweep.log'),
  ];
  return candidates.find((p) => fs.existsSync(p)) || null;
}

// Reports start with a `# tars sweep — <stamp> on <host>` banner. A clean run
// writes a bare `<stamp>  clean` line instead, which carries no decision and is
// deliberately not shown.
function blocksSince(text) {
  const out = [];
  let current = null;
  for (const line of text.split('\n')) {
    if (/^# tars sweep /.test(line)) {
      if (current) out.push(current);
      current = [line];
    } else if (current) {
      current.push(line);
    }
  }
  if (current) out.push(current);
  return out.map((b) => b.join('\n').trim()).filter(Boolean);
}

// Every line the sweep writes carries an ISO stamp — the report banner and the
// one-line `<stamp>  clean` entry alike. The newest one is when it last ran.
function lastRunAt(text) {
  const stamps = text.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/g);
  if (!stamps || !stamps.length) return null;
  const t = Date.parse(stamps[stamps.length - 1]);
  return Number.isNaN(t) ? null : t;
}

// A daily job gets one missed day of grace before this counts as broken.
const STALE_MS = 48 * 60 * 60 * 1000;

// Another agent session live in THIS working tree.
//
// The repo convention is that parallel sessions each take a worktree and branch
// and never fight over the main tree. It was written down and enforced by
// nothing, and on 2026-08-19 it cost real work: two sessions committed the same
// tree minutes apart, and a routing change landed inside a commit about a
// containment test, twice. Nobody was warned, because nobody was looking.
//
// Ancestors are excluded or this fires on every launch: the hook is spawned BY
// the session it would be reporting. Linux-only via /proc, quiet everywhere
// else — outpost is the run machine, and a check that cannot run is not a
// failure it should announce.
// Substring matching on the whole command line called the codex app-server and
// its vendored helper "sessions", because both have `codex` somewhere in their
// path. A warning that fires on two daemons every launch is a warning that gets
// ignored, which is the same end state as not having one. Match the executable
// NAME, then drop the subcommands that mean "daemon", not "session".
const AGENT_BINARIES = new Set(['claude', 'codex', 'grok']);
const WRAPPERS = new Set(['node', 'bun', 'deno', 'npx']);
const NOT_A_SESSION = new Set(['app-server', 'serve', 'mcp', 'login', 'logout', '--version', '--help']);

function isAgentSession(args) {
  let i = 0;
  while (i < args.length && WRAPPERS.has(path.basename(args[i]).replace(/\.(exe|js|mjs|cjs)$/, ''))) i++;
  if (i >= args.length) return false;
  const name = path.basename(args[i]).replace(/\.exe$/, '');
  if (!AGENT_BINARIES.has(name)) return false;
  return !NOT_A_SESSION.has(args[i + 1]);
}

function cotenants(repoRoot) {
  let pids;
  try { pids = fs.readdirSync('/proc').filter((f) => /^\d+$/.test(f)); } catch { return []; }

  const mine = new Set();
  let walk = String(process.pid);
  for (let i = 0; i < 40 && walk && walk !== '0'; i++) {
    mine.add(walk);
    try {
      const stat = fs.readFileSync(`/proc/${walk}/stat`, 'utf8');
      walk = stat.slice(stat.lastIndexOf(')') + 2).split(' ')[1];
    } catch { break; }
  }

  const found = [];
  for (const pid of pids) {
    if (mine.has(pid)) continue;
    let cwd;
    try { cwd = fs.realpathSync(`/proc/${pid}/cwd`); } catch { continue; }
    if (cwd !== repoRoot) continue;
    let args;
    try { args = fs.readFileSync(`/proc/${pid}/cmdline`).toString().split('\0').filter(Boolean); } catch { continue; }
    if (!isAgentSession(args)) continue;
    found.push({ pid, cmd: args.join(' ').slice(0, 60) });
  }
  return found;
}

function main() {
  // Before the sweep-log early return: a repo that has never been swept still
  // has sessions in it, and this is the warning that has to arrive first.
  let here = REPO;
  try { here = fs.realpathSync(REPO); } catch { /* use it unresolved */ }
  const others = cotenants(here);
  if (others.length) {
    process.stdout.write(
      `[tars:sweep-report] ${others.length} other agent session(s) are live in this working tree `
      + `(pid ${others.map((o) => o.pid).join(', ')}). Committing here will sweep up their staged files, `
      + 'and theirs will sweep up yours. Take a worktree before starting long work: '
      + '`git worktree add .worktrees/<topic> -b session/<topic>`.\n\n'
    );
  }

  const file = logPath();
  if (!file) return; // no sweep has ever run here; nothing to say

  // Checked BEFORE the seen-marker, and deliberately not silenced once shown.
  // If cron dies or the script breaks, the log simply stops growing — and
  // "nothing new" is indistinguishable from "nothing wrong". That is the exact
  // failure this whole reporting path exists to prevent, so it nags.
  try {
    const tail = fs.readFileSync(file, 'utf8').slice(-4000);
    const last = lastRunAt(tail);
    if (last !== null) {
      const age = Date.now() - last;
      if (age > STALE_MS) {
        const days = Math.floor(age / (24 * 60 * 60 * 1000));
        process.stdout.write(
          `[tars:sweep-report] the daily sweep has not run in ${days} day(s) — last entry ${new Date(last).toISOString()}. `
          + 'Check `crontab -l` and the cron log; nothing has been checking the repos or the Windows suite since then.\n\n');
      }
    }
  } catch { /* fall through to the report below rather than losing it too */ }

  const marker = path.join(path.dirname(file), '.sweep-report-seen');
  const size = fs.statSync(file).size;
  let seen = 0;
  try {
    seen = Number(fs.readFileSync(marker, 'utf8').trim()) || 0;
  } catch { seen = 0; }

  // Truncated or rotated: re-read from the start rather than skipping content.
  if (seen > size) seen = 0;
  if (seen === size) return;

  const fd = fs.openSync(file, 'r');
  const buf = Buffer.alloc(size - seen);
  fs.readSync(fd, buf, 0, buf.length, seen);
  fs.closeSync(fd);

  // Advance the marker even when the new content is all "clean" lines, so a
  // quiet week does not re-scan the same tail every session.
  fs.writeFileSync(marker, String(size));

  const blocks = blocksSince(buf.toString('utf8'));
  if (!blocks.length) return;

  // Only the most recent matters. Older unread reports describe a state the
  // newest one has already re-measured, and printing a backlog is how a report
  // becomes noise.
  const latest = blocks[blocks.length - 1];
  const extra = blocks.length > 1 ? `\n\n(${blocks.length - 1} older report(s) skipped — this is the current state.)` : '';
  process.stdout.write(`${latest}${extra}\n`);
}

// Exported for the suite. Without the guard, requiring this file to test one
// pure function would run the whole report as a side effect.
if (require.main !== module) module.exports = { cotenants, isAgentSession };

try {
  if (require.main === module) main();
} catch (err) {
  // Report the reporter's own failure rather than exiting non-zero: a hook that
  // blocks a session because it could not read a log is worse than the gap it
  // was added to close.
  process.stdout.write(`[tars:sweep-report] could not read the sweep log: ${err.message}\n`);
}
