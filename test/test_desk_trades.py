"""The emails as trades: the desk's action text parsed into a direction and a kind, the
overlay turned into positions by source with conflicts stated, and a ledger that fills at
the next open, marks shorts with the right sign, and closes when the desk exits."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_live_system"))
import desk_notes  # noqa: E402
import desk_trades as dt  # noqa: E402


def _px(open_, close, n=80, end="2026-10-05"):
    idx = pd.bdate_range(end=end, periods=n)
    return pd.DataFrame({"open": [open_] * n, "close": [close] * n, "volume": [1e6] * n}, index=idx)


@pytest.mark.parametrize("text,direction,kind", [
    ("bought Oct 9 146/143 put debit spread, indicative debit ~$1.18", -1, "open"),
    ("reduced 0.25 unit", 1, "reduce"),
    ("added 0.5 unit XLF", 1, "add"),
    ("closed the GLD position at ~$25.14", 1, "close"),
    ("shorted IWM against the QQQ long", -1, "open"),
    ("bought Oct puts as protection over the weekend", -1, "hedge"),
    ("sold the call credit spread", -1, "reduce"),
])
def test_parse_action_reads_the_desks_own_words(text, direction, kind):
    assert dt.parse_action(text) == (direction, kind)


def test_positions_from_the_overlay_by_source_with_conflicts_stated():
    now = pd.Timestamp("2026-10-05 12:00", tz=dt.ET)
    ov = {
        "desk_book": [
            {"asset": "USO", "action": "bought Oct 9 146/143 put debit spread", "date": "2026-10-02 15:40"},
            {"asset": "GLD", "action": "reduced 0.25 unit", "date": "2026-10-01 10:00"},
            {"asset": "USO", "action": "bought puts as protection", "date": "2026-10-03 09:00"},
            {"asset": "Brent crude", "action": "bought", "date": "2026-10-03 09:00"},
            {"asset": "WEAT", "action": "bought", "date": "2026-08-01 09:00"},              # too old
        ],
        "trade_calls": [
            {"instrument": "XLF", "direction": "long", "horizon": "weeks", "conviction": "high", "why": "steepener", "date": "2026-10-02 09:43"},
            {"instrument": "XHB", "direction": "avoid", "horizon": "months", "why": "rates", "date": "2026-10-02 09:43"},
            {"instrument": "Brent crude", "direction": "short", "horizon": "days", "why": "x", "date": "2026-10-02 09:43"},
        ],
        "themes": [
            {"key": "a", "label": "Banks win", "stance": "favour", "favours": ["JPM", "BAC"], "why": "w", "updated": "2026-10-02 09:43"},
            {"key": "b", "label": "Banks lose", "stance": "avoid", "against": ["JPM"], "why": "w", "updated": "2026-10-01 09:00"},
            {"key": "c", "label": "Old theme", "stance": "favour", "favours": ["IWM"], "why": "w", "updated": "2026-09-01 09:00"},
            {"key": "d", "label": "Housing", "stance": "avoid", "against": ["ITB"], "why": "w", "updated": "2026-10-02 09:43"},
        ],
    }
    pos, closes, conflicts, skipped = dt.positions_from(ov, now=now)
    by = {(p["source"], p["ticker"]): p for p in pos}
    assert by[("desk", "USO")]["dir"] == -1                                   # the put spread, mirrored short
    assert [c["ticker"] for c in closes] == ["GLD"]                           # the reduce closes GLD
    assert ("desk", "BRENT CRUDE") not in by and any(s["what"] == "BRENT CRUDE" for s in skipped)
    assert not any(p["ticker"] == "WEAT" for p in pos)                         # outside the window
    assert any("hedge" in s["why"] for s in skipped)                           # protection is not a view
    assert by[("call", "XLF")]["dir"] == 1 and by[("call", "XLF")]["hold"] == 21
    assert by[("call", "XHB")]["dir"] == -1 and by[("call", "XHB")]["hold"] == 63  # avoid = paper short, months
    assert not any(k[0] == "call" and "CRUDE" in k[1] for k in by)            # a commodity word is not a ticker
    assert by[("theme", "BAC")]["dir"] == 1 and by[("theme", "ITB")]["dir"] == -1
    assert ("theme", "JPM") not in by and conflicts[0]["ticker"] == "JPM"     # argued both ways -> not traded
    assert ("theme", "IWM") not in by                                         # stale theme


def test_ledger_fills_marks_shorts_with_the_right_sign_and_closes_on_the_desks_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(dt, "DB", str(tmp_path / "dt.db"))
    monkeypatch.setattr(dt, "_stamp", lambda: "2026-10-01 16:00")
    px = {"USO": _px(100.0, 90.0), "XLF": _px(50.0, 55.0), "SPY": _px(500.0, 505.0)}
    pos = [{"source": "desk", "ticker": "USO", "dir": -1, "hold": 21, "src_date": "2026-10-01 10:00", "why": "put spread"},
           {"source": "call", "ticker": "XLF", "dir": 1, "hold": 21, "src_date": "2026-10-01 10:00", "why": "steepener"}]
    r = dt.book(pos, [], px, now=pd.Timestamp("2026-10-03 16:00", tz=dt.ET))
    assert r["added"] == 2 and r["filled"] == 2
    led = dt.ledger()
    uso = [x for x in led["open"] if x["ticker"] == "USO"][0]
    assert uso["entry_date"] == "2026-10-02" and uso["pnl_pct"] == pytest.approx(10.0)        # short, name fell 10%
    assert uso["rel_pct"] == pytest.approx(11.0)                                                 # and SPY rose 1%
    xlf = [x for x in led["open"] if x["ticker"] == "XLF"][0]
    assert xlf["pnl_pct"] == pytest.approx(10.0) and xlf["rel_pct"] == pytest.approx(9.0)
    # the same call again does not open a second position
    assert dt.book(pos, [], px, now=pd.Timestamp("2026-10-03 17:00", tz=dt.ET))["added"] == 0
    # the desk exits USO -> the mirror closes on the next mark
    dt.book([], [{"ticker": "USO", "why": "closed the put spread"}], px, now=pd.Timestamp("2026-10-04 16:00", tz=dt.ET))
    assert [x["ticker"] for x in dt.ledger()["closed"]] == ["USO"]
    assert dt.ledger()["by_source"]["desk"]["closed"]["n"] == 1


def test_merge_note_accumulates_the_desk_book_stamps_themes_and_keeps_trade_calls():
    base = {"themes": [], "catalysts": [], "drivers": [], "desk_book": [], "notes_ingested": []}
    a, _ = desk_notes.merge_note(base, {"desk_book": [{"asset": "GLD", "action": "reduced 0.25 unit"}],
                                        "themes": [{"key": "k", "label": "L", "stance": "favour", "favours": ["XLF"], "why": "w"}],
                                        "implications": [{"instrument": "xlf", "direction": "long", "horizon": "weeks", "why": "w"}]},
                                 "Desk note: Trade Update", "2026-10-01 10:00")
    b, _ = desk_notes.merge_note(a, {"desk_book": [{"asset": "USO", "action": "bought put spread"}],
                                     "themes": [{"key": "k", "label": "L", "stance": "avoid", "favours": ["XLF"], "why": "w2"}]},
                                 "Desk note: USO", "2026-10-02 15:40")
    assert [x["asset"] for x in b["desk_book"]] == ["GLD", "USO"]           # accumulated, not replaced
    assert b["desk_book"][1]["date"] == "2026-10-02 15:40"
    t = b["themes"][0]
    assert t["stance"] == "avoid" and t["updated"] == "2026-10-02 15:40" and t["first_seen"] == "2026-10-01 10:00"
    assert b["trade_calls"][0]["instrument"] == "XLF" and b["trade_calls"][0]["date"] == "2026-10-01 10:00"


def test_snapshot_schema_is_registered_and_nothing_places_an_order():
    from idt import snapshots
    name, spec = snapshots.schema_for(dt.OUT)
    assert name == "desk_trades" and "positions" in spec["required_when_ok"]
    src = open(dt.__file__, encoding="utf-8").read()
    assert "place_order" not in src and "submit_order" not in src
