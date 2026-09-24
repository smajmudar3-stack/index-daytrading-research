"""The swing ranker: the three-input composite and cut, momentum from a name's own year,
the weekly issue gate, and a ledger that fills at the next open and closes after the hold."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_live_system"))
import swing_ranker as rk  # noqa: E402


def _frame(path, end="2026-09-18"):
    idx = pd.bdate_range(end=end, periods=len(path))
    return pd.DataFrame({"open": path, "close": path, "volume": [1e6] * len(path)}, index=idx)


def test_select_ranks_on_the_mean_rank_of_three_inputs_and_refuses_with_reasons():
    rows = [{"ticker": f"T{i}", "sue": i / 100, "resid_mom": i / 10, "mom12_1": i / 5, "close": 50.0, "adv20": 50e6}
            for i in range(10)]
    rows.append({"ticker": "SHORT", "sue": 0.9, "resid_mom": None, "mom12_1": None, "close": 50.0, "adv20": 50e6})
    rows.append({"ticker": "THIN", "sue": 0.9, "resid_mom": 9, "mom12_1": 9, "close": 50.0, "adv20": 1e6})
    picks, refused = rk.select(rows, n_picks=3)
    assert [p["ticker"] for p in picks] == ["T9", "T8", "T7"]
    assert picks[0]["rank"] == 1 and picks[0]["cohort"] == 10 and picks[0]["score"] == 1.0
    why = {r["ticker"]: r["why"] for r in refused}
    assert "year" in why["SHORT"] and "volume" in why["THIN"] and "ranked 4 of 10" in why["T6"]


def test_momentum_strips_the_market_and_skips_the_last_month():
    n = 300
    spy = _frame(list(np.linspace(100, 130, n)))
    # a name that tracks SPY exactly: residual momentum ~0; its own 12-1 is positive
    same = _frame(list(np.linspace(50, 65, n)))
    m = rk.momentum(same, spy)
    assert m["mom12_1"] > 0 and abs(m["resid_mom"]) < 0.5 and m["beta"] == pytest.approx(1.0, abs=0.05)
    assert rk.momentum(_frame([50.0] * 100), spy) is None


def test_run_issues_weekly_fills_next_open_and_does_not_reissue(tmp_path, monkeypatch):
    monkeypatch.setattr(rk, "DB", str(tmp_path / "rk.db"))
    monkeypatch.setattr(rk, "_stamp", lambda: "2026-09-18 16:00")
    monkeypatch.setattr(rk, "_notify", lambda *a, **k: True)
    monkeypatch.setattr(rk.snapshots, "write", lambda name, out: None)
    rows = [{"ticker": "AAA", "sue": 0.05, "close": 50.0, "adv20": 50e6, "report_date": "2026-09-10"},
            {"ticker": "BBB", "sue": -0.05, "close": 50.0, "adv20": 50e6, "report_date": "2026-09-10"}]
    monkeypatch.setattr(rk, "reporters", lambda: (rows, None))
    n = 300
    px = {"AAA": _frame(list(np.linspace(40, 60, n))), "BBB": _frame(list(np.linspace(60, 40, n))),
          "SPY": _frame(list(np.linspace(100, 110, n)))}
    monkeypatch.setattr(rk, "_prices", lambda names, period="14mo": px)
    out = rk.run(now=pd.Timestamp("2026-09-18 16:00", tz=rk.ET))
    assert out["issued"] and out["picks"][0]["ticker"] == "AAA" and out["ledger_result"]["added"] == 2
    later = {k: pd.concat([v, _frame([v["close"].iloc[-1] * 1.1] * 3, end="2026-09-23")]) for k, v in px.items()}
    r = rk.book([], later, now=pd.Timestamp("2026-09-23 16:00", tz=rk.ET))
    assert r["filled"] == 2
    row = [x for x in rk.ledger()["open"] if x["ticker"] == "AAA"][0]
    assert row["entry_date"] == "2026-09-21" and row["pnl_pct"] == 0.0     # entered at the lifted open, flat since
    out2 = rk.run(now=pd.Timestamp("2026-09-19 16:00", tz=rk.ET))
    assert out2["issued"] is False and "next is due" in out2["note"]
    rk.book([], later, now=pd.Timestamp("2026-11-30 16:00", tz=rk.ET))
    assert all(x["status"] == "closed" for x in rk.ledger()["closed"]) and rk.ledger()["summary"]["n"] == 2


def test_snapshot_schema_is_registered():
    from idt import snapshots
    name, spec = snapshots.schema_for(rk.OUT)
    assert name == "swing_ranker" and "picks" in spec["required_when_ok"]


def test_nothing_places_an_order():
    src = open(rk.__file__, encoding="utf-8").read()
    assert "place_order" not in src and "submit_order" not in src
