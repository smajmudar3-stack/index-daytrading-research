#!/usr/bin/env node
// TARS hook: verify-gate (Stop)
//
// "Verifiers replace approval gates" (SPEC principle 3). The runner already
// enforces that for orchestrated nodes: a node cannot reach `done` without the
// repo's verify manifest passing. An interactive session had no equivalent — it
// could say "done" with a red suite and nothing would disagree.
//
// This is that gate, and it was in the SPEC hook pack unbuilt from the start.
//
// WHAT IT DOES NOT DO, deliberately:
//
//   - It does not run the whole manifest. A session that touched only docs must
//     not pay for a browser suite, and zelta-app's e2e is 4.6 minutes. Entries
//     declaring `when` are skipped exactly as they are for a node, using the
//     same code, so this gate costs what the change costs.
//   - It does not run when nothing changed. A session that read code and
//     answered a question has nothing to verify.
//   - It does not block on a missing toolchain. "This tree cannot run its own
//     verify" and "your change broke the suite" are different sentences and only
//     the second one is the agent's problem.

'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

function findRepoRoot(startDir) {
  let dir = startDir;
  for (let i = 0; i < 40; i++) {
    if (fs.existsSync(path.join(dir, '.git'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

function git(args, cwd) {
  try {
    return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  } catch { return null; }
}

function kitDir(repoRoot) {
  for (const d of ['.tars']) {
    if (fs.existsSync(path.join(repoRoot, d, 'profile.json'))) return d;
  }
  return null;
}

// Vendored hooks must stand alone — a repo gets the hook pack without the
// orchestrator — so the manifest shapes are read here rather than imported.
// The two forms must agree with kit/orchestrator/verify.js; a test asserts it.
function manifestEntries(profile) {
  return Object.entries(profile?.verify || {}).map(([name, spec]) => (
    typeof spec === 'string'
      ? { name, cmd: spec, when: null }
      : { name, cmd: String(spec?.cmd || ''), when: Array.isArray(spec?.when) ? spec.when : null }
  ));
}

function globToRegExp(glob) {
  let re = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*') {
      if (glob[i + 1] === '*') { i++; if (glob[i + 1] === '/') i++; re += '.*'; }
      else re += '[^/]*';
    } else if (c === '?') re += '[^/]';
    else re += c.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(`^${re}$`);
}

function applies(when, changed) {
  if (!when || !when.length) return true;
  if (!changed.length) return true;
  const pats = when.map(globToRegExp);
  return changed.some((f) => pats.some((re) => re.test(f)));
}

function main() {
  try { JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch (e) {
    process.stderr.write(`[tars:verify-gate] unparseable hook input (${e.message}) — gate skipped\n`);
    return;
  }

  const root = findRepoRoot(process.cwd());
  if (!root) return;
  const dir = kitDir(root);
  if (!dir) return; // not an adopted repo

  let profile;
  try { profile = JSON.parse(fs.readFileSync(path.join(root, dir, 'profile.json'), 'utf8')); } catch { return; }
  const entries = manifestEntries(profile).filter((e) => e.cmd);
  if (!entries.length) return;

  // Uncommitted work AND anything committed but unpushed: a session that
  // committed a broken change and stopped is exactly the case worth catching.
  const dirty = (git(['status', '--porcelain'], root) || '')
    .split('\n').map((l) => l.slice(3).trim()).filter(Boolean);
  const upstream = git(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], root);
  const ahead = upstream
    ? (git(['diff', '--name-only', `${upstream}...HEAD`], root) || '').split('\n').filter(Boolean)
    : [];
  const changed = [...new Set([...dirty, ...ahead])];
  if (!changed.length) return; // nothing was changed; nothing to verify

  const failures = [];
  for (const e of entries) {
    if (!applies(e.when, changed)) continue;
    try {
      execFileSync(e.cmd, { cwd: root, shell: true, stdio: ['ignore', 'pipe', 'pipe'], encoding: 'utf8' });
    } catch (err) {
      const out = `${err.stdout || ''}${err.stderr || ''}`.replace(/\[[0-9;]*m/g, '').trim();
      // A command that is not installed is not a broken change. Say which kind
      // of failure this is, or the reader debugs the wrong thing.
      const missing = err.status === 127 || err.status === 9009
        || /command not found|not recognized as an internal|no such file or directory/i.test(out);
      failures.push({ name: e.name, cmd: e.cmd, missing, tail: out.split('\n').slice(-25).join('\n') });
    }
  }

  const real = failures.filter((f) => !f.missing);
  const absent = failures.filter((f) => f.missing);
  if (absent.length) {
    process.stderr.write(`[tars:verify-gate] not run (command absent): ${absent.map((f) => f.name).join(', ')}\n`);
  }
  if (!real.length) return;

  process.stderr.write(
    `This session changed ${changed.length} file(s) and the repo's verify manifest fails on them.\n\n` +
    real.map((f) => `### ${f.name} — \`${f.cmd}\`\n\n\`\`\`\n${f.tail}\n\`\`\``).join('\n\n') +
    '\n\nFix the cause rather than disabling the check. If the failure is genuinely ' +
    'pre-existing and unrelated to this session, say so explicitly with the output ' +
    'above rather than staying silent about it.\n',
  );
  process.exit(2);
}

main();
process.exit(process.exitCode || 0);
