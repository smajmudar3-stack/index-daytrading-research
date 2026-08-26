"""The information architecture: four views, one question each.

The old page had five CSS-only tabs plus five panels stacked above them, 26 render
slots across about 22 panels, and no view had a stated purpose. Between them the
panels emitted at least seventeen different action verbs with no arbitration.

The rule that produced this structure: if two panels answer the same question
differently, one of them is deleted, not restyled. And exactly one panel on the whole
site is allowed to contain an action verb.
"""
import os
import time

from idt import paths

from . import signals, structures, evidence, markets, risk, today

VIEWS = [
    {
        "slug": "today",
        "label": "Today",
        "question": "Is there anything to do right now, and how much should I trust it?",
        "panels": [signals.patterns, today.answer, signals.gamma_meter,
                   today.gates, today.regime, today.positions],
    },
    {
        "slug": "evidence",
        "label": "Evidence",
        "question": "How much of what this system tells me is measured, and how much is a guess?",
        # Order is layout: the grid places panels two-up, so the two half-width
        # panels (meters, scorecard) sit side by side and the two full-width lists
        # (verdicts, weights) follow.
        "panels": [evidence.meters, evidence.scorecard, evidence.verdicts, evidence.weights],
    },
    {
        "slug": "markets",
        "label": "Markets",
        "question": "What is the tape doing? Context only — nothing here is a recommendation.",
        "panels": [structures.gamma_structures,
                   markets.periscope_spx, markets.periscope_ndx, markets.swing,
                   markets.gaps, markets.blackswan],
    },
    {
        "slug": "risk",
        "label": "Risk & account",
        "question": "What am I allowed to risk, what is switched off, and what is stale?",
        "panels": [risk.events, risk.account, risk.graduation, risk.services],
    },
]

DEFAULT_VIEW = "today"


def view_by_slug(slug):
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
    ("periscope_SPX.json", 20, "periscope"),
    ("gap_snapshot.json", 30, "gap scan"),
    ("gex_snapshot.json", 90, "gamma regime"),
    ("swing_snapshot.json", 1500, "swing"),
]


def _age_min(name):
    p = os.path.join(paths.STATE_ROOT, name)
    if not os.path.exists(p):
        return None
    return (time.time() - os.path.getmtime(p)) / 60


def status():
    """One status line. It replaced four banners that could disagree with each other.

    It answers, in order: is the market awake, is the data fresh, did the last cycle
    actually work. That last one is new. Clicking Refresh used to return an identical
    302 whether every engine ran or every engine threw.
    """
    chips = []
    worst = None
    for fname, limit, label in FRESHNESS:
        age = _age_min(fname)
        if age is None:
            chips.append({"label": f"{label}: missing", "severity": "stop"})
            worst = "stop"
        elif age > limit:
            chips.append({"label": f"{label}: {age:.0f}m", "severity": "watch"})
            worst = worst or "watch"
        else:
            chips.append({"label": f"{label}: {age:.0f}m", "severity": None})

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

    # The masthead owns the market-open state; repeating it here in a different
    # colour recreates the two-sources-disagree shape this strip replaced.
    if worst == "stop":
        headline = "Data missing or last cycle failed"
    elif worst == "watch":
        headline = "Some data is older than it should be"
    else:
        headline = "Data fresh"

    return {"headline": headline, "chips": chips, "detail": detail, "severity": worst}
