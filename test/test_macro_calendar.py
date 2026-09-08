"""The dated macro calendar, and the collision it exists to prevent.

On 2026-09-06 twenty-eight of thirty-six open positions expired 2026-09-11, the morning the
August CPI print lands at 08:30. The engine already had the rule that should have prevented it
-- `_pick_weekly` takes the first expiry MACRO_BUFFER_DAYS past a macro print -- but the only
source of dated catalysts was the desk notes, and the desk described that print in three
notes without ever giving its date. A correct rule with no data to act on is not a control.

These tests lock the two halves of the fix: the calendar knows the dates, and a position that
expires into a high-importance print is told to close before it rather than through it.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "04_live_system"))

import macro_calendar as mc                                    # noqa: E402
import weekly_book as wb                                       # noqa: E402

ET = ZoneInfo("America/New_York")
BEFORE_CPI = datetime(2026, 9, 6, 12, 0, tzinfo=ET)


def test_calendar_knows_the_cpi_date():
    """The specific fact whose absence caused the problem."""
    dates = {e["date"] for e in mc.upcoming(within_days=30, now=BEFORE_CPI)}
    assert "2026-09-11" in dates, "the August CPI date is the whole point of this module"


def test_macro_events_carry_no_tickers():
    """A tape-wide print must be a hazard to clear, never an event to own.

    `_pick_weekly` routes on this: a catalyst WITH tickers pulls the expiry onto the event
    (you want to hold through your own earnings), one WITHOUT pushes the expiry past it. If a
    CPI print ever arrived carrying tickers it would pull every card onto the print instead of
    clearing it -- the exact inversion that made six cards die on one payrolls number.
    """
    for e in mc.upcoming(within_days=45, now=BEFORE_CPI):
        assert not e.get("tickers"), f"{e['label']} must not name tickers"


def test_expiry_on_a_high_importance_print_is_flagged():
    """The 2026-09-11 book, replayed. Every one of those positions must be told to close."""
    row = {"ticker": "TEST", "expiry": "2026-09-11", "direction": "bullish",
           "cur_net": 1.0, "cur_spot": 100.0, "is_debit": True}
    v = wb.exit_verdict(row, live=True)
    assert v["action"] == "CLOSE", v
    assert "CPI" in v["why"]


def test_an_expiry_that_clears_the_print_is_not_flagged():
    """The rule must not fire on every position, or it says nothing.

    A card expiring the following week has a full session after the print to be right, which
    is what MACRO_BUFFER_DAYS was always asking for.
    """
    row = {"ticker": "TEST", "expiry": "2026-09-25", "direction": "bullish",
           "cur_net": 1.0, "cur_spot": 100.0, "is_debit": True}
    v = wb.exit_verdict(row, live=True)
    assert v["action"] != "CLOSE" or "CPI" not in v.get("why", "")


def test_collision_reports_whether_it_lands_on_expiry_day():
    hits = mc.collisions("2026-09-11", now=BEFORE_CPI)
    cpi = [h for h in hits if "CPI" in h["label"]]
    assert cpi and cpi[0]["on_expiry_day"] is True
    assert not mc.collisions("2026-09-08", now=BEFORE_CPI)


def test_no_panel_makes_a_network_call_at_render_time():
    """The ten-minute hang, locked out.

    `weekly.earnings_vol` first called `earnings_vol.scan()` directly, which makes a string of
    Unusual Whales requests. Every other panel in this repo reads a snapshot; that is why the
    page renders in milliseconds and survives a dead vendor. Rendering against the vendor hung
    the suite and would have hung `/markets` under the same rate limiting the scan already
    meets. A panel must be fast and offline, so this asserts the whole markets view renders
    inside a budget no network round trip could fit into.
    """
    import time as _t

    from panels import views
    spec = next(v for v in views.VIEWS if v.get("slug") == "markets")
    t0 = _t.time()
    for fn in spec["panels"]:
        fn()
    assert _t.time() - t0 < 8.0, (
        "a markets panel is doing network work at render time — move it into the scan and "
        "read the result from the snapshot")
