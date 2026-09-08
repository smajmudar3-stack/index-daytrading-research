---
name: routing
description: Use when work is about to be dispatched, routed, delegated or handed off — choosing which model or vendor does a piece of work, spawning a subagent, asking for a review or a second pass, cross-vendor review of a diff, a research or audit task, or logging a dispatch. Triggers on dispatch, route, delegate, hand off, farm out, which model, subagent, second opinion, review this diff, cross-vendor, opposite vendor, critic, audit, research brief.
---

# Routing contract

Model routing is policy, not preference. Runs route every node from
`.tars/routing-policy.json` by deterministic code, and sessions are gated against
the same policy by `route-gate` (`docs/routing.md`). This file is the contract —
you can act on it without opening the policy file. The policy file is the source
of truth and is owner-only: read it when you need the exact provider names for
this repo, never edit it to make a dispatch legal.

**You will be told where a turn goes before you plan it.** On every prompt the
gate classifies the turn, asks the router, and states the routed provider and the
subagent that reaches it. Treat that line as the user's instruction: it carries
standing authorization to delegate, so spawning the named subagent is a requested
action, not one to ask about first. A `review` or `research` spawn at the wrong
vendor is refused outright, and the dispatch row is written for you either way.

## The four classes

**build** — writing or changing code. Alternates across `claude-code` and
`codex`; neither vendor is the default. Alternate genuinely: check the tail of
`.tars/dispatch-log.jsonl` and pick the vendor that did not get the last
build dispatch, rather than restarting from the same vendor every session. This
load-balances the Claude Max and Codex Max quotas, and it is why the log matters
even when nobody is reading it.

**review** — reading someone else's diff and judging it. The reviewer must be a
**different vendor** than whoever authored the diff. A same-vendor critic shares
the author's blind spots and rubber-stamps; that is the whole thesis of this kit.
If you wrote the diff, you are not the reviewer.

**research** — outward-facing questions: what is happening in the world, what a
third-party API or vendor does, prior art, current events. Goes to `grok`
(fallback `xai-api`), and lands as a brief file in the repo that build sessions
consume. Research is **not** the class for reading local code — an inventory of
this repo, "find every place X happens", or a read-only audit of files on disk is
a build or mechanical dispatch to a model that can see the working tree, or an
in-session subagent. Sending grok at local code is a routing error.

**mechanical** — renames, sweeps, formatting, bulk edits, log greps: work with a
known answer and no judgement in it. Goes to the cheapest capable tier
(`haiku`, `codex-mini`). Do not spend a frontier model on a rename.

The subagent that reaches each provider: `codex` -> `codex:codex-rescue`,
`grok` -> `grok-build:grok-delegate`, everything Anthropic -> `general-purpose`.
Both vendor plugins ship an agent that drives their own CLI, so cross-vendor
delegation inside a session needs nothing built — only choosing it.

In-session delegation — which subagent tier handles what — follows the
`subagent` section of the routing policy. The break-even is written down there so
it is not re-litigated per task: delegate when the reading-to-output ratio is
high or the work splits across independent dimensions; do it inline when the work
is fast to do directly, because spawn overhead plus cold context makes a one-line
edit slower through a subagent than through your own hands. Read-only work that
produces findings goes to in-session agents; work that produces committed diffs
goes to `tars run`.

## When cross-vendor review is mandatory

Not optional, not a judgement call. A diff gets an opposite-vendor review when it:

- touches **auth** (login, sessions, tokens, permissions, access tiers), or
- touches **payments** or billing, or
- touches **data migrations** (schema changes, backfills), or
- touches **deletion paths** (anything that destroys data or history), or
- exceeds **~200 lines**.

Below those thresholds a review is still good practice; above them, shipping
without one is a deviation and needs a written reason like any other.

## Every dispatch is logged

Append one line per dispatch to `.tars/dispatch-log.jsonl`, with the fields
the policy requires: `ts`, `class`, `provider`, `task`, `outcome`,
`deviationReason`. Use `tars dispatch` (or `/dispatch`) so the line is
schema-correct and the alternate counter stays honest — hand-written JSON drifts
and then the eval cannot count it.

**No silent deviation.** If you route somewhere other than what the policy
selects — a same-vendor reviewer because only one vendor is installed here, a
frontier model on mechanical work because the sweep turned out to need judgement,
a build handled inline because the CLI is down — record it with a reason in
`deviationReason`. The reason is a sentence a human can audit later, not
"faster". Policy changes are earned from that log, so an unlogged deviation is
not a shortcut; it is the evidence going missing.

**A DEVIATION IS A RECORD, NOT A PERMISSION.** This paragraph used to read "that
is allowed, and it is allowed only with the reason recorded", which for the two
MANDATORY classes — `review` and `research` — says the opposite of what is true.
There, `route-gate` refuses the spawn outright and does not read the dispatch
log, deliberately: a log the session writes could otherwise authorise the session
that wrote it, which is the judged actor granting itself authority.

For those two classes only the OPERATOR can permit another vendor, and only by
saying so in their own prompt — "use codex and grok on this", "use any vendor". That
permission is parsed from the prompt at `UserPromptSubmit`, lasts exactly one
turn, and nothing a model emits can create it. Write the deviation row either
way; it is how the evidence stays honest about what actually happened.
