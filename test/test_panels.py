"""Panel behaviour, asserted on the dicts rather than on markup.

This is the whole point of Phase 4's contract. Before it, the only assertion
available against a panel was "does the page contain this substring", which is why
six contradictory recommendations coexisted on one page without a single test failing.
"""
import pytest

from panels import EMPTY, OK, STALE, UNAVAILABLE, panel, safe, describe


# --------------------------------------------------------------- the contract ---

def test_every_panel_declares_a_known_state():
    p = panel("k", "T")
    assert p["state"] == OK
    assert set(["key", "title", "state", "body", "note", "severity", "fix",
                "age_min", "source"]).issubset(p)


def test_unknown_state_is_rejected_loudly():
    with pytest.raises(AssertionError):
        panel("k", "T", state="probably-fine")


def test_a_raising_panel_becomes_unavailable_not_blank():
    """One bad panel must never blank the page, and must never vanish quietly.

    A fresh clone used to return HTTP 000 with zero bytes because scorecard.panel()
    hit a missing directory and render() had no guard.
    """
    @safe
    @describe("boom", "Exploding Panel")
    def boom():
        raise ValueError("the database is on fire")

    p = boom()
    assert p["state"] == UNAVAILABLE
    assert p["key"] == "boom"
    assert p["title"] == "Exploding Panel"
    assert "the database is on fire" in p["note"]
    assert "ValueError" in p["note"]
    assert p["body"]["traceback"]


def test_empty_and_unavailable_are_distinguishable():
    """They led to opposite actions and used to render identically as ""."""
    from panels import empty, unavailable
    e = empty("k", "T", "Nothing to report.")
    u = unavailable("k", "T", "Could not read the book.")
    assert e["state"] != u["state"]
    assert e["severity"] is None
    assert u["severity"] == "stop"


# ------------------------------------------------------------------- today ---

def test_answer_stands_down_when_a_gate_blocks(state, monkeypatch):
    """The deterministic gates outrank the model. Always."""
    import panels.today as today
    monkeypatch.setattr(today, "_gate_blockers",
                        lambda: [{"gate": "entry", "reason": "GEX z below the gate"}])
    state.put("master_call.json", "master_call_enter")

    p = today.answer()
    assert p["body"]["verb"] == "STAND DOWN"
    assert p["body"]["blockers"], "a blocked answer must name the gate"
    assert "GEX z below the gate" in p["body"]["blockers"][0]["reason"]


def test_answer_surfaces_the_proposal_only_when_nothing_blocks(state, monkeypatch):
    import panels.today as today
    monkeypatch.setattr(today, "_gate_blockers", lambda: [])
    monkeypatch.setattr(today, "_trust_sentence", lambda: "trust line")
    state.put("master_call.json", "master_call_enter")

    p = today.answer()
    assert "IRON CONDOR" in p["body"]["verb"]
    rows = {r["k"]: r["v"] for r in p["body"]["rows"]}
    assert rows["strikes"] == "596/598P · 606/608C"
    assert rows["stop"] == "$1.31"
    assert any(r.get("severity") == "stop" for r in p["body"]["rows"]), \
        "the stop must be marked, it is the only number that limits the loss"


def test_answer_always_carries_a_trust_sentence(state, monkeypatch):
    """The measured-vs-modelled split is the number the redesign exists to surface."""
    import panels.today as today
    monkeypatch.setattr(today, "_gate_blockers", lambda: [])
    state.put("master_call.json", "master_call_standdown")
    assert today.answer()["body"]["trust"]


def test_answer_reports_a_failed_engine_as_unavailable(state, monkeypatch):
    import panels.today as today
    monkeypatch.setattr(today, "_gate_blockers", lambda: [])
    state.put("master_call.json", data={"ok": False, "error": "no board"})
    p = today.answer()
    assert p["state"] == UNAVAILABLE
    assert "no board" in p["note"]


def test_regime_is_empty_not_broken_without_a_snapshot(state):
    import panels.today as today
    p = today.regime()
    assert p["state"] == EMPTY
    assert "idt refresh" in p["fix"], "an empty state must name the command that fills it"


def test_regime_goes_stale_and_says_how_old(state):
    import panels.today as today
    state.put("gex_snapshot.json", "gex_high_gamma")
    state.age("gex_snapshot.json", 200)
    p = today.regime()
    assert p["state"] == STALE
    assert p["age_min"] > 90
    assert p["severity"] == "watch"


def test_regime_reports_range_never_a_side(state):
    """Dealer gamma forecasts how big, never which way. Both regimes, both directions."""
    import panels.today as today
    for fixture in ("gex_high_gamma", "gex_low_gamma"):
        state.put("gex_snapshot.json", fixture)
        p = today.regime()
        text = repr(p).lower()
        for banned in ("buy calls", "buy puts", "buy a naked", "favor calls", "favor puts"):
            assert banned not in text, f"{fixture} panel contains a directional order: {banned}"


# ---------------------------------------------------------------- markets ---

def test_periscope_failure_is_unavailable_with_the_reason(state):
    import panels.markets as markets
    state.put("periscope_SPX.json", "periscope_failed")
    p = markets.periscope_spx()
    assert p["state"] == UNAVAILABLE
    assert "no option chain" in p["note"]


def test_periscope_renders_levels_when_healthy(state):
    import panels.markets as markets
    state.put("periscope_SPX.json", "periscope_ok")
    p = markets.periscope_spx()
    assert p["state"] == OK
    rows = {r["k"]: r["v"] for r in p["body"]["rows"]}
    assert rows["gamma flip"] == "5960.0"
    assert rows["call wall"] == "6050.0"


# ------------------------------------------------- the one-decision invariant ---

ACTION_VERBS = ("buy calls", "buy puts", "buy a naked", "go naked", "press size",
                "favor calls", "favor puts", "sell an iron condor", "buy premium")


def test_only_the_answer_panel_may_issue_an_action(state):
    """The invariant the whole redesign rests on.

    master_panel()'s own docstring recorded the original problem: the page "used to
    shout several conflicting headlines at once". A master call was added on top and
    the conflicting sources underneath were never removed. This test is what stops
    that happening again.
    """
    from panels import views
    state.put("gex_snapshot.json", "gex_low_gamma")
    state.put("periscope_SPX.json", "periscope_ok")

    offenders = []
    for v in views.VIEWS:
        for p in views.build(v["slug"]):
            if p["key"] == "answer":
                continue
            for where, blob, refuted in _fragments(p):
                if refuted:
                    continue        # naming a claim in order to refute it is the point
                for verb in ACTION_VERBS:
                    if verb in blob:
                        offenders.append(f"{v['slug']}/{p['key']}/{where}: {verb}")
    assert not offenders, "panels other than `answer` are issuing orders: " + "; ".join(offenders)


def _fragments(p):
    """Every operator-visible fragment of a panel, with whether it is marked refuted.

    A row tagged `null` or `stop` is a retired claim being listed as retired, which is
    exactly what the Evidence view exists to do. The same distinction the verify gate
    makes: catch the imperative, allow the mention.
    """
    out = [("note", str(p.get("note") or "").lower(), False),
           ("title", str(p.get("title") or "").lower(), False),
           ("fix", str(p.get("fix") or "").lower(), False)]
    body = p.get("body") or {}
    out.append(("text", str(body.get("text") or "").lower(), False))
    for r in body.get("rows") or []:
        refuted = r.get("tier") in ("null", "modelled") or r.get("severity") == "stop"
        out.append((f"row:{r.get('k')}", f"{r.get('k')} {r.get('v')}".lower(), refuted))
    for m in body.get("meters") or []:
        out.append((f"meter:{m.get('label')}",
                    f"{m.get('label')} {m.get('value')} {m.get('why')}".lower(), False))
    return out


def test_no_view_ever_raises(state):
    """Every view must build even with an entirely empty state directory."""
    from panels import views
    for v in views.VIEWS:
        panels = views.build(v["slug"])
        assert panels, f"{v['slug']} built no panels"
        for p in panels:
            assert p["state"] in (OK, EMPTY, STALE, UNAVAILABLE)


def test_status_says_when_no_cycle_has_run(state):
    from panels import views
    s = views.status()
    assert "no cycle has run yet" in s["detail"]
    assert s["severity"] in ("watch", "stop")
