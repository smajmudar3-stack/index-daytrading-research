"""The quarterly stock book: surprise construction, the cohort cut, and a ledger that fills
at the NEXT open, freezes the entry, marks against SPY and closes after the hold."""
import os
import sys

import pandas as pd
from datetime import datetime
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_live_system"))
import swing_stock as ss  # noqa: E402


def test_sue_is_surprise_over_price_not_over_estimate():
    assert ss.sue(1.10, 1.00, 50.0) == pytest.approx(0.002)
    assert ss.sue(0.02, 0.01, 50.0) == pytest.approx(0.0002)     # a tiny estimate does not explode
    assert ss.sue(1.0, 0.9, 0) is None


def test_select_cuts_the_top_share_and_refuses_the_rest_with_a_reason():
    rows = [{"ticker": f"T{i}", "sue": i / 100, "close": 50.0, "adv20": 50e6} for i in range(10)]
    rows.append({"ticker": "CHEAP", "sue": 0.5, "close": 4.0, "adv20": 50e6})
    rows.append({"ticker": "THIN", "sue": 0.5, "close": 50.0, "adv20": 1e6})
    rows.append({"ticker": "NOEPS", "sue": None, "close": 50.0, "adv20": 50e6})
    picks, refused = ss.select(rows)
    assert [p["ticker"] for p in picks] == ["T9", "T8"]              # top 20% of the 10 that qualify
    assert all(p["rank"] <= 2 and p["cohort"] == 10 for p in picks)
    why = {r["ticker"]: r["why"] for r in refused}
    assert "price" in why["CHEAP"] and "volume" in why["THIN"] and "EPS" in why["NOEPS"]
    assert "ranked 3 of 10" in why["T7"]
    assert len(picks) + len(refused) == len(rows)


def _px(open_, close, n=80, end="2026-09-21"):
    idx = pd.bdate_range(end=end, periods=n)
    return pd.DataFrame({"open": [open_] * n, "close": [close] * n, "volume": [1e6] * n}, index=idx)


def test_ledger_fills_at_the_next_open_and_marks_against_spy(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "DB", str(tmp_path / "book.db"))
    monkeypatch.setattr(ss, "_stamp", lambda: "2026-09-18 16:00")
    px = {"ABC": _px(100.0, 110.0), "SPY": _px(500.0, 505.0)}
    picks = [{"ticker": "ABC", "report_date": "2026-09-15", "sue": 0.01, "rank": 1, "cohort": 50}]
    r = ss.book(picks, px, now=pd.Timestamp("2026-09-21 16:00"))
    assert r["added"] == 1 and r["filled"] == 1
    led = ss.ledger()
    row = led["open"][0]
    assert row["entry_date"] == "2026-09-21"         # the first session AFTER the 09-18 issue
    assert row["entry"] == 100.0 and row["pnl_pct"] == 10.0
    assert row["rel_pct"] == pytest.approx(10.0 - 1.0)   # SPY did +1% over the same window
    # recorded once, never re-entered at a fresh price
    r2 = ss.book(picks, px, now=pd.Timestamp("2026-09-22 16:00"))
    assert r2["added"] == 0
    # closes after the hold, not before
    assert ss.ledger()["open"][0]["status"] == "open"
    ss.book([], px, now=pd.Timestamp("2027-01-15 16:00"))
    assert ss.ledger()["closed"][0]["status"] == "closed"


def test_snapshot_schema_is_registered():
    from idt import snapshots
    name, spec = snapshots.schema_for(ss.OUT)
    assert name == "swing_stock" and "picks" in spec["required_when_ok"]


def test_mark_fills_pending_picks_without_rebuilding_the_cohort(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "DB", str(tmp_path / "book.db"))
    monkeypatch.setattr(ss, "_stamp", lambda: "2026-09-18 16:00")
    px = {"ABC": _px(100.0, 104.0), "SPY": _px(500.0, 500.0)}
    monkeypatch.setattr(ss, "_prices", lambda names: {k: v for k, v in px.items() if k in set(names) | {"SPY"}})
    ss.book([{"ticker": "ABC", "report_date": "2026-09-15", "sue": 0.01}], {}, now=pd.Timestamp("2026-09-18 16:00"))
    assert ss.ledger()["open"][0]["status"] == "pending"
    r = ss.mark(now=pd.Timestamp("2026-09-21 16:00"))
    assert r["filled"] == 1 and ss.ledger()["open"][0]["entry"] == 100.0


def test_cached_surprise_fetches_a_print_once_and_retries_unknowns_later(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "DB", str(tmp_path / "ss.db"))
    calls = []

    def fake(ticker, report_date, now=None):
        calls.append(ticker)
        return (1.2, 1.0) if ticker == "KNOWN" else None
    now = datetime(2026, 9, 24, tzinfo=ss.ET)
    assert ss.cached_surprise("KNOWN", "2026-09-20", now=now, fetch=fake) == (1.2, 1.0)
    assert ss.cached_surprise("KNOWN", "2026-09-20", now=now, fetch=fake) == (1.2, 1.0)
    assert calls == ["KNOWN"]                                  # the second read came from the cache
    assert ss.cached_surprise("UNK", "2026-09-20", now=now, fetch=fake) is None
    assert ss.cached_surprise("UNK", "2026-09-20", now=now, fetch=fake) is None
    assert calls.count("UNK") == 1                             # not re-asked the same day
    later = datetime(2026, 9, 28, tzinfo=ss.ET)
    assert ss.cached_surprise("UNK", "2026-09-20", now=later, fetch=fake) is None
    assert calls.count("UNK") == 2                             # asked again after the retry window
