"""The stress book: the reversal composite and cut, the regime gate, and a ledger that fills
at the NEXT open, freezes the entry, marks against SPY and closes after the hold."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_live_system"))
import stress_reversal as sr  # noqa: E402


def _px(open_, close, n=80, end="2026-09-21", volume=1e6):
    idx = pd.bdate_range(end=end, periods=n)
    return pd.DataFrame({"open": [open_] * n, "close": [close] * n, "volume": [volume] * n}, index=idx)


def test_select_takes_the_biggest_losers_by_mean_rank_and_refuses_the_rest_with_a_reason():
    rows = [{"ticker": f"T{i}", "close": 50.0, "adv20": 50e6, "ret1m": -i / 100, "ret1w": -i / 200, "bb_pos": -i / 10}
            for i in range(10)]
    rows.append({"ticker": "CHEAP", "close": 4.0, "adv20": 50e6, "ret1m": -0.9, "ret1w": -0.5, "bb_pos": -3})
    rows.append({"ticker": "THIN", "close": 50.0, "adv20": 1e6, "ret1m": -0.9, "ret1w": -0.5, "bb_pos": -3})
    rows.append({"ticker": "SHORT", "close": 50.0, "adv20": 50e6, "ret1m": None})
    picks, refused = sr.select(rows, n_picks=3)
    assert [p["ticker"] for p in picks] == ["T9", "T8", "T7"]          # the three biggest losers
    assert picks[0]["rank"] == 1 and picks[0]["cohort"] == 10 and 0 < picks[0]["score"] <= 1
    why = {r["ticker"]: r["why"] for r in refused}
    assert "price" in why["CHEAP"] and "volume" in why["THIN"] and "short" in why["SHORT"]
    assert "ranked 4 of 10" in why["T6"]
    assert len(picks) + len(refused) == len(rows)


def test_composite_reads_one_month_one_week_and_bollinger():
    idx = pd.bdate_range(end="2026-09-21", periods=40)
    close = pd.Series([100.0] * 30 + [90.0] * 10, index=idx)
    c = sr.composite(pd.DataFrame({"close": close}))
    assert c["ret1m"] == pytest.approx(-0.10) and c["ret1w"] == 0.0 and c["bb_pos"] < 0
    assert sr.composite(pd.DataFrame({"close": close.tail(10)})) is None


def test_run_is_off_below_the_vix_threshold_and_issues_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "DB", str(tmp_path / "sr.db"))
    monkeypatch.setattr(sr, "vix_now", lambda: (17.2, "2026-09-23"))
    monkeypatch.setattr(sr, "universe", lambda: (_ for _ in ()).throw(AssertionError("must not price the universe when off")))
    written = {}
    monkeypatch.setattr(sr.snapshots, "write", lambda name, out: written.update({name: out}))
    monkeypatch.setattr(sr, "_prices", lambda names: {})
    out = sr.run(now=pd.Timestamp("2026-09-23 16:00", tz=sr.ET))
    assert out["ok"] and out["regime_on"] is False and out["picks"] == [] and "off" in out["note"]
    assert written[sr.OUT]["vix"] == 17.2


def test_run_issues_a_cohort_when_on_and_fills_it_at_the_next_open(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "DB", str(tmp_path / "sr.db"))
    monkeypatch.setattr(sr, "_stamp", lambda: "2026-09-18 16:00")
    monkeypatch.setattr(sr, "vix_now", lambda: (31.0, "2026-09-18"))
    monkeypatch.setattr(sr, "universe", lambda: (["AAA", "BBB", "CCC"], None))
    idx = pd.bdate_range(end="2026-09-18", periods=60)
    def frame(path):
        return pd.DataFrame({"open": path, "close": path, "volume": [1e6] * len(path)}, index=idx)
    px = {"AAA": frame([100.0] * 55 + [70.0] * 5),        # the loser
          "BBB": frame([100.0] * 60),
          "CCC": frame([100.0] * 55 + [120.0] * 5),
          "SPY": frame([500.0] * 60)}
    monkeypatch.setattr(sr, "_prices", lambda names: px)
    monkeypatch.setattr(sr.snapshots, "write", lambda name, out: None)
    out = sr.run(now=pd.Timestamp("2026-09-18 16:00", tz=sr.ET))
    assert out["regime_on"] and out["issued"] and out["picks"][0]["ticker"] == "AAA"
    assert out["ledger_result"]["added"] == len(out["picks"])
    # the next session's open fills it; the entry is frozen; the hold closes it
    later = {k: pd.concat([v, _px(80.0, 88.0, n=3, end="2026-09-23")]) for k, v in px.items()}
    later["SPY"] = pd.concat([px["SPY"], _px(500.0, 505.0, n=3, end="2026-09-23")])
    r = sr.book([], later, now=pd.Timestamp("2026-09-23 16:00", tz=sr.ET))
    assert r["filled"] >= 1
    row = [x for x in sr.ledger()["open"] if x["ticker"] == "AAA"][0]
    assert row["entry_date"] == "2026-09-21" and row["entry"] == 80.0
    assert row["pnl_pct"] == 10.0 and row["rel_pct"] == pytest.approx(9.0)
    # a second run the same day does not re-issue the cohort
    out2 = sr.run(now=pd.Timestamp("2026-09-18 17:00", tz=sr.ET))
    assert out2["issued"] is False and "next after" in out2["note"]
    sr.book([], later, now=pd.Timestamp("2026-11-01 16:00", tz=sr.ET))
    assert all(x["status"] == "closed" for x in sr.ledger()["closed"])


def test_snapshot_schema_is_registered():
    from idt import snapshots
    name, spec = snapshots.schema_for(sr.OUT)
    assert name == "stress_reversal" and "regime_on" in spec["required_when_ok"]


def test_nothing_places_an_order():
    src = open(sr.__file__, encoding="utf-8").read()
    assert "place_order" not in src and "submit_order" not in src
