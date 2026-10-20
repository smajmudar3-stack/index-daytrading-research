"""The information architecture: five views, one question each, plays first.

The page used to open on the index desk's 0DTE decision, which is STAND DOWN on four
sessions in five by design, while the things there actually were to act on — the week's
stock cohorts, the stress book, the desk's calls — sat two cards down on another view.
"No suggestions still" (2026-10-02) was the operator reading the wrong page first, and the
page's fault for making it the first page.

The order now is the order the operator needs it in: what to be in this week (Plays), what
every paper book has made against SPY (Books), what the index is doing today and what is
dated ahead (Tape), what has been measured and what grows next (Research), and what is
switched off or stale (System).

Two rules survive from the first redesign. If two panels answer the same question
differently, one of them is deleted, not restyled. And only two panels on the whole site
may state a trade: the Plays desk (a play names its legs) and Today's decision; everything
else is context and says so, and a test walks every view to keep it that way.
"""
import os
import time

from idt import paths

from . import direction, evidence, markets, plays, risk, signals, structures, today, weekly

VIEWS = [
    {
        "slug": "plays",
        "label": "Plays",
        "question": "What should I be in this week, why, and what is it expected to make?",
        # The plays first, with their reasoning and timeline; then what was considered and
        # why the rest was refused; then promised against delivered, with the priors table
        # every promise comes from.
        "panels": [plays.desk, plays.considered, plays.scorecard],
    },
    {
        "slug": "books",
        "label": "Books",
        "question": "Every paper book this desk runs, and what each has made against SPY.",
        # The two stock cohorts lead (they are what there is to act on most weeks), then the
        # quarterly book, the stress book, the emails as trades, the index overlay, the
        # weekly options cards and their ledger, the memecoin book, and the refusals.
        "panels": [weekly.books_overview, weekly.books, weekly.stock_picks, weekly.stress_book, weekly.desk_trades, weekly.overlay,
                   weekly.trades, weekly.book, weekly.memecoin_book, weekly.refused],
    },
    {
        "slug": "tape",
        "label": "Tape",
        "question": "What is the index doing today, what is dated ahead, and which gates are shut?",
        # The decision first, then the two dated things that outrank any thesis — the macro
        # calendar and the earnings window — then the gamma read and the levels under it.
        "panels": [today.answer, signals.patterns, direction.call,
                   signals.gamma_meter, direction.regime, direction.structure_note,
                   today.gates, today.regime, today.positions,
                   weekly.calendar, weekly.earnings_vol, weekly.macro, weekly.index,
                   structures.gamma_structures,
                   markets.periscope_spx, markets.periscope_ndx,
                   markets.gaps, markets.blackswan],
    },
    {
        "slug": "research",
        "label": "Research",
        "question": "What has been measured, what is being recorded, and which branch grows next?",
        # The tree first: every branch tested with its verdict and the waiting ones. Then
        # the evidence meters, the scorecard, the retired claims, the weights, and the
        # recorders' counters.
        "panels": [plays.tree, evidence.meters, evidence.scorecard, evidence.verdicts, evidence.weights,
                   weekly.data_lake, weekly.freshness],
    },
    {
        "slug": "system",
        "label": "System",
        "question": "What am I allowed to risk, what is switched off, and what is stale?",
        "panels": [risk.events, risk.account, risk.graduation, risk.services],
    },
]

DEFAULT_VIEW = "plays"

# The first redesign's slugs, kept as redirects so a bookmark or a runbook line still lands.
LEGACY = {"today": "tape", "markets": "books", "evidence": "research", "risk": "system"}


def view_by_slug(slug):
    slug = LEGACY.get(slug, slug)
    for v in VIEWS:
        if v["slug"] == slug:
            return v
    return VIEWS[0]


def build(slug):
    """Every panel for a view, already reduced to dicts. Never raises."""
    v = view_by_slug(slug)
    return [fn() for fn in v["panels"]]


# ------------------------------------------------------------------- status ---

# Files the operator's decisions depend on, and how old each is allowed to get.
# The limits are the ones audit_dash.py already enforces, so the banner and the
# audit cannot disagree about what "fresh" means.
FRESHNESS = [
    ("plays_snapshot.json", 1500, "plays"),
    ("swing_stock_snapshot.json", 1500, "stock book"),
    ("periscope_SPX.json", 20, "periscope"),
    ("gap_snapshot.json", 30, "gap scan"),
    ("gex_snapshot.json", 90, "gamma regime"),
]


def _age_min(name):
    p = os.path.join(paths.STATE_ROOT, name)
    if not os.path.exists(p):
        return None
    return (time.time() - os.path.getmtime(p)) / 60


def status():
    """One status line. It replaced four banners that could disagree with each other.

    It answers, in order: is the data fresh, did the last cycle actually work. Clicking
    Refresh used to return an identical 302 whether every engine ran or every engine threw.
    """
    chips = []
    worst = None
    for fname, limit, label in FRESHNESS:
        age = _age_min(fname)
        if age is None:
            chips.append({"label": f"{label}: missing", "severity": "stop"})
            worst = "stop"
        elif age > limit:
            chips.append({"label": f"{label}: {age / 60:.0f}h" if age > 120 else f"{label}: {age:.0f}m", "severity": "watch"})
            worst = worst or "watch"
        else:
            chips.append({"label": f"{label}: {age / 60:.0f}h" if age > 120 else f"{label}: {age:.0f}m", "severity": None})

    detail = ""
    cycle = os.path.join(paths.STATE_ROOT, "cycle_report.json")
    if os.path.exists(cycle):
        try:
            import json
            with open(cycle, encoding="utf-8") as fh:
                rep = json.load(fh)
            steps = rep.get("steps") or {}
            failed = [k for k, v in steps.items() if isinstance(v, dict) and v.get("error")]
            if failed:
                detail = f"last cycle: {len(failed)} step(s) failed — {', '.join(failed[:3])}"
                worst = "stop"
            elif steps:
                detail = f"last cycle: {len(steps)} steps ok"
        except Exception as e:                      # noqa: BLE001
            detail = f"cycle report unreadable ({type(e).__name__})"
            worst = worst or "watch"
    else:
        detail = "no cycle has run yet"
        worst = worst or "watch"

    if worst == "stop":
        headline = "Data missing or last cycle failed"
    elif worst == "watch":
        headline = "Some data is older than it should be"
    else:
        headline = "Data fresh"

    return {"headline": headline, "chips": chips, "detail": detail, "severity": worst}
