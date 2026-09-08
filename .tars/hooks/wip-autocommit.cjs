#!/usr/bin/env node
// TARS hook: wip-autocommit (Stop hook, Claude Code + Codex compatible)
//
// Snapshots a dirty working tree — tracked AND untracked (gitignore respected) —
// into refs/wip/<session> WITHOUT touching the user's branch, index, or worktree,
// then pushes the ref to origin so any other machine can recover the session state:
//
//   git fetch origin 'refs/wip/*:refs/wip/*'
//   git checkout -b recover-<x> refs/wip/<session>   (or cherry-pick / diff)
//
// Never blocks the session (always exits 0). Push failures are logged, not fatal.
// Opt out of pushing with TARS_WIP_NO_PUSH=1.

'use strict';

const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

function readStdinJson() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function main() {
  const input = readStdinJson();
  const cwd = input.cwd || process.cwd();

  const git = (args, extraEnv) =>
    execFileSync('git', args, {
      cwd,
      encoding: 'utf8',
      env: extraEnv ? { ...process.env, ...extraEnv } : process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
    }).trim();

  let toplevel;
  try {
    toplevel = git(['rev-parse', '--show-toplevel']);
  } catch {
    return; // not a git repo — nothing to protect
  }

  const dirty = git(['status', '--porcelain']);
  if (!dirty) return; // clean tree — nothing to snapshot

  const sessionId = String(input.session_id || `t${Date.now()}`)
    .replace(/[^a-zA-Z0-9._-]/g, '-')
    .slice(0, 64);
  const refName = `refs/wip/${sessionId}`;

  // Build the snapshot in a throwaway index so the real index is untouched.
  const tmpIndex = path.join(os.tmpdir(), `tars-wip-index-${process.pid}`);
  const env = { GIT_INDEX_FILE: tmpIndex };
  let commitSha;
  try {
    let headSha = null;
    try {
      headSha = git(['rev-parse', '--verify', 'HEAD']);
    } catch {
      // unborn branch (fresh repo) — snapshot has no parent
    }

    if (headSha) git(['-C', toplevel, 'read-tree', 'HEAD'], env);
    git(['-C', toplevel, 'add', '-A'], env);
    const treeSha = git(['-C', toplevel, 'write-tree'], env);

    let branch = 'detached';
    try {
      branch = git(['rev-parse', '--abbrev-ref', 'HEAD']);
    } catch {}

    const msg = `wip: session ${sessionId} on ${branch} (${os.hostname()})`;
    const commitArgs = ['commit-tree', treeSha, '-m', msg];
    if (headSha) commitArgs.push('-p', headSha);
    commitSha = git(commitArgs);

    git(['update-ref', refName, commitSha]);
  } finally {
    try { fs.unlinkSync(tmpIndex); } catch {}
  }

  let pushed = false;
  if (!process.env.TARS_WIP_NO_PUSH) {
    try {
      git(['remote', 'get-url', 'origin']);
      git(['push', '--no-verify', 'origin', `${refName}:${refName}`]);
      pushed = true;
    } catch {
      // no remote / offline / auth — local ref still protects the work
    }
  }

  try {
    fs.appendFileSync(
      path.join(toplevel, '.git', 'tars-wip.log'),
      `${new Date().toISOString()} ${refName} ${commitSha} pushed=${pushed}\n`
    );
  } catch {}
}

try {
  main();
} catch (err) {
  // Never block a session over a snapshot failure — but leave a trace.
  try { process.stderr.write(`[tars:wip-autocommit] ${err.message}\n`); } catch {}
}
process.exit(0);
