"""Generate per-folder INDEX.md files from real docstrings, not guesses.

Each entry's description is pulled from the file itself -- the first line of a
module docstring, or the first non-heading line of a markdown report -- so the
index cannot drift from what the code actually says it does.
"""
import ast
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "BUNDLE")


def py_desc(path):
    try:
        with open(path, "r", errors="ignore") as f:
            doc = ast.get_docstring(ast.parse(f.read()))
    except (SyntaxError, ValueError, OSError):
        return ""
    if not doc:
        return ""
    return clip(doc.strip().split("\n")[0].strip())


def clip(s, n=110):
    """Cut on a word boundary -- a description severed mid-word reads as broken."""
    s = s.strip()
    if len(s) <= n:
        return s
    return s[:s.rfind(" ", 0, n)].rstrip(" ,;:-\u2014") + " ..."


def md_desc(path):
    with open(path, "r", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#") or ln.startswith("---"):
                continue
            return clip(re.sub(r"[*_`\[\]]", "", ln))
    return ""


def write(sub, title, blurb, desc_fn, recurse=False):
    d = os.path.join(B, sub)
    rows = []
    for dirpath, _, files in os.walk(d):
        if not recurse and dirpath != d:
            continue
        for f in sorted(files):
            if f == "INDEX.md" or not f.endswith((".py", ".md")):
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, d)
            rows.append((rel, desc_fn(full)))

    with open(os.path.join(d, "INDEX.md"), "w") as fh:
        fh.write(f"# {title}\n\n{blurb}\n\n")
        fh.write("| file | what it does |\n|---|---|\n")
        for rel, desc in sorted(rows):
            fh.write(f"| `{rel}` | {desc or '—'} |\n")
        fh.write(f"\n**{len(rows)} files.**\n")
    print(f"{sub:18s} {len(rows):3d} entries")


write("03_research", "Research reports",
      "26 sweeps of academic papers, GitHub repos, and vendor documentation. "
      "These are inputs -- the conclusions that survived testing are in "
      "[../02_findings/](../02_findings/), and most of what is proposed here "
      "did not survive.", md_desc)

write("04_live_system", "Live system",
      "The 53 modules behind the dashboard on port 8094. `gap_dashboard.py` is "
      "the entry point; `signal_weights.py` is the single source of truth for "
      "how much each signal counts.", py_desc)

write("05_studies", "Studies and backtests",
      "The 113 harnesses that produced every number in the findings. All are "
      "standalone and read from `data/`. Anything here that reports a positive "
      "result should be re-checked against "
      "[../02_findings/METHODOLOGY_TRAPS.md](../02_findings/METHODOLOGY_TRAPS.md).",
      py_desc, recurse=True)
