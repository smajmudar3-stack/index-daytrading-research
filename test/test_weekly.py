"""The weekly book: the defects it exists to prevent, asserted directly.

Every test here names a real defect from the swing snapshot of 2026-09-02, which is the
output that prompted the rewrite. They are written against synthetic chains rather than
live ones so they run offline and deterministically -- a test that needed a real chain
would be skipped on a fresh clone, and a skipped test is not a test.
"""

import pandas as pd
import pytest

import desk_notes
import weekly_swing as ws


# ------------------------------------------------------------------- fixtures ---

def chain(strikes, bid, ask, iv=0.30, oi=500):
    """A synthetic option chain frame in the shape yfinance returns."""
    return pd.DataFrame({
        "strike": [float(k) for k in strikes],
        "bid": [bid(k) for k in strikes],
        "ask": [ask(k) for k in strikes],
        "impliedVolatility": [iv] * len(strikes),
        "openInterest": [oi] * len(strikes),
    })


@pytest.fixture
def overlay():
    """A minimal, valid macro overlay with one favour theme and one dated catalyst."""
    return {
        "ok": True,
        "as_of": "2026-09-02 14:00 ET",
        "regime_line": "Bonds are repricing equities.",
        "themes": [
            {"key": "ai", "label": "AI monetizers", "stance": "favour",
             "favours": ["NVDA"], "why": "Capex is converting to revenue."},
            {"key": "rates", "label": "Rate-sensitive equity", "stance": "avoid",
             "against": ["XLRE"], "why": "The long end keeps pushing higher."},
        ],
        "catalysts": [],
        "notes_ingested": [{"date": "2026-09-02 13:30", "subject": "Desk note: Morning"}],
    }


# ------------------------------------ defect 1: strikes that do not exist -------

def test_a_spread_that_collapses_to_one_strike_is_refused():
    """The TTD bug: `round(14.5*0.94, 0)` and `round(14.5, 0)` are both 14.

    The old engine printed "Buy 14P / Sell 14P" as a trade card. A spread whose legs land
    on the same strike is not a weak trade, it is not a trade, and it must never render.
    """
    # A ladder so coarse that both legs want the same rung.
    ladder = [14.0]
    calls = chain(ladder, lambda k: 1.0, lambda k: 1.1)
    puts = chain(ladder, lambda k: 1.0, lambda k: 1.1)
    struct, err = ws._vertical(calls, puts, spot=14.5, dte=7, ladder=ladder, inc=1.0,
                              bullish=False, debit=True)
    assert struct is None
    assert "two strikes" in err or "same listed strike" in err


def test_strikes_come_off_the_real_ladder_never_a_rounded_percentage():
    """The COST bug: 969 and 1015 are not listed strikes; COST lists in fives."""
    ladder = [900.0, 905.0, 910.0, 915.0, 920.0, 925.0, 930.0, 935.0, 940.0, 945.0, 950.0,
              955.0, 960.0, 965.0, 970.0, 975.0]
    # Prices must DECAY with strike or the "spread" has no value and the cost gate
    # correctly refuses it. A flat curve is not a chain.
    def cbid(k):
        return max(0.20, 30.0 - (k - 900.0) * 0.55)
    calls = chain(ladder, cbid, lambda k: cbid(k) + 0.20)
    puts = chain(ladder, lambda k: 5.0, lambda k: 5.2)
    struct, err = ws._vertical(calls, puts, spot=920.0, dte=7, ladder=ladder, inc=5.0,
                               bullish=True, debit=True)
    assert err is None, err
    assert struct["long_strike"] in ladder
    assert struct["short_strike"] in ladder
    assert struct["width"] > 0


def test_a_strike_listed_only_on_the_other_side_is_not_used():
    """Calls and puts do not always list the same rungs.

    The first version snapped against the UNION of both sides and then looked the strike
    up in one frame, so a put-only strike came back as "no such listed strike" and killed
    good candidates. Snapping must happen per side.
    """
    calls = chain([100.0, 105.0], lambda k: 2.0, lambda k: 2.1)
    puts = chain([95.0, 100.0, 105.0], lambda k: 2.0, lambda k: 2.1)
    assert ws._side_ladder(calls) == [100.0, 105.0]
    assert 95.0 in ws._side_ladder(puts)
    assert 95.0 not in ws._side_ladder(calls)


# ---------------------------------------------- fills: ask to buy, bid to sell ---

def test_legs_are_priced_at_the_ask_when_bought_and_the_bid_when_sold():
    """The repo's central lesson, asserted rather than trusted.

    A modelled mid turned +3.7%/trade into approximately break-even on real quotes. If
    this ever silently reverts to mid-pricing, every number on every card is optimistic.
    """
    df = chain([100.0], lambda k: 2.40, lambda k: 2.50)   # 4% wide, passes the buy gate
    bought, err = ws._leg_quote(df, 100.0, buying=True)
    assert err is None
    assert bought["price"] == 2.50            # the ask
    sold, err = ws._leg_quote(df, 100.0, buying=False)
    assert err is None
    assert sold["price"] == 2.40              # the bid


def test_a_leg_with_a_one_sided_quote_is_refused():
    df = chain([100.0], lambda k: 0.0, lambda k: 2.50)
    leg, err = ws._leg_quote(df, 100.0, buying=True)
    assert leg is None and "two-sided" in err


def test_a_wide_quote_is_refused_when_bought_but_tolerated_when_sold():
    """The measured filter applies where it was measured, and nowhere else.

    +5.6% came from filtering contracts you BUY to a 20% spread. Applying the same
    RELATIVE limit to a $0.15 short strike refuses every credit spread on a cheap ETF,
    which is exactly what the first version did to XLE, XHB and XLRE.
    """
    df = chain([100.0], lambda k: 0.10, lambda k: 0.20)     # 67% wide
    bought, err = ws._leg_quote(df, 100.0, buying=True)
    assert bought is None and "bought" in err
    sold, err = ws._leg_quote(df, 100.0, buying=False)
    assert err is None and sold["price"] == 0.10


def test_a_spread_whose_execution_eats_the_risk_is_refused():
    """The binding gate: total half-spread measured against the money at risk."""
    ladder = [100.0, 105.0]
    # Wide two-sided quotes: mid-priced spread is tight, real fills are not.
    calls = chain(ladder, lambda k: (8.0 if k == 100 else 4.0),
                  lambda k: (8.6 if k == 100 else 4.6))
    puts = chain(ladder, lambda k: 1.0, lambda k: 1.1)
    struct, err = ws._vertical(calls, puts, spot=100.0, dte=7, ladder=ladder, inc=5.0,
                               bullish=True, debit=True)
    assert struct is None
    assert "spread costs" in err


# ------------------------------- defect 3: the macro is the primary voter -------

def test_a_name_no_theme_names_is_never_proposed(overlay):
    """The fix for ranking a hundred names on momentum and always finding eight."""
    view = ws._macro_view(overlay, "AAPL")
    assert view["side"] == 0
    assert "no desk-note theme" in view["stand_down"]
    direction, why, vol_only = ws._decide(view, {"score": 0.9, "m60": 20.0})
    assert direction is None


def test_a_theme_naming_a_ticker_on_both_sides_stands_it_down(overlay):
    """A genuine contradiction in the macro read is not a half-size trade."""
    overlay["themes"].append({"key": "x", "label": "Contradiction", "stance": "avoid",
                              "against": ["NVDA"], "why": "..."})
    view = ws._macro_view(overlay, "NVDA")
    assert view["side"] == 0
    assert "contradicts itself" in view["stand_down"]


def test_macro_and_tape_in_hard_conflict_stands_the_name_down(overlay):
    view = ws._macro_view(overlay, "NVDA")
    assert view["side"] == 1
    direction, why, vol_only = ws._decide(view, {"score": -0.80, "m60": -12.0})
    assert direction is None
    assert "tape disagrees" in why


def test_the_same_conflict_becomes_a_volatility_trade_when_the_name_has_its_own_event(overlay):
    """AVGO went into its own print down 7% over 60 days.

    That is a reason not to express the week directionally, not a reason to skip the only
    real catalyst on the board.
    """
    view = ws._macro_view(overlay, "NVDA")
    cat = {"label": "NVDA earnings", "date": "2026-09-03", "days_away": 1}
    direction, why, vol_only = ws._decide(view, {"score": -0.80, "m60": -12.0},
                                          own_catalyst=cat)
    assert direction == "bullish"
    assert vol_only is True
    assert "volatility trade" in why


# ---------------------------------------- defect 2: the expiry is really weekly ---

def test_a_names_own_event_takes_the_first_expiry_that_covers_it(monkeypatch):
    """You must still be holding when the print lands, or you did not trade it."""
    monkeypatch.setattr(ws, "_expiries", lambda tk: ["2026-09-04", "2026-09-11", "2026-09-18"])
    monkeypatch.setattr(ws, "_dte", lambda e: {"2026-09-04": 2, "2026-09-11": 9,
                                               "2026-09-18": 16}[e])
    exp, dte, why = ws._pick_weekly(
        "AVGO", [{"label": "AVGO earnings", "date": "2026-09-02", "days_away": 0}], [])
    assert exp == "2026-09-04"
    assert why.startswith("covers")


def test_a_macro_print_takes_an_expiry_with_room_left_afterwards(monkeypatch):
    """Friday's payrolls pulled every card onto the 2-day expiry.

    Six "weekly" trades all died on one macro print. A tape-wide event is a hazard the
    position has to survive, not the thing being bought.
    """
    monkeypatch.setattr(ws, "_expiries", lambda tk: ["2026-09-04", "2026-09-11", "2026-09-18"])
    monkeypatch.setattr(ws, "_dte", lambda e: {"2026-09-04": 2, "2026-09-11": 9,
                                               "2026-09-18": 16}[e])
    exp, dte, why = ws._pick_weekly(
        "QQQ", [], [{"label": "August payrolls", "date": "2026-09-04", "days_away": 2}])
    assert exp == "2026-09-11"
    assert dte - 2 >= ws.MACRO_BUFFER_DAYS
    assert "clears" in why


def test_a_trade_with_no_event_of_its_own_gets_a_real_week(monkeypatch):
    monkeypatch.setattr(ws, "_expiries", lambda tk: ["2026-09-03", "2026-09-11"])
    monkeypatch.setattr(ws, "_dte", lambda e: {"2026-09-03": 1, "2026-09-11": 9}[e])
    exp, dte, why = ws._pick_weekly("QQQ", [], [])
    assert dte >= ws.DTE_MIN_SWING


# ------------------------------------------------- defect 6: exits always exist ---

def test_every_structure_gets_a_target_a_stop_and_a_price_that_kills_it():
    """Not one card in the old snapshot carried any of the three."""
    trend = {"lo20": 90.0, "hi20": 120.0}
    for debit in (True, False):
        struct = {"debit": debit, "width": 5.0, "net": 2.0, "short_strike": 105.0}
        e = ws._exits(struct, trend, "bullish" if debit else "bearish", 100.0, 3.2)
        assert e["target"] and e["stop"] and e["invalidation"]
        assert isinstance(e["invalidation_level"], float)
        assert "3.2%" in e["invalidation"]          # the priced move is stated


def test_the_invalidation_level_is_a_price_on_the_correct_side():
    trend = {"lo20": 90.0, "hi20": 120.0}
    struct = {"debit": True, "width": 5.0, "net": 2.0, "short_strike": 105.0}
    assert ws._exits(struct, trend, "bullish", 100.0, None)["invalidation_level"] == 90.0
    assert ws._exits(struct, trend, "bearish", 100.0, None)["invalidation_level"] == 120.0


# --------------------------------------------------------- the overlay itself ---

def test_the_engine_refuses_to_produce_cards_without_a_macro_overlay(state, monkeypatch):
    """Gates fail CLOSED. No macro read means no macro-conditioned trades, not stale ones."""
    import importlib
    import idt.snapshots
    importlib.reload(idt.snapshots)
    importlib.reload(desk_notes)
    importlib.reload(ws)

    out = ws.run()
    assert out["ok"] is False
    assert out["cards"] == []
    assert "overlay" in out["blocked"].lower()
    assert out["fix"]


def test_an_overlay_older_than_two_sessions_is_refused_not_faded(state):
    """A macro read from last week applied to this week looks exactly like information."""
    from idt import snapshots
    state.put("desk_notes.json", data={
        "ok": True, "as_of": "2026-08-20 09:00 ET", "regime_line": "old",
        "themes": [], "schema_version": 1})
    state.age("desk_notes.json", ws.desk_notes.MAX_AGE_MIN + 60)
    _, st = snapshots.read("desk_notes.json")
    assert st == "stale"


def test_age_is_measured_from_the_notes_own_date_not_the_files_mtime():
    """Rewriting the file does not make a Monday note describe Thursday."""
    fresh = desk_notes.age_min({"notes_ingested": [{"date": "2026-09-02 13:30"}]})
    old = desk_notes.age_min({"notes_ingested": [{"date": "2026-08-25 13:30"}]})
    assert old > fresh


def test_merging_the_same_note_twice_is_a_no_op():
    base = {"themes": [], "catalysts": [], "drivers": [], "desk_book": [],
            "notes_ingested": []}
    parsed = {"themes": [{"key": "a", "label": "A", "stance": "favour", "why": "w"}]}
    once, added1 = desk_notes.merge_note(base, parsed, "Desk note: Morning", "2026-09-02 09:29")
    twice, added2 = desk_notes.merge_note(once, parsed, "Desk note: Morning", "2026-09-02 09:29")
    assert added1 is True and added2 is False
    assert len(twice["themes"]) == 1


def test_a_theme_revisited_by_a_later_note_updates_rather_than_duplicating():
    base = {"themes": [], "catalysts": [], "drivers": [], "desk_book": [],
            "notes_ingested": []}
    a, _ = desk_notes.merge_note(
        base, {"themes": [{"key": "rates", "label": "Rates", "stance": "watch", "why": "v1"}]},
        "Note A", "2026-09-01 09:00")
    b, _ = desk_notes.merge_note(
        a, {"themes": [{"key": "rates", "label": "Rates", "stance": "avoid", "why": "v2"}]},
        "Note B", "2026-09-02 09:00")
    rates = [t for t in b["themes"] if t["key"] == "rates"]
    assert len(rates) == 1
    assert rates[0]["stance"] == "avoid" and rates[0]["why"] == "v2"


def test_a_theme_missing_a_required_field_is_ignored_not_half_used(overlay):
    overlay["themes"].append({"key": "broken", "favours": ["NVDA"]})   # no label/stance/why
    keys = [t["key"] for t in desk_notes.themes(overlay)]
    assert "broken" not in keys


def test_a_past_catalyst_is_dropped_on_merge():
    base = {"themes": [], "catalysts": [{"date": "2020-01-01", "label": "ancient"}],
            "drivers": [], "desk_book": [], "notes_ingested": []}
    out, _ = desk_notes.merge_note(base, {}, "Note", "2026-09-02 09:00")
    assert all(c["date"] != "2020-01-01" for c in out["catalysts"])


# ============================================================ the live ledger ===
#
# Every test here guards a way the ledger could quietly become a brochure: by losing the
# original entry price, by pricing the exit optimistically, or by closing positions on
# quotes nobody would trade at.

import weekly_book as wb


@pytest.fixture
def book(state, monkeypatch):
    """A ledger pointed at the temp state root, with its module reloaded to see it."""
    import importlib
    import idt.paths
    importlib.reload(idt.paths)
    importlib.reload(wb)
    return wb


CARD = {
    "ticker": "NVDA", "direction": "bullish", "structure": "Call debit spread",
    "legs": "Buy 225C / Sell 235C", "expiry": "2099-09-09", "back_expiry": None,
    "right": "C", "long_strike": 225.0, "short_strike": 235.0,
    "is_debit": True, "is_calendar": False, "net": 2.80, "width": 10.0,
    "max_risk_usd": 280.0, "spot": 224.0, "target_net": 6.00, "stop_net": 1.40,
    "invalidation_level": 207.0, "themes": [{"label": "AI monetizers"}],
}


def test_the_entry_price_is_never_rewritten_by_a_later_scan(book):
    """The failure this whole module exists to prevent.

    The generator re-issues the same structure every four hours at whatever it costs then.
    If each of those overwrote the entry, a position down 40% would read flat forever and
    the page would show healthy suggestions permanently.
    """
    assert book.record([CARD]) == 1
    later = dict(CARD, net=1.10)                    # same trade, cheaper, hours later
    assert book.record([later]) == 0                # not a new recommendation
    rows = book.open_book()
    assert len(rows) == 1
    assert rows[0]["entry_net"] == 2.80             # the ORIGINAL price, not 1.10


def test_closing_a_debit_spread_sells_the_long_at_the_bid(book, monkeypatch):
    """The exit must mirror the entry or the round trip is free and the P&L is a fiction."""
    import weekly_swing as ws
    calls = chain([225.0, 235.0],
                  lambda k: 12.00 if k == 225 else 5.00,     # bids
                  lambda k: 12.40 if k == 225 else 5.40)     # asks
    monkeypatch.setattr(ws, "_chain", lambda tk, exp: (calls, calls))
    row = {"expiry": "2099-09-09", "is_calendar": 0, "right": "C",
           "long_strike": 225.0, "short_strike": 235.0, "is_debit": 1,
           "back_expiry": None}
    net, err = book._exit_net(ws, "NVDA", row)
    assert err is None
    assert net == pytest.approx(12.00 - 5.40)       # long at BID, short back at ASK


def test_closing_a_credit_spread_buys_the_short_back_at_the_ask(book, monkeypatch):
    import weekly_swing as ws
    puts = chain([220.0, 210.0],
                 lambda k: 4.00 if k == 220 else 2.00,
                 lambda k: 4.30 if k == 220 else 2.30)
    monkeypatch.setattr(ws, "_chain", lambda tk, exp: (puts, puts))
    row = {"expiry": "2099-09-09", "is_calendar": 0, "right": "P",
           "long_strike": 210.0, "short_strike": 220.0, "is_debit": 0,
           "back_expiry": None}
    net, err = book._exit_net(ws, "NVDA", row)
    assert err is None
    assert net == pytest.approx(4.30 - 2.00)        # short back at ASK, long out at BID


def test_pnl_signs_are_right_for_both_directions(book):
    debit = {"is_debit": 1, "is_calendar": 0, "entry_net": 2.80, "max_risk": 280.0}
    usd, pct = book._pnl(debit, 4.00)               # sold for more than paid
    assert usd > 0 and pct > 0
    usd, pct = book._pnl(debit, 1.00)
    assert usd < 0

    credit = {"is_debit": 0, "is_calendar": 0, "entry_net": 2.00, "max_risk": 300.0}
    usd, pct = book._pnl(credit, 0.80)              # bought back cheaper
    assert usd > 0
    usd, pct = book._pnl(credit, 3.50)
    assert usd < 0


def test_nothing_is_closed_on_an_after_hours_mark(book, monkeypatch):
    """Quotes widen the moment the bell goes.

    The first live run marked six fresh positions minutes after the close and showed one
    down 29% on spread alone. Acting on that would stop out every position, every night.
    """
    import weekly_swing as ws
    book.record([CARD])
    # A quote far through the stop, but the market is shut.
    calls = chain([225.0, 235.0], lambda k: 0.10, lambda k: 0.20)
    monkeypatch.setattr(ws, "_chain", lambda tk, exp: (calls, calls))
    monkeypatch.setattr(ws, "_hist", lambda tk: None)
    monkeypatch.setattr(book, "_market_open", lambda: False)

    res = book.mark()
    assert res["closed"] == 0
    assert res["live"] is False
    assert res["mark_note"]
    assert book.open_book()[0]["status"] == "open"
    assert book.open_book()[0]["pnl_pct"] is not None      # still marked, just not closed


def test_a_stop_does_close_when_the_market_is_open(book, monkeypatch):
    import weekly_swing as ws
    book.record([CARD])
    calls = chain([225.0, 235.0], lambda k: 0.10, lambda k: 0.20)
    monkeypatch.setattr(ws, "_chain", lambda tk, exp: (calls, calls))
    monkeypatch.setattr(ws, "_hist", lambda tk: None)
    monkeypatch.setattr(book, "_market_open", lambda: True)

    res = book.mark()
    assert res["closed"] == 1
    assert book.history()[0]["close_reason"] == "stop"


def test_invalidation_outranks_a_target(book, monkeypatch):
    """A target reached after the reason evaporated is luck, and logging it as a win
    teaches the wrong thing."""
    import pandas as pd
    import weekly_swing as ws
    book.record([CARD])
    # Spread is worth its full width (target hit), but spot is through the 207 invalidation.
    calls = chain([225.0, 235.0],
                  lambda k: 20.0 if k == 225 else 9.9,
                  lambda k: 20.2 if k == 235 else 10.0)
    monkeypatch.setattr(ws, "_chain", lambda tk, exp: (calls, calls))
    monkeypatch.setattr(ws, "_hist",
                        lambda tk: pd.DataFrame({"close": [200.0], "high": [201.0],
                                                 "low": [199.0]}))
    monkeypatch.setattr(book, "_market_open", lambda: True)

    book.mark()
    assert book.history()[0]["close_reason"] == "invalidated"


def test_an_expired_position_settles_on_intrinsic_not_on_a_quote(book):
    row = {"is_calendar": 0, "right": "C", "long_strike": 225.0, "short_strike": 235.0,
           "is_debit": 1}
    assert book._intrinsic(row, 240.0) == pytest.approx(10.0)    # both in, full width
    assert book._intrinsic(row, 230.0) == pytest.approx(5.0)
    assert book._intrinsic(row, 210.0) == pytest.approx(0.0)     # worthless


def test_the_track_record_always_reports_its_own_sample_size(book):
    """A 100% hit rate on two trades is not a track record."""
    assert book.record_summary()["n"] == 0
    book.record([CARD])
    s = book.record_summary()
    assert s["n"] == 0                          # open positions are not a record
