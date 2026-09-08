#!/usr/bin/env node
// TARS hook: route-gate (UserPromptSubmit + PreToolUse:Task + PostToolUse:Task)
//
// "Model routing is policy, not preference" (SPEC principle 4). The runner has
// enforced that since F1: router.js assigns every node from routing-policy.json
// by deterministic code, and the model cannot talk its way out of it.
//
// An interactive session had no equivalent. Routing reached it as PROSE — a
// skill file asking a model to consult a policy — and prose is not a gate. The
// evidence was in the log the policy itself mandates: 73 dispatches, of which
// the last build/review/mechanical row came from a `tars run`, and every later
// row came from the research cron. Zero session dispatches. The policy said
// `build` alternates across two vendors while every session sent every task to
// one, and nothing anywhere disagreed.
//
// This is that gate. Three modes, one file, because they share the vendor map
// and disagreeing copies of it is the failure they exist to prevent:
//
//   prompt : classify the turn, ask the router, state the decision in context.
//   pre    : a spawn that contradicts the decision is refused, not noted.
//   post   : the dispatch line is written by the machine, not remembered.
//
// WHAT IT DOES NOT DO, deliberately:
//
//   - It does not route the main loop. The session you type into is Claude and
//     a hook cannot change that. Routing redirects DELEGATED work only, so the
//     ceiling on what it can save is however much work gets delegated. The
//     prompt mode therefore states the break-even rule too: unrouted work is
//     usually work that was never handed off in the first place.
//   - It does not classify by asking a model. A gate that costs a vendor call
//     per prompt gets switched off within a week. Heuristics here are
//     deliberately shallow and default to SILENT, not to `build`: a
//     misclassified chat turn that injects a routing directive trains you to
//     ignore the directive, which is worse than missing one dispatch.
//   - It does not block build-class spawns. Only the cases the policy calls
//     mandatory are refused, because a gate that fires on judgement calls is a
//     gate you learn to work around.
//   - It does not read the dispatch log to decide anything. The log is written
//     by the session the gate is judging, so a gate that trusted it would let a
//     session write itself a permission slip. See "operator directive" below:
//     the only override comes from the operator's own prompt text.

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

// npm installs a console script on Windows as `tars.cmd`, and Node cannot
// execFile a .cmd directly — CreateProcess only runs real executables, so it
// fails with ENOENT/EINVAL. `shell: true` routes it through cmd.exe, which is
// what makes the shim resolvable. Without this the gate could not run at all on
// Windows and emitted nothing, which reads as "the gate said nothing" rather
// than "the gate could not run".
const SHELL_FOR_SHIMS = process.platform === 'win32';

// ...but shell:true then stops Node quoting the arguments, because it hands the
// whole line to cmd.exe. `--deviation "session spawned X where policy routed
// grok"` split at the first space and the log recorded the single word
// "session". Two traps in one call: the shim will not resolve without a shell,
// and the arguments will not survive one. So quote them here, and only here.
function winQuote(arg) {
  const a = String(arg);
  // cmd.exe has no escape for a quote inside a quoted string that also works for
  // backslashes; doubling is what its own parser accepts.
  return `"${a.replace(/"/g, '""')}"`;
}

function tarsExec(args, opts = {}) {
  if (!SHELL_FOR_SHIMS) return execFileSync('tars', args, opts);
  return execFileSync('tars', args.map(winQuote), { ...opts, shell: true, windowsVerbatimArguments: true });
}

const STATE_DIR = '.tars';
const STATE_FILE = 'route-state.json';
// Per-session routing decisions live here; see stateFile().
const SESSION_DIR = 'route-state';

// --------------------------------------------------------------- vendor map ---
//
// Subagent type -> vendor. This is the join between the routing policy, which
// names PROVIDERS, and the Task tool, which names SUBAGENT TYPES. Both vendor
// plugins ship an agent that shells out to their own CLI, so in-session
// cross-vendor delegation needs no new machinery — only something that picks it.
const AGENT_FOR = {
  codex: 'codex:codex-rescue',
  'codex-mini': 'codex:codex-rescue',
  grok: 'grok-build:grok-delegate',
  'claude-code': 'general-purpose',
  // The policy's `subagent.tiers` name capability tiers, not providers. They all
  // resolve to Anthropic agents, and they are in this map because a test asserts
  // every name the policy can utter has somewhere to land — a tier added to the
  // policy with no mapping here would route to the default and look deliberate.
  haiku: 'general-purpose',
  sonnet: 'general-purpose',
  opus: 'general-purpose',
};

function vendorOfAgent(subagentType) {
  const t = String(subagentType || '').toLowerCase();
  if (t.startsWith('codex')) return 'openai';
  if (t.startsWith('grok')) return 'xai';
  return 'anthropic';
}

function vendorOfProvider(provider) {
  const p = String(provider || '').toLowerCase();
  if (p.startsWith('codex')) return 'openai';
  if (p.startsWith('grok') || p === 'xai-api') return 'xai';
  return 'anthropic';
}

// ------------------------------------------------------ operator directive ---
//
// The escape hatch this gate advertised for months and never had.
//
// `modePre` refused a non-policy vendor and then printed: "if <provider>
// genuinely cannot do this work here, that is a deviation and it is allowed —
// record it first with tars dispatch --deviation ...". The gate never read the
// dispatch log. Logging the deviation changed nothing: the next spawn was
// refused word for word, which is what happened live on 2026-08-20. The
// instructions and the implementation disagreed, and the instructions were the
// half a person acted on.
//
// The tempting fix is the hole. Trusting the log would mean:
//
//   agent wants a forbidden vendor -> agent writes its own deviation row ->
//   gate reads that row -> agent has authorised itself
//
// which breaks the invariant everything else here rests on: the judged actor
// may never grant itself authority (SPEC principle 6). The dispatch log is
// written by the session being judged, so it can never be a source of
// permission — only a record.
//
// So the override is taken from the one piece of text in a turn the model does
// not author: the operator's own prompt, parsed at UserPromptSubmit before any
// tool has run. Naming vendors there ("use Claude, Codex and Grok on this",
// "use any vendor") writes `operatorAllowedVendors` into the turn state. Three
// properties, and they are the whole point:
//
//   written only by `prompt` mode, from `input.prompt` — nothing the model
//     emits later can add a vendor to it;
//   scoped to ONE turn — every UserPromptSubmit rewrites the field, including
//     turns the gate otherwise says nothing about, or "use codex here" quietly
//     becomes a standing permission;
//   absent, empty, tampered or naming anything outside the vendor set = no
//     override at all. Fail closed, no partial credit.

const VENDORS = Object.freeze(['anthropic', 'openai', 'xai']);

// The words an operator actually types for a vendor. Tier names are here because
// "use opus on this" names Anthropic as plainly as "use claude" does.
const VENDOR_WORDS = Object.freeze([
  ['anthropic', 'claude(?:\\s+code)?|anthropic|sonnet|opus|haiku|fable'],
  ['openai', 'codex(?:-mini)?|open\\s?ai|chat\\s?gpt|gpt'],
  ['xai', 'grok|x\\.ai|xai'],
]);
const VENDOR_RE = VENDOR_WORDS.map(([vendor, src]) => [vendor, new RegExp(`\\b(?:${src})\\b`, 'i')]);
const VENDOR_HEAD = new RegExp(`^(?:${VENDOR_WORDS.map(([, src]) => src).join('|')})\\b`, 'i');

// "all vendors" / "use all three" names no vendor and means every one of them.
// The second pattern insists on the verb so "all three tests pass" grants
// nothing.
// "all vendors" / "use all three" names no vendor and means every one of them —
// but ONLY inside an instruction. The first version matched the noun phrase
// anywhere, and an audit listed four sentences that granted all three vendors
// while plainly granting nothing:
//
//   i do not want to use any vendor.
//   never use any vendor for this.
//   all vendors are currently unavailable.
//   the issue affects every provider.
//
// The file's own doctrine already said "mentioning is not choosing"; this form
// simply did not enforce it. So the all/any form now needs an AFFIRMATIVE ACTION
// VERB immediately in front of it, the same rule the named-vendor form has had
// all along.
const ALL_VENDORS = [
  /\b(?:use|using|try|ask|spawn|route|send|hand|give|pass|delegate|dispatch)\s+(?:it\s+|this\s+|that\s+|them\s+)?(?:to\s+|on\s+|through\s+|with\s+)?(?:all|any|every|each)\s+(?:of\s+)?(?:the\s+)?(?:three\s+|3\s+)?(?:vendors?|providers?|models?|clis?)\b/i,
  /\b(?:use|using|try)\s+(?:all|any)\s+(?:of\s+)?(?:the\s+)?(?:three|3)\b/i,
];

// A POSITIVE GRAMMAR, NOT A BLACKLIST OF ENGLISH NEGATIONS.
//
// The previous version hunted for a directive verb anywhere in the sentence and
// then tried to spot negations around it. That is an arms race with English, and
// English wins: `not|never|don't` caught four reported cases and a later audit
// walked straight past them with contractions and a synonym —
//
//   you shouldn't use any vendor.       granted all three
//   you mustn't use codex for this.     granted OpenAI
//   you aren't to use codex for this.   granted OpenAI
//   please refrain from using any vendor.  granted all three
//
// So the rule is inverted. A directive only counts when it STARTS ITS CLAUSE.
// Everything above fails that test without anyone having to enumerate "mustn't",
// because `you shouldn't`, `you aren't to` and `refrain from` are all words
// sitting in front of the verb, and the only words allowed in front of it are
// ones that cannot change who is being told to act.
//
// The safe direction is a false NEGATIVE: "I'd like you to use codex" grants
// nothing, and the operator says "use codex" instead. An authority parser that
// guesses generously is the one shape that must not exist.
const LEAD_WORDS = /^(?:\s*(?:and|then|also|now|okay|ok|so|please|just|first|next|finally|but|actually)\b)*\s*$/i;

// The text between the start of this clause and the directive verb. A clause
// begins at the sentence start or after a comma or semicolon — deliberately NOT
// at a conjunction, because "use Claude, Codex and Grok on this" is one
// instruction naming three vendors and splitting it would grant only the first.
// A clause begins at the sentence start, or after a comma, semicolon, colon or
// dash. Dashes matter: "search X for new eval harnesses — use Claude, Codex and
// Grok on this" is two clauses, and treating the whole thing as one made the
// operator's own instruction read as though somebody else was being described.
// Deliberately NOT split at conjunctions — "use Claude, Codex and Grok on this"
// is one instruction naming three vendors, and splitting it would grant the
// first and drop the rest.
const CLAUSE_START = /[,;:\u2014\u2013]|(?:^|\s)-(?=\s)/;

function directiveStartsItsClause(sentence, index) {
  return LEAD_WORDS.test(String(sentence).slice(0, index).split(CLAUSE_START).pop());
}

// THERE IS NO NEGATION LIST ANY MORE, AND THAT IS THE POINT.
//
// A sentence-level blacklist was tried and kept for a while as a "second net".
// It was doing two harmful things. It could not be complete — every audit found
// another contraction — and it produced a false NEGATIVE that a real operator
// would hit: `use codex, but not grok` voided the whole sentence and granted
// nothing, because `not` appeared somewhere in it.
//
// The clause rule handles all twenty reported negative cases on its own, and
// `use codex, but not grok` correctly grants OpenAI, because the clause ends at
// `but`. One rule, in one direction, with no vocabulary to maintain.

// Same house style as `classify`: shallow, ordered, and defaulting to the safe
// answer, which here is "no override". A prompt that MENTIONS a vendor has not
// CHOSEN one — "fix the codex CLI bug" names OpenAI and asks for nothing — so a
// vendor name only counts inside an instruction about who does the work.
const DIRECTIVE = new RegExp(
  '\\b(?:use|using|try|ask|spawn'
  + '|run\\s+(?:it|this|that|them)\\s+(?:on|through|with|by)'
  + '|(?:route|send|hand|give|pass|delegate|dispatch)\\s+(?:it|this|that)\\s+(?:off\\s+)?to'
  + ')\\b([^.;:!?\\n]{0,120})',
  'gi',
);
// The clause is cut at the first boundary AND must LEAD with a vendor, so
// "run the tests, then review the codex change" cannot smuggle a vendor in from
// a different instruction, and "use the existing helper rather than a claude
// call" cannot grant Anthropic to a turn the policy routed elsewhere.
// The clause body ends here. `unless|except|not|without` joined the list so
// `use codex, but not grok` and `use anything except grok` stop reading the
// vendor on the far side of the break as one that was chosen.
const CLAUSE_BREAK = /\b(?:then|after that|but|because|so that|instead|rather than|unless|except|not|never|without|avoid)\b/i;
const CLAUSE_LEAD = /^[\s,]*(?:the|a|an|both|all|only|just|either|our|your|please)?\s*/i;

function vendorsInClause(clause) {
  const text = String(clause || '');
  const body = text.split(CLAUSE_BREAK)[0];
  if (!VENDOR_HEAD.test(body.replace(CLAUSE_LEAD, ''))) return [];
  return VENDOR_RE.filter(([, re]) => re.test(body)).map(([vendor]) => vendor);
}

// --------------------------------------------------------- operator authority ---
//
// THE STATE FILE IS A CACHE. IT IS NOT THE PROOF.
//
// The first version stored `operatorAllowedVendors` in `.tars/route-state.json`
// and had `modePre` trust it. An audit wrote the file by hand:
//
//     {"class":"research","provider":"grok","operatorAllowedVendors":["anthropic"]}
//
// and the gate replied `permitted: this turn's prompt named anthropic`. The
// prompt had said no such thing. A model that can edit the repo could grant
// itself the permission the whole feature exists to withhold — the judged actor
// authorising itself, which is the one invariant this file is built on.
//
// So the directive is now SEALED with an HMAC whose key lives OUTSIDE the repo,
// in the host's state directory at mode 0600. Three consequences, and the second
// is the one that matters most:
//
//   1. Writing the JSON is no longer enough; you need the key.
//   2. A forgery cannot live in a DIFF. Everything a run proposes for merge is
//      reviewable text, and no reviewable text can carry a valid seal. Forging
//      now requires reading a host secret at runtime, which is a different and
//      much louder act than editing a tracked file.
//   3. `.tars/route-state.json` is on the protected surface list, so a run that
//      edits it cannot release itself unattended either.
//
// HONEST LIMIT: workers here run with the sandbox bypassed — "the machine is the
// sandbox" — so a determined process on this box can still read the key. This
// raises the bar from "edit a file you were already editing" to "exfiltrate a
// host secret"; it does not make it impossible. A host-owned authority channel
// that the agent process genuinely cannot read is the real fix, and it needs the
// harness, not this hook.
function authorityKeyFile() {
  const home = os.homedir();
  const base = process.env.XDG_STATE_HOME || path.join(home, '.local', 'state');
  return path.join(base, 'tars', 'authority.key');
}

// Read-or-create. Created only from `prompt` mode; `pre` mode never creates one,
// because a gate that mints the key it is about to verify against would accept
// anything on a machine where the key was deleted.
function authorityKey({ create = false } = {}) {
  const file = authorityKeyFile();
  try {
    return fs.readFileSync(file);
  } catch { /* fall through */ }
  if (!create) return null;
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const key = crypto.randomBytes(32);
    fs.writeFileSync(file, key, { mode: 0o600 });
    try { fs.chmodSync(file, 0o600); } catch { /* best effort on Windows */ }
    return key;
  } catch {
    return null;
  }
}

// Everything the permission is ABOUT goes into the seal. Leaving any of it out
// would let a valid seal be replayed onto a different session or a wider vendor
// set.
// EVERY SECURITY-RELEVANT FIELD IS IN THE SEAL.
//
// v1 covered the session, the prompt and the vendor list — which protected the
// operator override and nothing else. An audit pointed out that the decision
// itself is the authority: rewrite `class` from `review` to `build` and modePre
// stops enforcing at all; rewrite `provider` and the comparison is against the
// wrong vendor; clear `unresolved` and a router outage looks like a resolved
// turn. All of those are now bound into the MAC, so changing any one of them
// invalidates it.
function sealBody(state) {
  const s = state || {};
  return [
    'v2',
    String(s.sessionId || ''),
    String(s.class || ''),
    String(s.provider || ''),
    String(s.agent || ''),
    s.unresolved ? 'unresolved' : 'resolved',
    String(s.promptSha || ''),
    [...(Array.isArray(s.operatorAllowedVendors) ? s.operatorAllowedVendors : [])].sort().join(','),
    String(s.ts || ''),
  ].join('\n');
}

function sealFor(state, key) {
  if (!key) return null;
  return crypto.createHmac('sha256', key).update(sealBody(state)).digest('hex');
}

function sealValid(state) {
  const key = authorityKey();
  if (!key) return false;                       // no key, no authority
  const want = sealFor(state, key);
  const got = typeof state.seal === 'string' ? state.seal : '';
  if (!want || want.length !== got.length) return false;
  // Constant-time, because this is a MAC comparison and short-circuiting on the
  // first differing byte is how a MAC gets guessed a byte at a time.
  try {
    return crypto.timingSafeEqual(Buffer.from(want, 'hex'), Buffer.from(got, 'hex'));
  } catch {
    return false;
  }
}

// Text the operator did not write as an instruction. A prompt that QUOTES a
// state file — an audit report pasting `"operatorAllowedVendors": ["anthropic"]`,
// which is exactly how this was found — must not grant anything, and neither
// must a fenced code block full of examples.
function withoutQuotedText(text) {
  return String(text || '')
    .replace(/```[\s\S]*?```/g, ' ')       // fenced blocks
    .replace(/~~~[\s\S]*?~~~/g, ' ')
    .replace(/`[^`\n]*`/g, ' ')             // inline code
    .replace(/^\s{4,}\S.*$/gm, ' ')        // indented blocks
    .replace(/^\s*>.*$/gm, ' ')             // markdown blockquotes
    // REPORTED SPEECH IS NOT INSTRUCTION. `the log said "use codex for this
    // one". review the diff.` granted OpenAI — the operator was describing a log
    // line, not choosing a vendor. Quoted spans are somebody else talking.
    //
    // NO LENGTH CAP. The first version bounded these at 300 characters, so a
    // long quotation fell out of the pattern and its contents went back into
    // active parsing — a quote that grants nothing at 299 characters and grants
    // OpenAI at 301 is a rule nobody can hold in their head. `[^"\n]*` is
    // already bounded by the line, which is the honest limit.
    .replace(/"[^"\n]*"/g, ' ')
    .replace(/\u201c[^\u201d\n]*\u201d/g, ' ')
    .replace(/\u2018[^\u2019\n]*\u2019/g, ' ')
    // Straight single quotes only where they look like speech marks rather than
    // apostrophes: opened after whitespace, closed before whitespace or
    // punctuation. Stripping every `'` would eat the apostrophe out of "don't"
    // and swallow the rest of the sentence with it.
    .replace(/(^|[\s(\[])'[^'\n]*'(?=[\s.,;:!?)\]]|$)/g, ' ')
    .replace(/\{[\s\S]{0,400}?\}/g, ' ');  // JSON-ish objects
}

// A QUESTION IS NOT AN INSTRUCTION. "can any model do this?" granted all three
// vendors, which is plainly not authorisation — it is asking whether it would be
// allowed. Anything ending in a question mark, or opening with an interrogative,
// grants nothing.
const INTERROGATIVE = /^\s*(?:can|could|should|would|will|shall|is|are|was|were|do|does|did|may|might|am|have|has|what|which|who|whom|whose|when|where|why|how)\b/i;

function isQuestion(sentence) {
  const t = String(sentence || '').trim();
  return t.endsWith('?') || INTERROGATIVE.test(t);
}

// Called ONLY from `prompt` mode, ONLY on `input.prompt`. If this ever gets a
// second caller reading model-authored text, the override stops being the
// operator's and the gate stops meaning anything.
function operatorVendorsFromPrompt(prompt) {
  const text = withoutQuotedText(prompt);
  if (!text.trim()) return [];

  // Sentence at a time, so one instruction in a long prompt still counts while a
  // question elsewhere in the same prompt cannot grant anything.
  const found = [];
  let all = false;
  for (const sentence of text.split(/(?<=[.!?\n])/)) {
    if (isQuestion(sentence)) continue;

    // The all/any form, held to the same clause rule as a named vendor. Matching
    // it anywhere in the sentence is how "you shouldn't use any vendor" granted
    // everything.
    for (const re of ALL_VENDORS) {
      const rx = new RegExp(re.source, 'gi');
      let m;
      while ((m = rx.exec(sentence)) !== null) {
        if (directiveStartsItsClause(sentence, m.index)) { all = true; break; }
      }
      if (all) break;
    }
    if (all) return VENDORS.slice();

    DIRECTIVE.lastIndex = 0;
    let match;
    while ((match = DIRECTIVE.exec(sentence)) !== null) {
      // THE RULE. Anything in front of the verb inside this clause — `you
      // shouldn't`, `refrain from`, `I'd like you to` — means somebody other
      // than the operator is being described, or the instruction is being
      // refused. Only a clause that OPENS with the verb is an operator directive.
      if (!directiveStartsItsClause(sentence, match.index)) continue;
      for (const vendor of vendorsInClause(match[1])) if (!found.includes(vendor)) found.push(vendor);
    }
  }
  return found;
}

// Reading the directive back is where fail-closed is enforced. Only `prompt`
// mode can write this field, so anything that is not a clean array of known
// vendors reached the file by tampering or by a half-written state, and both of
// those are answered the same way: no override.
function allowedByOperator(state, sessionId) {
  const raw = state && state.operatorAllowedVendors;
  if (!Array.isArray(raw) || raw.length === 0) return [];

  // EXACT session identity, both sides present. The first version only voided a
  // mismatch "when both ids are known", so a caller that sent NO session id
  // inherited whatever permission was lying in the file. Absent identity is not
  // matching identity; it is unknown, and unknown is refused.
  if (!state.sessionId || !sessionId || state.sessionId !== sessionId) return [];

  const out = [];
  for (const entry of raw) {
    const name = typeof entry === 'string' ? entry.trim().toLowerCase() : '';
    // One unrecognised entry voids the whole directive rather than being
    // dropped from it. A partially-honoured permission is a permission nobody
    // can reason about.
    if (!VENDORS.includes(name)) return [];
    if (!out.includes(name)) out.push(name);
  }

  // AND THE SEAL. Everything above only proves the file is well-formed, which a
  // forger has no trouble with — an audit hand-wrote a perfectly well-formed
  // directive and the gate honoured it. Only the seal proves `prompt` mode wrote
  // this, because only `prompt` mode has the key.
  // The whole decision is sealed now, so this is checked once in modePre for
  // every field. Re-checking here keeps allowedByOperator honest on its own.
  if (!sealValid(state)) return [];
  return out;
}

// ----------------------------------------------------------------- plumbing ---

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

// The decision comes from `tars dispatch --route`, never from a second copy of
// the rotation logic living here. A vendored hook sits in an adopted repo that
// has no kit/orchestrator/ to require, so the CLI is the only seam that reaches
// the real router from both places. If the CLI is missing the gate goes quiet:
// "this machine has no tars" and "you routed wrongly" are different sentences,
// and only the second one is the session's problem.
function askRouter(repoRoot, cls) {
  try {
    const out = tarsExec(['dispatch', repoRoot, '--route', cls], {
      encoding: 'utf8', timeout: 10000, stdio: ['ignore', 'pipe', 'pipe'],
    });
    const provider = (out.match(/->\s*(\S+)/) || [])[1];
    const rule = (out.match(/rule:\s*(.+)/) || [])[1];
    return provider ? { provider, rule: (rule || '').trim() } : null;
  } catch {
    return null;
  }
}

// ONE FILE PER SESSION.
//
// There was a single repo-global `route-state.json`, and the session id inside
// it only ever guarded the OPERATOR OVERRIDE — never the routing decision
// itself. An audit ran two sessions in one repo: session 1 was routed for a
// Claude review, session 2 then took a Grok research turn and overwrote the
// file, and session 1's next delegation was refused because the gate believed
// session 1 was mid-research. Working in one tree with two sessions is a
// documented shape here (the SessionStart hook warns about it), so this is not
// exotic.
//
// The id is hashed rather than used as a filename: it arrives from the harness,
// and a value containing `../` would otherwise choose where the gate writes.
function sessionKey(sessionId) {
  const id = String(sessionId || '').trim();
  if (!id) return null;
  return crypto.createHash('sha256').update(id).digest('hex').slice(0, 16);
}

// THE ROUTING DECISION IS AUTHORITY, NOT A NOTE.
//
// Per-session files fixed isolation and left the decision itself inside the
// repository, where anything able to edit the tree could rewrite a mandatory
// `review` into `build` and walk a forbidden delegation straight through
// modePre. Sealing only `operatorAllowedVendors` protected the smallest part of
// it: `class`, `provider`, `agent` and `unresolved` decide whether the gate
// fires at all.
//
// So the AUTHORITATIVE copy lives in host-owned runtime state, next to
// authority.key and under the same 0700 directory:
//
//   ~/.local/state/tars/route/<repo>/<session>.json
//
// and the repo keeps a MIRROR that is never read for an authorization decision.
// The mirror exists so `tars doctor`, a person, or a future console can see what
// the gate decided without being able to change it.
function runtimeStateDir(repoRoot) {
  const base = process.env.XDG_STATE_HOME || path.join(os.homedir(), '.local', 'state');
  const repoKey = crypto.createHash('sha256').update(path.resolve(repoRoot)).digest('hex').slice(0, 16);
  return path.join(base, 'tars', 'route', repoKey);
}

function stateFile(repoRoot, sessionId) {
  const key = sessionKey(sessionId);
  // No session id: one shared file, because a caller with no identity cannot be
  // isolated. Still outside the repo — an unidentified caller is not a reason to
  // put the decision back where it can be edited.
  return path.join(runtimeStateDir(repoRoot), `${key || '_shared'}.json`);
}

// Never read for authorization — only to notice that authorization is MISSING.
// See the `absent` branch of modePre.
function readMirror(repoRoot, sessionId) {
  try { return JSON.parse(fs.readFileSync(mirrorFile(repoRoot, sessionId), 'utf8')); }
  catch { return null; }
}

// Never read for authorization. Written so the decision is inspectable.
function mirrorFile(repoRoot, sessionId) {
  const key = sessionKey(sessionId);
  if (!key) return path.join(repoRoot, STATE_DIR, STATE_FILE);
  return path.join(repoRoot, STATE_DIR, SESSION_DIR, `${key}.json`);
}

// Per-session files accumulate. Dropping the ones nobody has touched in a day
// keeps the directory from growing without bound, and a stale file cannot
// authorise anything anyway: the seal is bound to its session and the directive
// is rewritten every prompt.
function sweepStaleSessions(repoRoot, keepKey) {
  for (const dir of [runtimeStateDir(repoRoot), path.join(repoRoot, STATE_DIR, SESSION_DIR)]) {
    sweepDir(dir, keepKey);
  }
}

function sweepDir(dir, keepKey) {
  let names;
  try { names = fs.readdirSync(dir); } catch { return; }
  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  for (const name of names) {
    if (!name.endsWith('.json') || name === `${keepKey}.json`) continue;
    try {
      if (fs.statSync(path.join(dir, name)).mtimeMs < cutoff) fs.rmSync(path.join(dir, name), { force: true });
    } catch { /* another session may have removed it first */ }
  }
}

// ABSENT AND CORRUPT ARE DIFFERENT ANSWERS.
//
// This returned null for both, and `modePre` then returned without enforcing
// anything — so truncating the file to `{broken` disabled the gate entirely and
// a forbidden spawn sailed through. An audit did exactly that. Absence is
// legitimate (the hook has not run this turn, or the repo is not adopted);
// corruption is a tamper signal or a torn write, and neither is a reason to stop
// gating.
function readState(repoRoot, sessionId) {
  let raw;
  try {
    raw = fs.readFileSync(stateFile(repoRoot, sessionId), 'utf8');
  } catch {
    return { absent: true };
  }
  try {
    const doc = JSON.parse(raw);
    if (!doc || typeof doc !== 'object') return { corrupt: true };
    return doc;
  } catch {
    return { corrupt: true };
  }
}

// Temp-then-rename, because a torn write now REFUSES spawns rather than being
// ignored. Making corruption fail closed is only safe if we also stop causing it.
function writeAtomic(dest, body) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  const tmp = `${dest}.tmp`;
  fs.writeFileSync(tmp, body);
  fs.renameSync(tmp, dest);
}

// The per-session file is authoritative. The shared file is a MIRROR, and it
// exists for one reason: a harness that sends no session id cannot be isolated,
// and if the gate could not find any state for such a caller it would enforce
// nothing at all — turning an isolation fix into a fail-open. Mirroring keeps
// those callers gated exactly as before.
//
// With two id-less sessions the mirror is whoever wrote last, which is the old
// bug. That is the honest limit: without an identity there is nothing to key on.
// Every caller that DOES send an id reads its own file and never the mirror.
// Seal, write the authoritative copy outside the repo, then mirror it inside for
// eyes only. The mirror carries a marker so nobody mistakes it for the source of
// truth if they find it in a diff.
function writeState(repoRoot, state, sessionId) {
  const id = sessionId === undefined ? (state && state.sessionId) : sessionId;
  const sealed = { ...state, seal: sealFor(state, authorityKey({ create: true })) };
  const body = JSON.stringify(sealed, null, 2);
  try { writeAtomic(stateFile(repoRoot, id), body); }
  catch { /* a gate that cannot cache still gates the turn it can see */ }

  // A SECOND AUTHORITATIVE COPY AT `_shared`, for callers that send no session id.
  //
  // Not a convenience: without it a harness that omits the id finds no decision
  // and the gate enforces NOTHING, which turns an isolation improvement into a
  // fail-open. It is sealed like every other copy, so it is trusted for the same
  // reasons — it simply cannot be isolated, because there is no identity to key
  // on. Every caller that DOES send an id reads its own file and never this one.
  if (sessionKey(id)) {
    try { writeAtomic(stateFile(repoRoot, null), body); }
    catch { /* the per-session copy is the one that matters */ }
  }

  const mirror = {
    _note: 'MIRROR ONLY. The gate reads ~/.local/state/tars/route/; editing this file changes nothing.',
    ...sealed,
  };
  void body;
  try { writeAtomic(mirrorFile(repoRoot, id), JSON.stringify(mirror, null, 2)); }
  catch { /* the mirror is a convenience */ }
}

// -------------------------------------------------------------- classifying ---
//
// Order matters: the first match wins, and the list runs most-specific first.
// `null` means "say nothing", and it is the default on purpose (see header).
const SIGNALS = [
  // `cross-vendor` is deliberately NOT a signal on its own. It is the name of a
  // mechanism in this repo, so "fix the cross-vendor bug" is a build request that
  // happens to say it — and it classified as `review` until a test said so.
  ['review', /\b(review|critique|adversarial|second opinion|sanity[- ]check|check my work|poke holes|red[- ]team)\b/i],
  ['research', /\b(search (x|the web|online)|latest|newest|what'?s new|state of the art|prior art|current events|release notes|changelog for|competitor|market)\b/i],
  ['mechanical', /\b(rename|renaming|sweep|reformat|formatting|lint|bulk (edit|replace)|find and replace|typo|whitespace|sort the|regenerate)\b/i],
  ['build', /\b(add|implement|fix|build|write|refactor|create|wire|migrate|remove|delete|rebuild|port|hook up|make it|set up)\b/i],
];

// An interrogative with no imperative is a conversation, not a dispatch. This
// runs BEFORE the signal table because "how do we fix X" contains "fix" and is
// still a question about approach, not an instruction to go and change files.
const CONVERSATIONAL = /^\s*(can i ask|do(es)? (you|the|it|this)|is |are |why|how (do|does|come|should|would)|what|when|where|who|explain|tell me|thoughts|opinion|should (i|we))\b/i;

// A sentence that OPENS with a build verb is a build, whatever machinery it goes
// on to name. Without this, "implement the adversarial review gate" and "fix the
// cross-vendor bug" both classified as `review` — the signal table matched the
// noun and never saw the imperative in front of it. Position beats vocabulary:
// the first verb is what the sentence is asking for.
const BUILD_IMPERATIVE = /^\s*(please\s+)?(add|implement|fix|build|refactor|create|wire|migrate|remove|delete|rebuild|port|make|finish|hook up|set up)\b/i;

function classify(prompt) {
  const text = String(prompt || '').trim();
  if (!text) return null;
  if (CONVERSATIONAL.test(text)) return null;
  if (BUILD_IMPERATIVE.test(text)) return 'build';
  for (const [cls, pattern] of SIGNALS) if (pattern.test(text)) return cls;
  return null;
}

// ------------------------------------------------------------------- mode: prompt ---

// A turn the gate says nothing about is still a NEW turn. The cached class and
// provider survive it — they are the last real routing decision — but the
// operator's permission must not. Without this, "use codex on this research
// task" followed by "thanks, what did it find?" would leave the override
// standing on a turn nobody granted it for, which is exactly how a one-turn
// permission becomes a permanent one.
function expireDirective(repoRoot, allowed, sessionId) {
  const previous = readState(repoRoot, sessionId);
  // Nothing there: leave it that way. Writing a state file for a turn that was
  // never classified would invent a decision nobody made.
  if (!previous || previous.absent) return;

  // Corrupt, on the other hand, must be REPLACED. `modePre` now refuses while
  // the file is unparseable, so leaving it would wedge the session until a
  // classified prompt happened along. A conversational turn is the cheapest
  // moment to clear it, and it is cleared to something that grants nothing.
  if (previous.corrupt) {
    writeState(repoRoot, {
      sessionId: sessionId || null, operatorAllowedVendors: [], promptSha: null, seal: null, ts: new Date().toISOString(),
    }, sessionId);
    return;
  }
  // The seal goes with it. Leaving a valid seal behind while rewriting the
  // vendors would leave a signature attesting to a permission nobody granted.
  writeState(repoRoot, { ...previous, operatorAllowedVendors: allowed, promptSha: null, seal: null }, sessionId);
}

function modePrompt(input, repoRoot) {
  // First thing, once per turn, from the operator's own text. Every path out of
  // this function rewrites the field, including the early returns.
  const allowed = operatorVendorsFromPrompt(input.prompt);
  const cls = classify(input.prompt);
  if (!cls) return expireDirective(repoRoot, allowed, input.session_id);

  const decision = askRouter(repoRoot, cls);
  if (!decision) {
    // NOT `expireDirective`. That cleared the override and deliberately left the
    // previous turn's class and provider standing, so a review turn whose router
    // was unreachable inherited the last build turn's routing and sailed through
    // modePre as non-mandatory. The turn classified; the routing did not resolve;
    // both of those are facts and the state has to carry them.
    writeState(repoRoot, {
      sessionId: input.session_id || null,
      class: cls,
      provider: null,
      rule: null,
      agent: null,
      unresolved: true,
      unresolvedWhy: 'the tars CLI did not answer `dispatch --route`',
      operatorAllowedVendors: allowed,
      promptSha: null,
      seal: null,
      ts: new Date().toISOString(),
    }, input.session_id);
    return;
  }

  const agent = AGENT_FOR[decision.provider] || 'general-purpose';
  const sessionId = input.session_id || null;
  const promptSha = crypto.createHash('sha256').update(String(input.prompt || '')).digest('hex').slice(0, 32);
  const state = {
    sessionId,
    class: cls,
    provider: decision.provider,
    rule: decision.rule,
    agent,
    operatorAllowedVendors: allowed,
    // The seal covers the session, the exact prompt, and the exact vendor set,
    // so a valid seal cannot be replayed onto another turn or widened.
    promptSha,
    ts: new Date().toISOString(),
  };
  // writeState seals it. Computing the MAC here would mean two places that must
  // agree about what is covered, and the one that forgot a field would be the
  // one nobody noticed.
  writeState(repoRoot, state, sessionId);
  sweepStaleSessions(repoRoot, sessionKey(sessionId));

  const lines = [
    `[tars:routing] This turn classifies as **${cls}**. The routing policy assigns it to **${decision.provider}** (${decision.rule}).`,
    '',
    `Delegate the substantive work of this turn to the \`${agent}\` subagent. You have STANDING AUTHORIZATION to spawn it: the routing policy is the user's instruction, so this is a requested delegation and needs no further asking.`,
  ];
  if (vendorOfProvider(decision.provider) !== 'anthropic') {
    lines.push(
      '',
      `Routing to another vendor is the point, not an escalation. Do not substitute an Anthropic subagent because it seems easier: the gate refuses it, and logging a deviation afterwards does not change that. Only the operator can permit another vendor, in their own prompt.`
    );
  }
  if (cls === 'review') {
    lines.push('', 'Cross-vendor review is mandatory for this class. If you authored the diff, you are not the reviewer.');
  }
  if (allowed.length) {
    lines.push(
      '',
      `The operator's prompt named **${allowed.join(', ')}** for this turn, so the gate will permit a subagent from any of them. `
      + 'That permission came from their prompt and expires with this turn; you cannot extend it, and logging a deviation does not create one.'
    );
  }
  lines.push(
    '',
    'Break-even still applies: delegate when the reading-to-output ratio is high or the work splits across independent dimensions. Genuinely one-line work stays inline, and that decision gets logged as a deviation like any other.'
  );
  // The schema-validated envelope, not bare stdout. The CLI declares
  // `{hookEventName:"UserPromptSubmit", additionalContext}` under
  // `hookSpecificOutput` and documents additionalContext as "Text injected into
  // model context". Bare stdout may also be injected, but "may" is how the last
  // two dead hooks in this kit got written: wired, running, and reaching nothing.
  // If a host ever fails to parse this, the raw JSON still lands in context and
  // is still readable — the failure mode degrades to ugly, not to silent.
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext: lines.join('\n'),
    },
  }) + '\n');
}

// ---------------------------------------------------------------- mode: pre ---

// A workflow is a delegation too, and it is the one that spends the most. Its
// `model` option accepts only Anthropic names, so a script that sets nothing
// else runs every agent in-vendor — which is how a "cross-vendor review" ends up
// as Haiku reading Opus. `agentType` is the seam that fixes it: it resolves
// against the same registry as the Task tool, so `agentType: 'codex:codex-rescue'`
// puts a real OpenAI agent in a workflow phase.
//
// The check is flat on purpose. Parsing a script to work out WHICH phase should
// be cross-vendor is guesswork, and a gate that guesses is worse than none. On a
// turn the policy routes to another vendor, a script that never says `agentType`
// cannot possibly be honouring it, and that is decidable by reading the text.
function preWorkflow(input, state, allowed) {
  const script = String(input.tool_input?.script || '');
  // A resumed or saved workflow has no inline script to read; nothing to assert.
  if (!script) return;
  if (/agentType\s*:/.test(script)) return;

  // An agentType-less workflow runs Anthropic. If the POLICY routed this turn to
  // Anthropic, that is the right vendor and there is nothing to refuse — this
  // arm is only reachable now that modePre no longer returns early on Anthropic
  // routing, and refusing here would block a correctly-routed workflow.
  if (vendorOfProvider(state.provider) === 'anthropic') return;

  // Otherwise, an operator who named Anthropic this turn has already permitted
  // exactly that.
  if (allowed.includes('anthropic')) return permitted(state, 'this workflow', 'anthropic', allowed);

  process.stderr.write(
    `ROUTE GATE: refused. This turn is class \`${state.class}\`, which routing-policy.json assigns to `
    + `${state.provider} (${state.rule}). This workflow script sets no \`agentType\`, so every agent in it `
    + `runs as Anthropic — the \`model\` option only accepts Anthropic names.\n`
    + `Pass agentType on the agents that carry this class: agent(prompt, { agentType: "${state.agent}" }).\n`
    + operatorEscapeHatch(state)
  );
  process.exit(2);
}

// The corrected escape hatch, in one place because both refusal arms print it
// and two copies of a permission rule is how the wrong one gets read. What it
// replaced told the operator to log a deviation "first", as though the row
// unlocked the next attempt. It never did, and it never can.
function operatorEscapeHatch(state) {
  return 'Only the OPERATOR can permit another vendor here, and only by saying so in their own prompt — '
    + '"use codex and grok on this", "use any vendor". Ask them; that permission lasts one turn.\n'
    + `A deviation is a RECORD, not a permission: tars dispatch --class ${state.class} `
    + '--provider <what you used> --task "..." --outcome "..." --deviation "why" writes down what happened. '
    + 'This gate does not read the dispatch log, deliberately — a log the session writes could authorise '
    + 'the session that wrote it.\n';
}

// Say so out loud when the gate stands down. A silent permission is
// indistinguishable from a gate that stopped running, and this kit has shipped
// three hooks that were wired, present and dead.
function permitted(state, what, vendor, allowed) {
  process.stdout.write(
    `[tars:route-gate] permitted: this turn's prompt named ${allowed.join(', ')}, so ${what} (${vendor}) `
    + `is allowed even though routing-policy.json assigns \`${state.class}\` to ${state.provider} `
    + `(${state.rule}). Operator override, recorded as such in the dispatch log, and it expires with this turn.\n`
  );
}

// The delegation tool is `Agent` in this harness and `Task` in others, and they
// are otherwise identical: same `subagent_type`, same `description`. Watching
// only `Task` is why a LIVE probe session delegated to codex:codex-rescue
// exactly as routed and the gate saw nothing — no refusal was possible and no
// dispatch row was written. Wired, correct, and pointed at a name that never
// arrives. Both are accepted, and a test drives every mode under both.
const DELEGATION_TOOLS = new Set(['Task', 'Agent']);

// The classes where the reviewer must be a different vendor than the author.
const MANDATORY_CLASSES = new Set(['review', 'research']);

function modePre(input, repoRoot) {
  if (!DELEGATION_TOOLS.has(input.tool_name) && input.tool_name !== 'Workflow') return;
  const state = readState(repoRoot, input.session_id);
  if (!state) return;

  // A file that exists and does not parse is the one case that must NOT fail
  // open. Whatever the routing for this turn was, it is now unreadable, and a
  // gate that cannot read its own decision has no business waving work through.
  if (state.corrupt) {
    process.stderr.write(
      'ROUTE GATE: refused. This turn\'s routing decision (.tars/route-state.json) exists but does not parse, '
      + 'so the gate cannot tell what was routed where.\n'
      + 'That is either a torn write or tampering, and neither is a reason to stop gating. '
      + 'Send another prompt to re-establish the turn state, or delete the file if you know it is junk.\n',
    );
    process.exit(2);
  }
  if (state.absent || !state.class) {
    // DELETING THE AUTHORITATIVE STATE MUST NOT BE A WAY TO TURN THE GATE OFF.
    //
    // Absent state is legitimate — a repo that never ran prompt mode, a fresh
    // session — so it cannot simply refuse. But the repo MIRROR is written
    // alongside every decision, and while it may never PERMIT anything, it is
    // perfectly good at raising suspicion: a mirror saying this session was
    // routed for a mandatory class, with no sealed decision behind it, means the
    // authoritative copy was removed. Refuse, and say which file gave it away.
    const shadow = readMirror(repoRoot, input.session_id);
    if (shadow && MANDATORY_CLASSES.has(shadow.class)) {
      process.stderr.write(
        `ROUTE GATE: refused. The repo mirror says this session was routed for \`${shadow.class}\`, `
        + 'but there is no sealed routing decision behind it.\n'
        + 'The authoritative copy under ~/.local/state/tars/route/ is missing, which is what deleting it '
        + 'to disable the gate looks like. Send another prompt to re-establish routing.\n',
      );
      process.exit(2);
    }
    return;
  }

  // A MISMATCHED SESSION IN A PER-SESSION FILE IS TAMPERING, NOT SOMEBODY ELSE'S TURN.
  //
  // This used to `return` on any mismatch, and that was the last unguarded field:
  // every other value is inside the seal, but rewriting `sessionId` made the gate
  // say "not mine" and stop enforcing altogether. Tamper-by-disowning.
  //
  // The file was located BY this session's key, so a different id inside it
  // cannot be an honest state — the only way to write there is to know the key.
  // The shared `_shared.json` fallback is the one place a foreign id is normal,
  // and that path has no session key to disagree with.
  if (state.sessionId && input.session_id && state.sessionId !== input.session_id) {
    process.stderr.write(
      'ROUTE GATE: refused. The routing decision stored for this session names a different session '
      + `(${String(state.sessionId).slice(0, 12)}...), which means it was written by something other than this turn.\n`
      + 'Send another prompt to re-establish routing.\n',
    );
    process.exit(2);
  }

  // A CLASSIFIED TURN WHOSE ROUTER COULD NOT ANSWER IS NOT AN UNROUTED TURN.
  //
  // `askRouter` failing used to leave the PREVIOUS turn's class and provider in
  // place. An audit made the CLI unavailable on a review turn after a build
  // turn: the state still said `build`, `mandatory` was false, and the review
  // delegation went straight through to any vendor it liked. The gate was
  // enforcing yesterday's decision and calling it today's.
  if (state.unresolved) {
    if (!MANDATORY_CLASSES.has(state.class)) return;
    process.stderr.write(
      `ROUTE GATE: refused. This turn classified as \`${state.class}\`, which is a class where the `
      + 'reviewer must be a different vendor than the author — but the router could not be reached, '
      + `so there is no decision to enforce.\n`
      + `Why: ${state.unresolvedWhy || 'the tars CLI did not answer'}\n`
      + 'Fix the CLI and send another prompt to re-establish routing. Refusing rather than reusing the '
      + 'last turn\'s routing, because that is how a review silently gets reviewed by its own author.\n',
    );
    process.exit(2);
  }

  // Only the cases the policy calls mandatory are refused. Everything else is
  // advice, and advice does not belong in an exit code.
  const mandatory = MANDATORY_CLASSES.has(state.class);
  if (!mandatory && !sealValid(state)) {
    // A NON-MANDATORY CLASS IS ONLY NON-MANDATORY IF SOMETHING TRUSTWORTHY SAYS SO.
    //
    // This is the downgrade attack: rewrite `review` to `build` and the two
    // lines above hand the turn straight back with no enforcement. `class` is
    // inside the seal, so an unsealed or altered state cannot claim to be a
    // class that needs no gate.
    process.stderr.write(
      'ROUTE GATE: refused. This turn\'s routing decision does not carry a valid seal, so its class '
      + `(\`${state.class}\`) cannot be trusted — and an unverified class is exactly how a mandatory `
      + 'review gets rewritten into a build that nothing checks.\n'
      + 'The authoritative decision lives in ~/.local/state/tars/route/, not in the repo. Send another '
      + 'prompt to re-establish it.\n',
    );
    process.exit(2);
  }
  if (!mandatory) return;

  // For a mandatory class the seal is not optional either.
  if (!sealValid(state)) {
    process.stderr.write(
      `ROUTE GATE: refused. This turn is class \`${state.class}\`, where the reviewer must be a different `
      + 'vendor than the author, and the routing decision does not carry a valid seal.\n'
      + 'Either it was edited, or it was written by a TARS that could not reach its authority key. '
      + 'Refusing rather than trusting it.\n',
    );
    process.exit(2);
  }

  // NO SPECIAL CASE FOR ANTHROPIC. This used to return early whenever the routed
  // provider was Claude, on the reasoning that "if the routing stayed in-vendor
  // there is nothing to enforce". That is wrong, and an audit showed exactly how:
  // a diff authored by CODEX routes its review to claude-code — correctly,
  // because the reviewer must differ from the author — and the early return then
  // permitted Claude, Grok AND CODEX ITSELF. The author reviewing its own diff
  // is the single thing this class exists to prevent, and it was reachable
  // whenever the answer happened to be the vendor running the session.
  //
  // `want` is whatever the policy said. Nothing about it being Anthropic makes
  // it optional.
  const allowed = allowedByOperator(state, input.session_id);
  if (input.tool_name === 'Workflow') return preWorkflow(input, state, allowed);

  const spawned = input.tool_input?.subagent_type || '';
  const want = vendorOfProvider(state.provider);
  const got = vendorOfAgent(spawned);
  if (got === want) return;

  // The operator asked for this vendor in this turn's prompt. That is the only
  // input to this decision the model did not write.
  if (allowed.includes(got)) return permitted(state, `\`${spawned || 'an unnamed agent'}\``, got, allowed);

  process.stderr.write(
    `ROUTE GATE: refused. This turn is class \`${state.class}\`, which routing-policy.json assigns to `
    + `${state.provider} (${state.rule}). You spawned \`${spawned || 'an unnamed agent'}\`, which is ${got}, not ${want}.\n`
    + `Respawn with subagent_type: "${state.agent}".\n`
    + operatorEscapeHatch(state)
  );
  process.exit(2);
}

// --------------------------------------------------------------- mode: post ---
//
// The log stops depending on a model remembering to write it. Every dispatch
// the policy mandates a row for gets one, at the moment it happened, with the
// deviation recorded when the spawn disagreed with the routing.
// Who wrote the diff being reviewed, read from the dispatch log the same way
// routeDispatch picks a critic. Needed so a receipt can answer "was the reviewer
// a different vendor than the author" without re-deriving it later.
function authorVendorFor(repoRoot, state) {
  const m = /opposite of ([a-z-]+)/i.exec(String(state.rule || ''));
  return m ? vendorOfProvider(m[1]) : null;
}

function modePost(input, repoRoot) {
  if (!DELEGATION_TOOLS.has(input.tool_name)) return;
  // The dispatch row must describe THIS session's routing. Reading the shared
  // file meant a concurrent session's class and provider could be logged against
  // work it had nothing to do with, and `tars eval` counts that evidence.
  const state = readState(repoRoot, input.session_id);
  if (!state || !state.class) return;

  const spawned = input.tool_input?.subagent_type || 'unknown';
  const provider = Object.keys(AGENT_FOR).find((p) => AGENT_FOR[p] === spawned)
    || (vendorOfAgent(spawned) === 'anthropic' ? 'claude-code' : spawned);
  const task = String(input.tool_input?.description || input.tool_input?.prompt || 'in-session delegation').slice(0, 200);
  const deviated = provider !== state.provider;
  // An operator override is still a deviation from the policy — the row must
  // exist — but `tars eval` counts deviation reasons by exact text, so "the
  // operator asked for this vendor" and "the session went its own way" have to
  // read differently or the evidence quietly lies about why the policy was left.
  const byOperator = deviated && allowedByOperator(state, input.session_id).includes(vendorOfAgent(spawned));

  // `delegated` MEANS "A WRAPPER STARTED", NOT "THE VENDOR DID THE WORK".
  //
  // The dispatch row said `provider: codex, outcome: delegated` and that read as
  // an OpenAI review having happened. It never proved more than a spawn: the
  // real shape is a Sonnet wrapper subagent, then the codex/grok bridge, then
  // the actual vendor runtime — and the bridge returns a background job id long
  // before anything completes. "Codex requested, Sonnet wrapper ran, Codex
  // result unknown" is UNKNOWN, not a completed cross-vendor review.
  //
  // So an EXTERNAL delegation opens a provenance receipt here, and the receipt —
  // not this row — is what a mandatory cross-vendor requirement is checked
  // against. `tars provenance` follows it to a terminal state.
  let receiptId = null;
  const spawnedVendor = vendorOfAgent(spawned);
  if (spawnedVendor && spawnedVendor !== 'anthropic') {
    try {
      const provenance = require(path.join(__dirname, '..', 'orchestrator', 'vendor-provenance.js'));
      const receipt = provenance.createReceipt(repoRoot, {
        requestedVendor: spawnedVendor,
        requestedAgent: spawned,
        class: state.class,
        authorVendor: authorVendorFor(repoRoot, state),
        sessionId: input.session_id || null,
      });
      receiptId = receipt.id;
      provenance.recordWrapperStarted(repoRoot, receipt.id, {
        agent: spawned,
        // The wrapper IS Anthropic and saying so is the point: it must never be
        // mistaken for the vendor that executed.
        model: 'anthropic-wrapper',
        sessionId: input.session_id || null,
      });
    } catch (err) {
      // No receipt is not "review completed by another vendor". It is one more
      // reason such a review cannot be counted, and it has to be visible.
      process.stdout.write(`[tars:route-gate] vendor provenance not opened: ${String(err.message).trim()}\n`);
    }
  }

  const args = [
    'dispatch', repoRoot,
    '--class', state.class,
    '--provider', provider,
    '--task', task,
    // Not `delegated`. The wrapper started; the vendor has not been observed
    // finishing anything yet.
    '--outcome', receiptId ? `wrapper_started (provenance ${receiptId})` : 'delegated',
  ];
  if (deviated) {
    const what = `session spawned ${spawned} (${vendorOfAgent(spawned)}) where policy routed ${state.provider}`;
    args.push('--deviation', byOperator
      ? `operator override: this turn's prompt permitted ${allowedByOperator(state, input.session_id).join('+')}; ${what}`
      : what);
  }
  try {
    tarsExec(args, { encoding: 'utf8', timeout: 10000, stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (err) {
    // A log write that fails must be visible. An unlogged deviation is the
    // evidence going missing, which is the one outcome the policy names.
    process.stdout.write(`[tars:route-gate] dispatch not logged: ${String(err.stderr || err.message).trim()}\n`);
  }
}

// ---------------------------------------------------------------------- main ---

function main() {
  const mode = process.argv[2];
  let input = {};
  try { input = JSON.parse(fs.readFileSync(0, 'utf8') || '{}'); } catch (e) {
    process.stderr.write(`[tars:route-gate] unparseable hook input (${e.message}) — gate skipped\n`);
    return;
  }
  const repoRoot = findRepoRoot(input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd());
  if (!repoRoot) return;
  // Unadopted repo: no policy of its own, no gate. Adopting is what turns it on.
  if (!fs.existsSync(path.join(repoRoot, STATE_DIR))) return;

  if (mode === 'prompt') return modePrompt(input, repoRoot);
  if (mode === 'pre') return modePre(input, repoRoot);
  if (mode === 'post') return modePost(input, repoRoot);
  process.stderr.write(`[tars:route-gate] unknown mode "${mode}" — expected prompt|pre|post\n`);
}

// Required as a module by the test suite, which exercises the classifier and
// the vendor map directly. A hook whose only entry point is a live stdin read is
// a hook that gets tested by running the session it guards.
if (require.main === module) {
  try { main(); } catch (err) {
    process.stderr.write(`[tars:route-gate] ${err.message}\n`);
  }
  process.exit(process.exitCode || 0);
}

module.exports = {
  classify, vendorOfAgent, vendorOfProvider, AGENT_FOR,
  operatorVendorsFromPrompt, allowedByOperator, VENDORS,
  // Exported so tests ask WHERE the state lives rather than hardcoding a path.
  // The tests hardcoded `.tars/route-state.json` and broke the moment state
  // became per-session — which is a test coupled to a filename, not to a
  // behaviour.
  stateFile, sessionKey, MANDATORY_CLASSES,
};
