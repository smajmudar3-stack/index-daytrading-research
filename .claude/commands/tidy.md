---
description: Re-audit repo structure against structure.json and refresh the migration report
argument-hint: [repo-path]
---

Audit the repo against its structure doctrine:

```
tars tidy $ARGUMENTS
```

It counts stray root files and unregistered top-level directories against
`.tars/structure.json`, writes a migration report, and exits non-zero when
the repo is untidy. Nothing is moved — the audit never touches files.

Then fix what it found: move each file to its documented home, or, when a file
genuinely needs a new category, create the spot properly — add the home to
`.tars/structure.json` and document its purpose in `AGENTS.md` in the same
change. Do moves on their own branch and re-run `tars verify` before merging.
