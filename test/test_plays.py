"""The Plays desk, offline.

What these pin: a promise is never made without a prior; the prior is clipped so a
tail-driven cell cannot lead; shares lead when every option cell loses; the expiry is kept
before a print when it can be; the timeline is sorted and ends at the horizon; the panels
render through the real templates in every state; and the ledger scores a closed play
against what it promised.
"""
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 19, 10, 0, tzinfo=ET)        # a Monday


def _prior(mean, median=0.0, hit=0.5, n=200, splits=(0.1, 0.1, 0.1)):
    return {"mean": mean, "median": median, "hit": hit, "payoff": 1.2, "n": n, "p25": -0.3, "p75": 0.4,
            "splits": dict(zip("ABC", splits, strict=True)), "raw_mean": mean, "top5_share": 0.4, "t": 2.0, "cost_pct": 20.0}


def test_priors_are_empty_when_the_backtest_has_not_run(monkeypatch, tmp_path):
    import plays
    monkeypatch.setattr(plays, "PRIORS_FILE", str(tmp_path / "missing.parquet"))
    assert plays.priors() == {}
    assert plays.best_structure("surprise", {}) == (None, None)


def test_a_cell_paid_by_the_tail_cannot_lead():
    """The stress long call printed +100% raw with 99% of it in the top 5% of trades and a
    negative median; clipped it is small and its median is below the floor, so it may not
    lead. Shares lead instead."""
    import plays
    pri = {("stress_vix25", "long_call_60"): _prior(0.18, median=-0.30, hit=0.44),
           ("stress_vix25", "long_call_80"): _prior(0.17, median=-0.03, hit=0.49, splits=(1.3, 0.7, -0.05)),
           ("stress_vix25", "shares"): _prior(0.055, median=0.02, hit=0.60)}
    # long_call_60 clears the median floor but is beaten by nothing... check the gate itself
    assert plays._qualifies(pri[("stress_vix25", "long_call_60")])          # median -0.30 is above the -0.35 floor
    assert not plays._qualifies(pri[("stress_vix25", "long_call_80")])      # a negative split
    struct, p = plays.best_structure("stress_vix25", pri)
    assert struct == "long_call_60"                                         # the best QUALIFYING cell leads
    pri[("stress_vix25", "long_call_60")]["median"] = -0.40                 # below the floor: shares lead
    assert plays.best_structure("stress_vix25", pri)[0] == "shares"


def test_shares_lead_when_every_option_cell_loses():
    import plays
    pri = {("surprise", "call_debit_70_40"): _prior(-0.14), ("surprise", "long_call_80"): _prior(-0.04),
           ("surprise", "shares"): _prior(0.074, median=0.03, hit=0.60)}
    assert plays.best_structure("surprise", pri) == ("shares", pri[("surprise", "shares")])


def test_nothing_leads_when_nothing_measured_positive():
    import plays
    pri = {("ranker", "shares"): _prior(-0.01), ("ranker", "long_call_80"): _prior(-0.12)}
    assert plays.best_structure("ranker", pri) == (None, None)


def test_confidence_is_earned_from_the_prior_never_typed():
    import plays
    assert plays.confidence(_prior(0.07, hit=0.6), 1, []) == "measured, all splits"
    assert plays.confidence(_prior(0.07, hit=0.6), 2, []).endswith("two books agree")
    assert plays.confidence(_prior(0.07, hit=0.40), 1, []).startswith("measured, all splits; paid by the tail")
    assert plays.confidence(_prior(0.07, splits=(0.2, -0.1, 0.1)), 1, []).startswith("weak")
    assert plays.confidence(_prior(-0.02), 1, []) == "negative prior"
    assert plays.confidence(_prior(0.07), 1, ["the desk notes argue against"]) == "vetoed"
    assert plays.confidence(None, 1, []) == "unmeasured"


def test_expiry_is_kept_before_a_print_when_it_still_covers_the_horizon():
    import plays
    exps = ["2026-10-30", "2026-11-20", "2026-12-18", "2027-01-15"]
    e, dte, note = plays._pick_expiry(exps, 63, "2026-12-25", NOW)
    assert e == "2026-12-18" and "BEFORE" in note                        # the last expiry before the print still covers 60 of 63 days
    e, dte, note = plays._pick_expiry(exps, 63, "2026-12-01", NOW)
    assert e == "2026-12-18" and "falls inside the hold" in note         # the only pre-print expiry (32 days) is too short: cover the print and say so
    e, dte, note = plays._pick_expiry(exps, 63, None, NOW)
    assert e == "2026-12-18" and note is None
    e, dte, note = plays._pick_expiry(exps, 63, "2026-11-05", NOW)      # the only pre-print expiry is too short: cover it and say so
    assert e == "2026-12-18" and "falls inside the hold" in note
    assert plays._pick_expiry(["2026-10-21"], 63, None, NOW) == (None, None, None)


def test_timeline_is_sorted_and_ends_at_the_horizon():
    import plays
    bits = {"expiry": "2026-11-20"}
    t = plays._timeline(NOW, bits, 21, "2026-11-17", [{"date": "2026-11-05", "label": "FOMC"}], {"date": "2026-11-10"}, False)
    whens = [x["when"] for x in t]
    assert whens == sorted(whens)
    assert t[0]["when"] == "2026-10-20" and "enter" in t[0]["what"]
    assert any("FOMC" in x["what"] for x in t) and any("reports" in x["what"] for x in t)
    assert any(x["when"] == "2026-11-17" and x["what"].startswith("exit") for x in t)
    assert t[-1]["when"] == "2026-11-20" and t[-1]["what"] == "expiry"


def test_issue_without_candidates_writes_an_ok_snapshot_that_says_so(state, monkeypatch):
    import plays
    from idt import snapshots
    monkeypatch.setattr(plays, "DB", str(state.path / "plays.db"))
    monkeypatch.setattr(plays, "priors", lambda: {})
    out = plays.issue(now=NOW)
    assert out["ok"] and out["considered"] == [] and out["issued"] == []
    assert not out["priors_available"]
    p, st = snapshots.read(plays.OUT)
    assert st == "ok" and p["issue_window"]["due_today"] is True


def test_issue_records_a_play_once_and_the_ledger_scores_it(state, monkeypatch):
    """A shares play on a surprise name: issued once, marked, closed at the horizon with
    the delivered number next to the promised one."""
    import plays
    monkeypatch.setattr(plays, "DB", str(state.path / "plays.db"))
    monkeypatch.setattr(plays, "priors", lambda: {("surprise", "shares"): _prior(0.074, median=0.03, hit=0.60)})
    monkeypatch.setattr(plays, "candidates", lambda now=None: ([{"ticker": "ACME", "sources": ["surprise"], "signal_detail": {"surprise": {"sue": 0.02}}}], []))
    monkeypatch.setattr(plays, "context_for", lambda tk, now=None: {"macro": None, "macro_side": 0, "events": [], "earnings": None, "research": None, "uw": None})
    monkeypatch.setattr(plays, "_spot", lambda tk: 50.0)
    monkeypatch.setattr(plays, "_option_alt", lambda *a, **k: {"refused": "offline"})
    out = plays.issue(now=NOW)
    assert len(out["issued"]) == 1
    p = out["issued"][0]
    assert p["structure"] == "shares" and p["contracts"] == 10 and p["expected_usd"] == 37.0 and p["confidence"] == "measured, all splits"
    assert p["timeline"][0]["when"] == "2026-10-20"
    # the same candidate again: refused as already open, nothing duplicated
    out2 = plays.issue(now=NOW)
    assert out2["issued"] == [] and any(r["why"] == "already an open play" for r in out2["refused"])
    con = sqlite3.connect(str(state.path / "plays.db"))
    assert con.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 1
    con.close()
    # mark at a higher print: open with the P&L; mark past the horizon: closed and scored
    monkeypatch.setattr(plays, "_spot", lambda tk: 55.0)
    m = plays.mark(now=NOW)
    assert m == {"ok": True, "marked": 1, "closed": 0}
    rows = plays.open_plays()
    assert rows[0]["pnl_usd"] == 50.0 and rows[0]["pnl_pct"] == 10.0 and rows[0]["status"] == "open"
    m = plays.mark(now=datetime(2027, 2, 1, tzinfo=ET))
    assert m["closed"] == 1
    sc = plays.scorecard()
    assert sc["n_closed"] == 1 and sc["hit"] == 1.0 and sc["promised_vs_delivered"] == pytest.approx(10.0 - 7.4, abs=0.05)


def test_plays_panels_render_in_every_state(state, monkeypatch):
    """Absent snapshot -> unavailable; no candidates -> empty with the reason; an issued
    play -> ok through the real template with the legs, the expected profit and the timeline."""
    import importlib
    import sys
    import plays
    from panels import plays as pp
    import dashboard_app
    monkeypatch.setattr(plays, "DB", str(state.path / "plays.db"))
    importlib.reload(pp)
    tpl = dashboard_app.env.get_template("panel.html")

    d = pp.desk()
    assert d["state"] == "unavailable"
    assert "unavailable" in dashboard_app._render_panel(tpl, d)

    monkeypatch.setattr(plays, "priors", lambda: {("surprise", "shares"): _prior(0.074, median=0.03, hit=0.60)})
    monkeypatch.setattr(plays, "candidates", lambda now=None: ([], ["swing_stock_snapshot.json absent"]))
    plays.issue(now=NOW)
    d = pp.desk()
    assert d["state"] == "empty" and "no measured book holds a candidate" in d["note"]
    html = dashboard_app._render_panel(tpl, d)
    assert "is-empty" in html

    monkeypatch.setattr(plays, "candidates", lambda now=None: ([{"ticker": "ACME", "sources": ["surprise", "ranker"], "signal_detail": {}}], []))
    monkeypatch.setattr(plays, "context_for", lambda tk, now=None: {"macro": [{"theme": "US exceptionalism", "stance": "favour", "side": 1, "why": "capex"}], "macro_side": 1,
                                                                    "events": [{"date": "2026-11-05", "label": "FOMC", "days_away": 17, "importance": "high"}],
                                                                    "earnings": None, "research": None, "uw": None})
    monkeypatch.setattr(plays, "_spot", lambda tk: 50.0)
    monkeypatch.setattr(plays, "_option_alt", lambda *a, **k: {"structure": "long_call_80", "label": "Deep call", "legs_text": "Buy 45C", "net": 7.1, "expiry": "2027-01-15",
                                                                 "dte": 88, "max_risk": 710, "max_reward": None, "cost_pct": 8.0, "breakevens": [52.1], "iv_atm": 30.0,
                                                                 "prior": None, "verdict": "unmeasured on this signal"})
    out = plays.issue(now=NOW)
    assert out["issued"] and out["issued"][0]["confidence"].endswith("two books agree")
    d = pp.desk()
    assert d["state"] == "ok"
    html = dashboard_app._render_panel(tpl, d)
    for needle in ("ACME", "Buy shares at the next open", "expected ·", "Timeline", "US exceptionalism", "FOMC", "Buy 45C", "as options"):
        assert needle in html, needle
    c = pp.considered()
    assert c["state"] == "ok"
    assert "ACME" in dashboard_app._render_panel(tpl, c)
    s = pp.scorecard()
    assert s["state"] in ("ok", "empty")
    dashboard_app._render_panel(tpl, s)
    t = pp.tree()
    assert t["state"] == "ok" and t["body"]["departments"]
    html = dashboard_app._render_panel(tpl, t)
    assert "earnings surprise" in html.lower() and "waiting" in html
    for mod in ("panels.plays",):
        sys.modules.pop(mod, None)


def test_plays_is_the_default_view_and_old_slugs_still_land():
    from panels import views
    assert views.DEFAULT_VIEW == "plays"
    assert views.VIEWS[0]["slug"] == "plays"
    for old, new in views.LEGACY.items():
        assert views.view_by_slug(old)["slug"] == new


def test_snapshot_schema_covers_plays():
    from idt import snapshots
    assert "plays_snapshot.json" in snapshots.SCHEMAS["plays"]["files"]
    assert "considered" in snapshots.SCHEMAS["plays"]["required_when_ok"]


def test_strategy_tree_is_well_formed():
    """Every child names a node, every node has a status, a measured node carries a verdict,
    a waiting node carries a rule or a label the hunt can act on."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "docs", "strategy_tree.json"), encoding="utf-8") as fh:
        t = json.load(fh)
    nodes = t["nodes"]
    assert t["root"] in nodes
    for k, n in nodes.items():
        assert n.get("status") in t["legend"]["status"], k
        for c in n.get("children") or []:
            assert c in nodes, f"{k} -> {c} is not a node"
        if n["status"] == "measured":
            assert n.get("verdict") in t["legend"]["verdict"], k
        if n["status"] in ("proposed", "untested"):
            assert n.get("label"), k
