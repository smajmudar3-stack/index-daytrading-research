---
description: List orchestrated runs in this repo and their state
argument-hint: [repo-path]
---

List the runs:

```
tars runs $ARGUMENTS
```

Each line is a run id, its status, whether it is live or archived, and its node
and event counts. For detail on one run:

```
tars run-status [repo-path] [runId]
```

with no run id meaning the latest. Read runs through these commands rather than
by opening `.tars/runs/` — that directory is the runner's state, and the
renderer is what turns it into the picture (contract: `docs/run-state.md`).

Use this when asked what is running, what a run did, or which run needs
`tars release`.
