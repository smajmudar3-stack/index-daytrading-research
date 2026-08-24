---
description: Ask the routing policy where work should go, or log a dispatch that just happened
argument-hint: route <class> | <class> <provider> "<task>" <outcome> [deviation reason]
---

Arguments: $ARGUMENTS

Two modes, both backed by `tars dispatch` — the same router code the runner
uses, so a session and a run never disagree about where work goes.

**Asking where work should go.** When the argument starts with `route` (or is
just a class name):

```
tars dispatch --route <class>
```

Classes are `build`, `review`, `research`, `mechanical`. It prints the provider
the policy selects and the rule that produced it, reading the tail of
`.tars/dispatch-log.jsonl` so build dispatches genuinely alternate across
vendors instead of restarting from the same one. Report the provider and the
rule, then dispatch there.

**Recording a dispatch.** When arguments name a class and a provider:

```
tars dispatch --class <c> --provider <p> --task "..." --outcome <o> [--deviation "..."]
```

This appends one schema-correct line to `.tars/dispatch-log.jsonl`. If the
provider differs from what `--route` would have chosen, `--deviation` is
required and the CLI refuses without it — write the actual reason, not "faster".

If arguments are missing, run `--route` for the class first and ask before
inventing a task description or an outcome.
