---
description: Run this repo's verify manifest before claiming work is done
argument-hint: [repo-path]
---

Run every verifier this repo declares:

```
tars verify $ARGUMENTS
```

The commands come from `verify` in `.tars/profile.json` — the same manifest
listed under "Verification" in `AGENTS.md`, and the same one the runner gates
nodes on. It runs each in turn and exits non-zero if any fail.

Run this before saying work is complete. If something fails for reasons that
pre-date the change, say so explicitly and paste the failure output; never
silently skip a failing verifier.
