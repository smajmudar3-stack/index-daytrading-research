#!/usr/bin/env node
// TARS hook: tidy-gate (PostToolUse: Write)
// Enforces the "everything has a spot" doctrine from .tars/structure.json.
// When a NEW file lands somewhere with no defined home, nags the agent (exit 2 →
// stderr is fed back to the agent as feedback; the write itself already happened).
// The agent must either move the file to its spot or formally create a new spot
// (update structure.json + document it in AGENTS.md) in the same change.

'use strict';

const fs = require('fs');
const path = require('path');

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

function main() {
  let input = {};
  try { input = JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch (e) {
    // Fail loudly, not open: a gate that silently passes on bad input is no gate.
    process.stderr.write(`[tars:tidy-gate] unparseable hook input (${e.message}) — gate skipped\n`);
    return;
  }
  const filePath = input.tool_input?.file_path;
  if (!filePath) return;

  const repoRoot = findRepoRoot(path.dirname(path.resolve(filePath)));
  if (!repoRoot) return;

  // kit but has not re-run `tars adopt` still has its doctrine there, and a
  // gate that silently stops enforcing is worse than no rename at all.
  const structurePath = [path.join(repoRoot, '.tars', 'structure.json')].find((p) => fs.existsSync(p));
  if (!structurePath) return; // repo not adopted — no doctrine to enforce

  let structure;
  try { structure = JSON.parse(fs.readFileSync(structurePath, 'utf8')); } catch { return; }

  const rel = path.relative(repoRoot, path.resolve(filePath)).replace(/\\/g, '/');
  if (rel.startsWith('..')) return;

  const base = path.basename(rel);
  const topDir = rel.includes('/') ? rel.split('/')[0] : null;

  // Root files: must be on the allowlist.
  if (!topDir) {
    const allow = structure.rootAllow || [];
    const ok = allow.some((entry) => {
      if (!entry.includes('*')) return base === entry;
      const [pre, suf] = entry.split('*');
      return base.startsWith(pre) && base.endsWith(suf) && base.length >= pre.length + suf.length;
    });
    if (!ok) {
      process.stderr.write(
        `TIDY GATE: "${base}" landed at repo root, which is allowlist-only (see ${path.basename(path.dirname(structurePath))}/structure.json). ` +
        'Move it to its proper home, or if it genuinely needs a new spot, create one: add it to structure.json ' +
        'and document it in AGENTS.md in this same change. Root junk never persists.\n'
      );
      process.exit(2);
    }
    return;
  }

  // Directory files: top-level dir must be a known home.
  const known = new Set([
    ...(structure.knownDirs || []),
    ...Object.values(structure.homes || {}).map((h) => String(h).split('/')[0]),
  ]);
  if (!known.has(topDir)) {
    process.stderr.write(
      `TIDY GATE: "${rel}" is in "${topDir}/", which is not a defined spot in ${path.basename(path.dirname(structurePath))}/structure.json. ` +
      'Either this file belongs in an existing home, or the new directory is legitimate — in which case add it ' +
      'to structure.json knownDirs and document its purpose in AGENTS.md in this same change.\n'
    );
    process.exit(2);
  }
}

try { main(); } catch (err) {
  process.stderr.write(`[tars:tidy-gate] ${err.message}\n`);
}
process.exit(process.exitCode || 0);
