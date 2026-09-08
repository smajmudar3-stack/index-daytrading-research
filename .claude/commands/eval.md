---
description: Count routing evidence from the dispatch log
argument-hint: [repo-path] [--all]
---

Run the routing eval and report what it printed:

```
tars eval $ARGUMENTS
```

Folds `.tars/dispatch-log.jsonl` into counts: first-attempt acceptance,
critic verdicts by vendor pair, deviation reasons, blocked nodes, and coverage
(what each metric had to exclude). `--all` also counts sibling repos that carry a
dispatch log; the `SOURCES` table names every repo included.

Use it before proposing any change to `.tars/routing-policy.json`. The eval
reports numbers only — no scoring, no recommendation. A proposal quotes this
output; the eval never makes the proposal, and the policy file is owner-only.
