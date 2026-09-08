"""Where things live. One resolver, two roots, no hardcoded home directories.

There are genuinely two data locations and conflating them was part of the mess:

  STATE_ROOT  small, live, rewritten every cycle — the ~26 snapshot JSONs and the
              SQLite books the dashboard reads. Ships empty; created on demand.
              Default: <repo>/04_live_system/data

  DATA_ROOT   the 16 GB of market data that is deliberately NOT in git (see
              06_data_guide/DATA.md). Nothing here is created for you; if it is
              absent, callers must say so rather than fabricating a number.
              Default: <repo>/data

Override either with an environment variable. `05_studies/` previously hardcoded
`/Users/sahilmajmudar/index-daytrading/data/...` in 26 files, so a clone ran
nothing; point IDT_DATA_ROOT at an existing copy and those scripts work again.
"""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LIVE_DIR = os.path.join(REPO_ROOT, "04_live_system")
STUDIES_DIR = os.path.join(REPO_ROOT, "05_studies")
SCRIPTS_DIR = os.path.join(STUDIES_DIR, "scripts")

STATE_ROOT = os.environ.get("IDT_STATE_ROOT") or os.path.join(LIVE_DIR, "data")
DATA_ROOT = os.environ.get("IDT_DATA_ROOT") or os.path.join(REPO_ROOT, "data")


def state(*parts):
    """A path under STATE_ROOT, with the directory created. Live snapshots and
    SQLite books are ours to create — a missing dir here is not a data problem,
    it is a first-run problem, and it used to return HTTP 000."""
    p = os.path.join(STATE_ROOT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def data(*parts):
    """A path under DATA_ROOT. Deliberately does NOT create anything: market data
    cannot be conjured, and a silently-created empty directory reads downstream as
    'no rows' rather than 'not installed'."""
    return os.path.join(DATA_ROOT, *parts)


def have_data(*parts):
    """True if that market-data path actually exists. Use this to print an honest
    'not installed' instead of raising three frames deeper in pandas."""
    return os.path.exists(data(*parts))


def require_data(*parts):
    """Path to a market-data file, or a clear error naming the fix."""
    p = data(*parts)
    if not os.path.exists(p):
        rel = os.path.join(*parts) if parts else ""
        raise FileNotFoundError(
            f"market data not found: {p}\n"
            f"  This repo ships without its 16 GB of data (see 06_data_guide/DATA.md).\n"
            f"  Either run `idt bootstrap` to fetch what is fetchable, or point\n"
            f"  IDT_DATA_ROOT at an existing copy that contains {rel!r}.")
    return p
