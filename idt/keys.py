"""API keys, resolved in one place.

Replaces four copy-pasted `_key()` loaders (`ai_desk.py`, `analyst.py`,
`uw_client.py`, `fetch_minutes.py`), each of which searched the ORIGINAL AUTHOR's
home directory first — so on any other machine all four silently fell through to
the environment, and the failure looked like 'no credits' rather than 'no key'.

Search order, first hit wins:
  1. the process environment
  2. <repo>/.env
  3. $IDT_ENV_FILE, if set
"""
import os

from . import paths

_ALIASES = {
    "ANTHROPIC_API_KEY": ("ANTHROPIC_API_KEY",),
    "UNUSUALWHALES_API_KEY": ("UNUSUALWHALES_API_KEY", "UW_API_KEY"),
    "POLYGON_API_KEY": ("POLYGON_API_KEY",),
}


def _env_files():
    out = [os.path.join(paths.REPO_ROOT, ".env")]
    extra = os.environ.get("IDT_ENV_FILE")
    if extra:
        out.append(extra)
    return out


def _from_file(path, names):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() in names:
                    return v.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def get(name):
    """The key, or None. Never raises — callers decide whether absence is fatal."""
    names = _ALIASES.get(name, (name,))
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    for p in _env_files():
        v = _from_file(p, names)
        if v:
            return v
    return None


def status():
    """Which keys are present, for `idt bootstrap` and the dashboard's health
    banner. Returns names and booleans only — never the values."""
    return {n: bool(get(n)) for n in _ALIASES}
