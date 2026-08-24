"""The deterministic gates. These are the tests that matter most in the repo.

A gate that returns "allow" when it cannot evaluate is not a gate. Seven of them did
exactly that, including `check_entry` itself, whose handler caught every gate exception
and let the trade through with a comment claiming a gate that throws must fail OPEN.

The rule these tests encode: absence of evidence blocks. Every one of them is written
so that if the fail-open behaviour ever comes back, the test goes red rather than a
trade going through.
"""
import json
import os

import pytest


@pytest.fixture
def gates(state):
    import importlib
    import risk_gates
    importlib.reload(risk_gates)
    return risk_gates


# ------------------------------------------------------- the event calendar ---
#
# `event_blackout` is listed in ENFORCED. `_events()` used to be:
#     try:    cfg = json.load(open(EVENTS))
#     except: return []
# so a missing, empty or stale data/events.json made the gate pass EVERY DAY while
# reporting as enforced. FOMC and CPI dates are hand-entered, which is exactly the
# kind of file that goes stale without anyone noticing.

def test_missing_calendar_blocks_rather_than_permits(gates):
    st = gates.event_calendar_status()
    assert st["state"] not in ("ok", "current"), \
        "an absent event calendar must not look like a clear day"
    assert st.get("reason"), "a blocking gate must say why"


def test_empty_calendar_blocks(gates, state):
    state.put("events.json", data={"blackout": [], "labels": {}})
    st = gates.event_calendar_status()
    assert st["state"] not in ("ok", "current"), \
        "an empty calendar is not the same as a day with no events"


def test_exhausted_calendar_blocks(gates, state):
    """A calendar whose newest entry is in the past has run out.

    Its mtime may be recent and its JSON may be valid. It still cannot be describing
    today, and that is the failure mode a mtime check alone would miss.
    """
    state.put("events.json", data={"blackout": ["2020-01-15"],
                                   "labels": {"2020-01-15": "CPI"}})
    st = gates.event_calendar_status()
    assert st["state"] not in ("ok", "current")


def test_current_calendar_permits(gates, state):
    from datetime import date, timedelta
    future = [(date.today() + timedelta(days=d)).isoformat() for d in (7, 21, 45)]
    state.put("events.json", data={"blackout": future,
                                   "labels": {f: "FOMC" for f in future}})
    st = gates.event_calendar_status()
    assert st["state"] in ("ok", "current"), f"a current calendar must permit: {st}"
    assert st.get("newest") == future[-1]


def test_calendar_status_exposes_age_for_the_panel(gates, state):
    from datetime import date, timedelta
    future = [(date.today() + timedelta(days=30)).isoformat()]
    state.put("events.json", data={"blackout": future, "labels": {}})
    st = gates.event_calendar_status()
    assert "age_days" in st, "the panel needs the file's age to warn before it goes stale"


def test_malformed_calendar_blocks(gates, state):
    (state.path / "events.json").write_text("{not json at all", encoding="utf-8")
    st = gates.event_calendar_status()
    assert st["state"] not in ("ok", "current")


# --------------------------------------------------------- the master switches ---

def test_dry_run_and_live_agent_are_both_off(gates):
    """Two switches, both must flip for a real order. Neither may drift on quietly."""
    assert gates.DRY_RUN is True
    assert gates.LIVE_AGENT is False


def test_no_order_placement_code_exists():
    """The repo claims nothing places live orders. Check, do not take it on faith."""
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    live = os.path.join(root, "04_live_system")
    # Broker SDKs and order verbs that would indicate a real execution path.
    danger = re.compile(r"\b(place_order|submit_order|robin_stocks|tastytrade|"
                        r"ib_insync|alpaca|create_order)\b")
    hits = []
    for f in sorted(os.listdir(live)):
        if not f.endswith(".py"):
            continue
        with open(os.path.join(live, f), encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if danger.search(line) and not line.lstrip().startswith("#"):
                    hits.append(f"{f}:{i}")
    assert not hits, f"order-placement code appeared in the live system: {hits}"


# ------------------------------------------------------------ gate stack shape ---

def test_every_enforced_gate_is_named(gates):
    assert gates.ENFORCED, "an empty ENFORCED set means nothing is gated"
    for g in ("event_blackout", "time_window", "regime_gate", "daily_caps",
              "daily_loss_stop", "conviction"):
        assert g in gates.ENFORCED, f"{g} must be enforced, not shadowed"


def test_shadow_gates_are_declared_not_implied(gates):
    """A gate in SHADOW is logged, not enforced. That must be a deliberate list."""
    assert isinstance(gates.SHADOW, set)
    assert not (gates.SHADOW & gates.ENFORCED), \
        "a gate cannot be both enforced and shadow-only"


def test_rules_and_risk_gates_agree_about_the_calendar(state):
    """Two modules disagreeing about whether trading is permitted is the bug class
    this whole effort is about. rules.gate_state() used to report the gate OPEN with
    no calendar while risk_gates.check_entry() blocked."""
    import importlib
    import risk_gates
    import rules
    importlib.reload(risk_gates)
    importlib.reload(rules)

    cal = risk_gates.event_calendar_status()
    g = rules.gate_state()
    if cal["state"] not in ("ok", "current"):
        assert not g["open"], \
            "risk_gates blocks on the calendar but rules.gate_state() reports the gate open"
