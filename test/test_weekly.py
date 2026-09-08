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

# NOTE: the earlier pair of tests here asserted that a themeless name could clear a HIGHER
# bar on the measured voters alone. That behaviour was deliberately reversed on 2026-09-06 --
# see `test_a_card_with_no_macro_theme_is_refused_outright` below, and the 16:02 cycle that
# shipped JNJ and NEM with zero themes on a single input. `VOTE_NO_MACRO_FALLBACK` survives
# only for the case where `REQUIRE_MACRO_BASIS` is switched back off.


def test_the_fallback_bar_is_higher_than_the_themed_one():
    assert ws.VOTE_NO_MACRO_FALLBACK > ws.VOTE_NEUTRAL


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
    vote = {"score": -0.80, "n_inputs": 3, "unmeasured_share": 0.2,
            "detail": [{"input": "trend", "contribution": -0.5}]}
    direction, why, vol_only = ws._decide(view, {"score": -0.80, "m60": -12.0}, vote)
    assert direction is None
    assert "against it" in why


def test_the_same_conflict_becomes_a_volatility_trade_when_the_name_has_its_own_event(overlay):
    """AVGO went into its own print down 7% over 60 days.

    That is a reason not to express the week directionally, not a reason to skip the only
    real catalyst on the board.
    """
    view = ws._macro_view(overlay, "NVDA")
    cat = {"label": "NVDA earnings", "date": "2026-09-03", "days_away": 1}
    vote = {"score": -0.80, "n_inputs": 3, "unmeasured_share": 0.2,
            "detail": [{"input": "trend", "contribution": -0.5}]}
    direction, why, vol_only = ws._decide(view, {"score": -0.80, "m60": -12.0}, vote,
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
           "back_expiry": None, "legs_json": None}
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
           "back_expiry": None, "legs_json": None}
    net, err = book._exit_net(ws, "NVDA", row)
    assert err is None
    # Signed CASH: selling the long in brings 2.00, buying the short back costs 4.30, so
    # closing takes 2.30 out of pocket. Negative, and the same convention as the entry.
    assert net == pytest.approx(2.00 - 4.30)


def test_pnl_signs_are_right_for_both_directions(book):
    """One formula, exit minus entry, both in signed cash."""
    debit = {"is_debit": 1, "is_calendar": 0, "entry_net": 2.80, "max_risk": 280.0}
    usd, pct = book._pnl(debit, 4.00)               # closes for more than it cost
    assert usd > 0 and pct > 0
    usd, pct = book._pnl(debit, 1.00)
    assert usd < 0

    # Opened for a 2.00 credit, so entry_net is NEGATIVE.
    credit = {"is_debit": 0, "is_calendar": 0, "entry_net": -2.00, "max_risk": 300.0}
    usd, pct = book._pnl(credit, -0.80)             # cheaper to buy back than taken in
    assert usd > 0
    usd, pct = book._pnl(credit, -3.50)             # costs more to close than taken in
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
           "is_debit": 1, "legs_json": None}
    assert book._intrinsic(row, 240.0) == pytest.approx(10.0)    # both in, full width
    assert book._intrinsic(row, 230.0) == pytest.approx(5.0)
    assert book._intrinsic(row, 210.0) == pytest.approx(0.0)     # worthless


def test_the_track_record_always_reports_its_own_sample_size(book):
    """A 100% hit rate on two trades is not a track record."""
    assert book.record_summary()["n"] == 0
    book.record([CARD])
    s = book.record_summary()
    assert s["n"] == 0                          # open positions are not a record


# ================================ structures, weighting, and the sign convention ===

import weekly_structures as wst
import signal_weights as sw


def leg(right, strike, price, buying, qty=1):
    return {"right": right, "strike": float(strike), "price": float(price),
            "buying": buying, "qty": qty}


# ------------------------------------------------- the payoff / risk engine ----

def test_max_risk_is_read_off_the_payoff_curve_not_a_per_structure_formula():
    """A vertical, a condor and a backspread each have a different risk formula.

    Nine structures times a bespoke formula is nine chances to be silently wrong about how
    much money is on the table. One payoff walk is correct for all of them.
    """
    # 10-wide call debit spread paid for 3.00 -> risk 3.00, reward 7.00.
    v = [leg("C", 100, 6.0, True), leg("C", 110, 3.0, False)]
    risk, reward, net = wst.evaluate(v)
    assert risk == pytest.approx(3.0) and reward == pytest.approx(7.0)
    assert net == pytest.approx(3.0)

    # Iron condor, 5-wide wings, 2.00 credit -> risk 3.00, reward 2.00.
    c = [leg("P", 90, 1.0, False), leg("P", 85, 0.4, True),
         leg("C", 110, 1.4, False), leg("C", 115, 0.8, True)]
    risk, reward, net = wst.evaluate(c)
    assert risk == pytest.approx(3.8, abs=0.01)
    assert reward == pytest.approx(1.2, abs=0.01)
    assert net < 0                                     # a credit


def test_a_call_debit_spread_is_not_treated_as_naked():
    """The check was backwards and rejected every ordinary vertical.

    It demanded a short call be covered by a long call at a HIGHER strike. Long 165C /
    short 172.5C is capped at the debit above 172.5 — it is not naked, and refusing it
    knocked XOM and CVX out of the book entirely.
    """
    assert wst.is_defined_risk([leg("C", 165, 5.0, True), leg("C", 172.5, 2.0, False)])
    assert wst.is_defined_risk([leg("C", 165, 5.0, False), leg("C", 172.5, 2.0, True)])
    assert wst.is_defined_risk([leg("P", 100, 2.0, False), leg("P", 95, 1.0, True)])


def test_being_net_short_a_right_is_what_makes_it_naked():
    assert not wst.is_defined_risk([leg("C", 100, 3.0, False)])
    assert not wst.is_defined_risk([leg("C", 100, 3.0, False, qty=2),
                                    leg("C", 110, 1.0, True, qty=1)])
    # A backspread is short one and long two: defined.
    assert wst.is_defined_risk([leg("C", 100, 3.0, False, qty=1),
                                leg("C", 110, 1.0, True, qty=2)])


def test_the_menu_offers_opposite_structures_for_opposite_magnitude_reads():
    """A condor and a straddle are both non-directional and they are opposite bets.

    The old engine only ever asked about direction, which is why every card it produced
    was a vertical.
    """
    compress = wst.menu("neutral", "compress", "rich", False, False)
    expand = wst.menu("neutral", "expand", "cheap", False, False)
    assert compress[0] == "iron_condor"
    assert "long_straddle" not in compress
    assert expand[0] == "reverse_condor"
    assert "iron_condor" not in expand


def test_a_steep_term_structure_over_an_event_leads_with_the_calendar():
    assert wst.menu("neutral", "normal", "rich", True, True)[0] == "calendar"
    assert wst.menu("bullish", "normal", "rich", True, True)[0] == "diagonal"


def test_every_range_selling_structure_is_flagged_as_such():
    """So the gamma-flip refusal can find them without a name-by-name list elsewhere."""
    for n in ("iron_condor", "iron_butterfly", "put_credit", "call_credit"):
        assert n in wst.RANGE_SELLING
    for n in ("long_straddle", "call_debit", "reverse_condor"):
        assert n not in wst.RANGE_SELLING


def test_the_measured_losers_carry_their_measurement():
    for n in ("iron_condor", "iron_butterfly", "long_straddle", "long_strangle"):
        assert "MEASURED" in wst.EVIDENCE[n]
    assert "74.8%" in wst.EVIDENCE["iron_condor"]        # the seductive win rate
    assert "−100%" in wst.EVIDENCE["long_strangle"] or "-100%" in wst.EVIDENCE["long_strangle"]


# --------------------------------------------------- the weighting authority ----

def test_an_implausible_calibration_is_rejected_rather_than_believed():
    """|IC| of 0.62 is not a discovery, it is a broken calibration.

    data/uw_weights.json carried short_float_pct at -0.621 and oi_change_net at +0.265 —
    the latter being an input the registry records as a measured NULL. A weighting
    authority that believes those is worse than one with no calibration at all.
    """
    assert sw.IC_IMPLAUSIBLE < 0.62

    # THE CALIBRATION IS INJECTED, not read off disk. This used to assert against whatever
    # `data/uw_weights.json` happened to contain, so it only exercised the rejection path on a
    # machine where that file already held a broken number — it passed here and failed on a
    # clean install, where the file does not exist and the tier is simply "measured". A test
    # that depends on local state is not testing the logic.
    import unittest.mock as _mock
    broken = {"weights": {"short_float_pct": {"ic": -0.621, "n": 13219}}}
    with _mock.patch.object(sw, "_calibrated", lambda: broken):
        w, tier, sign = sw.weight("short_float_pct")
    assert "rejected" in tier, tier
    assert w == pytest.approx(sw.REGISTRY["short_float_pct"][0])

    # And the plausible case still blends, so the guard rejects the impossible rather than
    # everything.
    sane = {"weights": {"short_float_pct": {"ic": 0.03, "n": 13219}}}
    with _mock.patch.object(sw, "_calibrated", lambda: sane):
        _w2, tier2, _s2 = sw.weight("short_float_pct")
    assert "rejected" not in tier2, tier2


def test_a_calibration_may_adjust_a_prior_but_never_replace_it():
    """Before the band, every calibrated input came out at ~0.99 and the priors were dead.

    Insider open buys (prior 0.10, n=1,128, sign flips by era) were being served at the
    same weight as short interest (prior 0.30, n=13,219, monotone in horizon).
    """
    for name in sw.REGISTRY:
        prior, tier, _sign, _ev = sw.REGISTRY[name]
        w, _t, _s = sw.weight(name)
        if tier == "measured-null":
            assert w == 0.0
        else:
            assert w <= max(prior * sw.CAL_BAND_HI, prior) + 1e-9, name
            assert w >= min(prior * sw.CAL_BAND_LO, prior) - 1e-9, name


def test_insider_buys_weigh_less_than_short_interest_because_they_were_tested_less():
    """The whole point of weighting by evidence."""
    ins, _t, _s = sw.weight("insider_open_buys")
    shorts, _t2, _s2 = sw.weight("short_float_pct")
    assert ins < shorts


def test_a_measured_null_can_never_be_revived():
    for n in ("sector_rotation", "gamma_direction", "iv_rel", "oi_change_net"):
        w, tier, sign = sw.weight(n)
        assert w == 0.0 and sign == 0


def test_short_interest_enters_negatively_and_the_caller_passes_a_magnitude():
    """Negating it at the call site too would flip it back to bullish."""
    _w, _t, sign = sw.weight("short_float_pct")
    assert sign == -1
    res = sw.combine({"short_float_pct": 1.0})
    assert res["score"] < 0


def test_the_unmeasured_share_is_reported_so_it_can_be_shown():
    res = sw.combine({"desk_macro": 1.0, "trend": 1.0})
    assert 0 < res["unmeasured_share"] < 1
    assert res["confidence"] == pytest.approx(1 - res["unmeasured_share"])


# ------------------------------------------------ the VIX backwardation signal ----

def test_backwardation_abstains_rather_than_voting_the_other_way(monkeypatch):
    """What was measured is the CONJUNCTION of backwardation and a golden cross.

    Nothing was measured about the opposite case, so reading a symmetric claim out of a
    one-sided result would be turning a finding into folklore.
    """
    import pandas as pd
    import weekly_swing as ws

    def fake(*a, **k):
        n = 250
        return {"Close": pd.DataFrame({
            "^VIX": [15.0] * n, "^VIX3M": [18.0] * n,          # contango, NOT backwardated
            "SPY": list(range(400, 400 + n))})}                 # golden cross intact

    monkeypatch.setattr(ws, "_yf", lambda: type("Y", (), {"download": staticmethod(fake)}))
    m = ws.market_signal()
    assert m["vote"] == 0.0
    assert m["backwardated"] is False
    assert "abstains" in m["why"]


def test_backwardation_inside_a_golden_cross_votes_positive(monkeypatch):
    import pandas as pd
    import weekly_swing as ws

    def fake(*a, **k):
        n = 250
        return {"Close": pd.DataFrame({
            "^VIX": [22.0] * n, "^VIX3M": [20.0] * n,          # backwardated
            "SPY": list(range(400, 400 + n))})}

    monkeypatch.setattr(ws, "_yf", lambda: type("Y", (), {"download": staticmethod(fake)}))
    m = ws.market_signal()
    assert m["vote"] > 0
    assert m["backwardated"] is True and m["golden_cross"] is True


# ------------------------------------------- one sign convention in the ledger ----

def test_a_credit_spread_that_costs_more_to_close_is_a_loss(book):
    """DELL was opened for a 4.18 credit, would cost 5.61 to close, and read +6.9%.

    Both numbers are signed CASH: entry is what the position cost to put on (negative when
    a credit came in), the mark is what closing would pay you (negative when it costs).
    P&L is exit minus entry for every structure, with no per-structure branch to get wrong.
    """
    row = {"is_debit": 0, "is_calendar": 0, "entry_net": -4.18, "max_risk": 2073.0}
    usd, pct = book._pnl(row, -5.61)
    assert usd < 0 and pct < 0
    usd, pct = book._pnl(row, -3.00)                  # cheaper to close than the credit
    assert usd > 0 and pct > 0


def test_a_four_leg_condor_can_be_marked(book, monkeypatch):
    """The two-leg model could not describe a condor at all, so one would have been
    recorded and then never markable."""
    import weekly_swing as ws
    card = dict(CARD, ticker="SPY", legs="condor", structure="Iron condor",
                legs_detail=[
                    {"right": "P", "strike": 90.0, "buying": False, "qty": 1, "entry_price": 1.0},
                    {"right": "P", "strike": 85.0, "buying": True, "qty": 1, "entry_price": 0.4},
                    {"right": "C", "strike": 110.0, "buying": False, "qty": 1, "entry_price": 1.4},
                    {"right": "C", "strike": 115.0, "buying": True, "qty": 1, "entry_price": 0.8}],
                is_debit=False, net=-1.2, max_risk_usd=380.0)
    assert book.record([card]) == 1

    calls = chain([110.0, 115.0], lambda k: 0.5 if k == 110 else 0.2,
                  lambda k: 0.6 if k == 110 else 0.3)
    puts = chain([85.0, 90.0], lambda k: 0.1 if k == 85 else 0.3,
                 lambda k: 0.2 if k == 85 else 0.4)
    monkeypatch.setattr(ws, "_chain", lambda tk, exp: (calls, puts))
    monkeypatch.setattr(ws, "_hist", lambda tk: None)
    monkeypatch.setattr(book, "_market_open", lambda: False)

    res = book.mark()
    assert res["unmarked"] == 0
    assert book.open_book()[0]["cur_net"] is not None


# ===================================== ownership, exits, and render containment ===

def test_marking_a_card_entered_makes_it_owned_and_keeps_the_paper_card(book):
    """The ledger records every card for scoring; `owned` says which ones are real."""
    book.record([CARD])
    assert book.owned_book() == []
    res = book.mark_entered("NVDA", "2099-09-09")
    assert res["ok"] is True
    owned = book.owned_book()
    assert len(owned) == 1 and owned[0]["ticker"] == "NVDA"
    assert len(book.open_book()) == 1          # still one card, not two


def test_entering_a_card_that_does_not_exist_fails_loudly(book):
    res = book.mark_entered("ZZZZ", "2099-01-01")
    assert res["ok"] is False and "no open card" in res["why"]


def test_your_fill_price_is_used_when_you_give_one(book):
    book.record([CARD])
    book.mark_entered("NVDA", "2099-09-09", fill_net=2.00)   # card entry was 2.80
    o = book.owned_book()[0]
    assert o["fill_net"] == 2.00
    # Both keys always exist, even with no fill — a missing key rendered as Jinja Undefined,
    # which is `is not none`, and blanked the entire page to zero bytes.
    assert "pnl_pct_at_fill" in o and "pnl_usd_at_fill" in o


def test_the_fill_keys_exist_even_with_no_fill_price(book):
    book.record([CARD])
    book.mark_entered("NVDA", "2099-09-09")
    o = book.owned_book()[0]
    assert o["pnl_pct_at_fill"] is None and o["pnl_usd_at_fill"] is None


def test_exit_verdict_ranks_expiry_then_thesis_then_price(book):
    """Same order `mark()` closes on. A target hit after the reason died was luck."""
    base = {"expiry": "2099-09-09", "direction": "bullish", "is_debit": 1,
            "is_calendar": 0, "cur_net": 5.0, "cur_spot": 100.0,
            "inval_level": 90.0, "target_net": 6.0, "stop_net": 1.4,
            "close_early_dte": None}

    # expiry today outranks everything
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    v = book.exit_verdict({**base, "expiry": today}, live=True)
    assert v["action"] == "CLOSE" and "expires today" in v["why"]

    # thesis broken outranks a target that is also hit
    v = book.exit_verdict({**base, "cur_spot": 80.0, "cur_net": 9.0}, live=True)
    assert v["action"] == "CLOSE" and "no longer" not in v["why"]
    assert "90" in v["why"]

    # target with the thesis intact
    v = book.exit_verdict({**base, "cur_net": 7.0}, live=True)
    assert v["action"] == "TAKE PROFIT"

    # stop
    v = book.exit_verdict({**base, "cur_net": 1.0}, live=True)
    assert v["action"] == "CLOSE" and "stop" in v["why"]

    # between the levels
    assert book.exit_verdict(base, live=True)["action"] == "HOLD"


def test_no_exit_is_signalled_on_an_after_hours_mark(book):
    base = {"expiry": "2099-09-09", "direction": "bullish", "is_debit": 1,
            "is_calendar": 0, "cur_net": 5.0, "cur_spot": 100.0,
            "inval_level": 90.0, "target_net": 6.0, "stop_net": 1.4,
            "close_early_dte": None}
    v = book.exit_verdict(base, live=False)
    assert v["action"] == "HOLD" and "market is shut" in v["why"]


def test_credit_structure_thresholds_are_positive(book):
    """The bug that closed a profitable DELL credit spread as a 'stop' on entry.

    `net` is signed cash and negative for a credit, so thresholds derived from it were
    negative while the mark is compared as |cur_net|. `mark >= stop` was trivially true.
    """
    import weekly_swing as ws
    trend = {"lo20": 90.0, "hi20": 120.0}
    credit = {"is_debit": False, "net": -4.18, "width": None, "short_strike": 105.0}
    e = ws._exits(credit, trend, "bullish", 100.0, None)
    assert e["target_net"] > 0 and e["stop_net"] > 0
    assert e["stop_net"] > e["target_net"]          # buy back at 2x the credit, not 0.45x

    # ...and it must not fire on the entry mark.
    row = {"is_debit": 0, "is_calendar": 0, "direction": "bullish", "expiry": "2099-09-09",
           "cur_net": -4.30, "cur_spot": 100.0, "inval_level": 90.0,
           "target_net": e["target_net"], "stop_net": e["stop_net"], "close_early_dte": None}
    assert book.exit_verdict(row, live=True)["action"] == "HOLD"


def test_a_vertical_reports_its_width_so_it_manages_on_width(book):
    v = wst.assemble("call_debit",
                     [("C", 100.0, True, 1), ("C", 110.0, False, 1)],
                     lambda right, k, buying: (
                         {"strike": k, "price": 6.0 if k == 100 else 2.0,
                          "spread_pct": 2.0, "half_spread": 0.05, "oi": 500,
                          "buying": buying, "iv": 30.0}, None),
                     max_cost_pct=50.0)[0]
    assert v["width"] == 10.0

    # A straddle has no single width and must report None rather than a wrong number.
    st = wst.assemble("long_straddle",
                      [("C", 100.0, True, 1), ("P", 100.0, True, 1)],
                      lambda right, k, buying: (
                          {"strike": k, "price": 3.0, "spread_pct": 2.0,
                           "half_spread": 0.05, "oi": 500, "buying": buying, "iv": 30.0},
                          None),
                      max_cost_pct=50.0)[0]
    assert st["width"] is None


def test_a_broken_panel_template_cannot_blank_the_page():
    """`safe` guards a panel FUNCTION; nothing guarded its TEMPLATE.

    A missing dict key raised inside Jinja and /markets served ZERO BYTES — the exact
    HTTP-000 failure the panel contract exists to stop, one layer below where it reached.
    """
    import dashboard_app as app

    class Boom:
        def render(self, **kw):
            raise ValueError("no attribute 'nope'")

    out = app._render_panel(Boom(), {"key": "weekly_book", "title": "Ledger"})
    assert "template failed to render" in out
    assert "ValueError" in out
    assert "Ledger" in out
    assert "is-unavailable" in out


def test_the_universe_spans_every_sector_and_all_cap_tiers():
    """It was 24 tech-heavy names: a single-sector bet with a diversification story."""
    import weekly_swing as ws
    sectors = {s for s, _c in ws.UNIVERSE_META.values() if s.startswith("XL")}
    caps = {c for _s, c in ws.UNIVERSE_META.values()}
    assert len(ws.UNIVERSE) >= 90
    assert len(sectors) >= 11, sectors
    assert {"large", "mid", "small"} <= caps


def test_a_theme_naming_a_sector_vehicle_reaches_names_in_that_sector():
    """Themes name ETFs, not GICS codes. Without this, 90 of 103 names are unreachable."""
    import weekly_swing as ws
    overlay = {"ok": True, "as_of": "2026-09-02 14:00 ET", "regime_line": "x",
               "themes": [{"key": "ai", "label": "AI", "stance": "favour",
                           "favours": ["SMH"], "why": "chips"}],
               "notes_ingested": [{"date": "2026-09-02 13:30", "subject": "n"}]}
    v = ws._macro_view(overlay, "AAPL")          # XLK, never named directly
    assert v["side"] == 1
    assert v["inherited"] is True
    assert "INHERITED" in v["why"]

    # A sector no theme mentions stays unreachable.
    assert ws._macro_view(overlay, "JPM")["side"] == 0


def test_the_weekly_trend_read_actually_discriminates():
    """Four tech names in one theme used to return +0.35, +0.35, +0.34, +0.34.

    With the macro theme also flat across a sector, the vote had nothing left to rank on
    and every card looked interchangeable.
    """
    import numpy as np
    import pandas as pd
    import weekly_swing as ws

    def series(drift):
        n = 300
        c = pd.Series(100 * np.cumprod(1 + np.full(n, drift)))
        return pd.DataFrame({"close": c, "high": c * 1.01, "low": c * 0.99})

    scores = [ws._trend(series(d))["score"] for d in (-0.002, 0.0, 0.001, 0.003)]
    assert scores == sorted(scores)                       # monotone in drift
    assert max(scores) - min(scores) > 0.8, scores        # and genuinely spread


def test_insider_buys_do_not_saturate_at_three():
    """`min(n/3, 1)` maxed out at three buys, so five of six cards carried +0.25."""
    import math
    vals = [math.tanh(n / 6.0) for n in (1, 3, 6, 12, 40)]
    assert vals == sorted(vals)
    assert len({round(v, 2) for v in vals[:4]}) == 4       # the useful range varies
    assert vals[0] < 0.25 < vals[2]


def test_an_inherited_theme_votes_at_half_strength(monkeypatch):
    """A theme naming the ticker outright is stronger evidence than one taken via sector."""
    import weekly_swing as ws
    monkeypatch.setattr(ws, "_yf", lambda: (_ for _ in ()).throw(RuntimeError("no net")))
    named = ws.votes_for("NVDA", +1, {"score": 0.0}, None, inherited=False)
    inherited = ws.votes_for("NVDA", +1, {"score": 0.0}, None, inherited=True)
    dm = lambda v: next(d["contribution"] for d in v["detail"] if d["input"] == "desk_macro")
    assert dm(named) > dm(inherited) > 0


# ================================== a trade needs more than two things agreeing ===

def test_a_card_with_no_macro_theme_is_refused_outright(overlay):
    """Reversed on purpose. It was briefly a handicap so every sector could be covered.

    The 2026-09-04 16:02 cycle showed why that was wrong: JNJ and NEM shipped with ZERO
    themes on a single voting input — trend — which is exactly the pure-technicals card the
    rewrite existed to remove. Sector coverage is not worth a card with nothing behind it.
    """
    assert ws.REQUIRE_MACRO_BASIS is True
    view = ws._macro_view(overlay, "JNJ")
    assert view["no_macro_basis"] is True
    assert view["stand_down"] and "not a trade" in view["stand_down"]
    direction, why, _ = ws._decide(
        view, {"score": 0.9, "m60": 20.0},
        {"score": 0.9, "detail": [], "n_inputs": 1, "unmeasured_share": 0.0,
         "agreement": 1.0})
    assert direction is None


def _vote(pairs, score):
    """A vote whose detail carries one entry per (input, contribution)."""
    return {"score": score, "n_inputs": len(pairs), "unmeasured_share": 0.2,
            "agreement": 1.0,
            "detail": [{"input": n, "contribution": c, "value": c, "weight": 0.35,
                        "tier": "measured", "sign": "+"} for n, c in pairs]}


def test_two_inputs_agreeing_is_not_enough(overlay):
    """`desk_macro` and `trend` are the only always-available voters.

    A card resting on those two is the macro read plus a moving average, and `agreement`
    cannot detect it — one input agreeing with itself is 100%.
    """
    view = ws._macro_view(overlay, "NVDA")
    assert view["side"] == 1
    v = _vote([("desk_macro", 0.35), ("trend", 0.19)], 0.54)
    direction, why, _ = ws._decide(view, {"score": 0.5, "m60": 20.0}, v)
    assert direction is None
    assert "at least" in why and "corroborating" in why


def test_one_input_is_refused_even_at_a_huge_score(overlay):
    view = ws._macro_view(overlay, "NVDA")
    direction, why, _ = ws._decide(view, {"score": 0.9, "m60": 40.0},
                                   _vote([("trend", 0.9)], 0.9))
    assert direction is None
    assert "1 input(s)" in why


def test_three_agreeing_inputs_clears_it(overlay):
    view = ws._macro_view(overlay, "NVDA")
    v = _vote([("desk_macro", 0.35), ("trend", 0.19), ("flow_lean", 0.12)], 0.40)
    direction, why, _ = ws._decide(view, {"score": 0.4, "m60": 20.0}, v)
    assert direction == "bullish"


def test_inputs_that_disagree_do_not_count_toward_the_three(overlay):
    view = ws._macro_view(overlay, "NVDA")
    v = _vote([("desk_macro", 0.35), ("trend", 0.19),
               ("flow_lean", -0.11), ("dp_buy_share", -0.08)], 0.35)
    direction, why, _ = ws._decide(view, {"score": 0.35, "m60": 20.0}, v)
    assert direction is None
    assert "point that way" in why


def test_the_backing_list_always_leads_with_the_macro_pillar():
    view = {"themes": [{"label": "AI monetizers", "why": "chips deliver"}],
            "inherited": False, "why": "x"}
    v = _vote([("desk_macro", 0.35), ("trend", 0.19), ("flow_lean", 0.12)], 0.40)
    trend = {"w4": 3.0, "w12": 10.0, "rs12": 4.0, "rsi": 55, "from_hi": -5.0}
    out = ws._backing(view, v, trend, "confirmed", [], False, None, "normal", "why")
    assert out[0]["kind"] == "macro"
    # desk_macro is the macro pillar and must not also appear as a signal row.
    assert not any(b["label"] == "desk macro" for b in out)
    assert any(b["kind"] == "tape" for b in out)
    assert len(out) >= 4


def test_staleness_is_counted_in_sessions_not_hours():
    """A Friday note read on Sunday is still the current read — nothing happened between.

    Gating on wall-clock hours blanked the weekly book every weekend, and on 2026-09-06 it
    did exactly that: a Friday-afternoon note refused as stale on the Sunday.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    friday = {"notes_ingested": [{"date": "2026-09-04 11:53"}]}

    sunday = datetime(2026, 9, 6, 12, 0, tzinfo=et)
    assert desk_notes.sessions_since_newest(friday, now=sunday) == 0

    # By Tuesday, Monday's session has come and gone with no note.
    tuesday = datetime(2026, 9, 8, 17, 0, tzinfo=et)
    assert desk_notes.sessions_since_newest(friday, now=tuesday) >= 2
    assert desk_notes.sessions_since_newest(friday, now=tuesday) > desk_notes.MAX_MISSED_SESSIONS


def test_an_abstaining_voter_does_not_dilute_the_score():
    """`vix_backwardation` votes 0.0 in contango (weight 0.30) and insider votes 0.0 when
    there are no recent buys. Counting them in the DENOMINATOR while they add nothing to the
    numerator dragged every score toward zero — 24% dead weight measured on 2026-09-06, so a
    name genuinely at +0.41 was served as +0.31, and the book fell from six cards to one.
    """
    import signal_weights as sw
    live = {"desk_macro": 1.0, "trend": 0.55}
    with_abstainers = {**live, "vix_backwardation": 0.0, "insider_open_buys": 0.0}
    assert sw.combine(live)["score"] == sw.combine(with_abstainers)["score"]

    # A voter that actually disagrees MUST still count.
    disagreeing = {**live, "vix_backwardation": -1.0}
    assert sw.combine(disagreeing)["score"] < sw.combine(live)["score"]


def test_a_straddle_price_is_not_a_one_sigma_move():
    """The bug that made every fairly-priced name read EXPAND and killed the condor.

    straddle/S ~= sqrt(2/pi) * sigma*sqrt(T) = 0.798 * sigma*sqrt(T). Comparing the raw
    straddle against a one-sigma realised move biases the ratio down ~20%: IV == RV scored
    0.80, under the 0.85 expand threshold, while COMPRESS needed 1.25 — a 57% vol premium
    almost nothing clears. Measured 2026-09-06: WFC's true IV/RV was 1.34, reading "normal".
    """
    import math
    import weekly_swing as ws
    assert abs(ws.STRADDLE_TO_SIGMA - math.sqrt(2 / math.pi)) < 1e-9
    assert 0.79 < ws.STRADDLE_TO_SIGMA < 0.80

    # A fairly-priced name (implied sigma == realised over the horizon) must read NEITHER
    # expand nor compress.
    rv, dte = 30.0, 5
    horizon = rv * math.sqrt(dte / 252)
    view, why = ws.move_view(100.0, horizon, rv, dte, None, False, None, "AAPL")
    assert view == "normal", (view, why)

    # And the straddle PRICE for that same name would have been 0.798 * horizon, which under
    # the old comparison read "expand".
    stale_view, _ = ws.move_view(100.0, horizon * ws.STRADDLE_TO_SIGMA, rv, dte,
                                 None, False, None, "AAPL")
    assert stale_view == "expand"


def test_the_scan_never_stampedes_a_vendor():
    """12 workers returned HTTP 429 from Unusual Whales and 401 crumb errors from Yahoo,
    producing ZERO cards in one minute instead of six. Fast and wrong is worse than slow."""
    import weekly_swing as ws
    assert ws.SCAN_WORKERS <= 8
    assert ws._UW_GATE._value <= 2      # concurrent vendor calls, whatever the worker count
    assert ws._YF_GATE._value <= 4


def test_a_neutral_event_card_is_not_judged_by_the_directional_floor():
    """The conflict that kept condors, butterflies and straddles from ever firing.

    `MIN_CONVICTION` asks "does the evidence point strongly ONE WAY". A dated event with no
    directional side is SUPPOSED to score near zero — that is what neutral means. KR scored
    +0.05 on a real earnings date five days out and was refused for lacking conviction it
    never claimed, so every structure branch requiring `direction == "neutral"` was dead code.
    """
    import weekly_swing as ws
    view = {"side": 0, "themes": [{"label": "KR reports in 5 day(s)", "why": "x"}],
            "why": "x", "neutral": True, "stand_down": None,
            "event": {"label": "KR earnings", "date": "2026-09-11", "days_away": 5}}
    vote = {"score": 0.05, "n_inputs": 4, "unmeasured_share": 0.2, "agreement": 0.5,
            "detail": [{"input": "trend", "contribution": 0.05}]}

    # A decisive volatility read: neutral is returned, and the directional floor is not applied.
    d, why, _ = ws._decide(view, {"score": 0.05, "m60": 1.0}, vote, move="expand")
    assert d == "neutral", why
    assert "HOW FAR, not which way" in why

    # No directional view AND no volatility view is genuinely nothing.
    d, why, _ = ws._decide(view, {"score": 0.05, "m60": 1.0}, vote, move="normal")
    assert d is None
    assert "no volatility view" in why


def test_a_derived_basis_is_never_presented_as_a_desk_theme():
    """Derived and written bases flow through identical code, so the flag is the only thing
    keeping an inference from reading as a statement."""
    import market_basis as mb
    b = mb.derive("ZZZZ_NOT_A_TICKER", "XLU", y10_5d=0.0)
    assert b is None                      # no event, no rate move -> no basis invented

    # A real rate move against a measured beta does produce one, and it is flagged.
    b = mb.derive("ZZZZ_NOT_A_TICKER", "XLRE", y10_5d=0.90)
    assert b and b["derived"] is True
    assert b["side"] == -1                # XLRE's measured beta to the 10y is NEGATIVE
    assert all("derived" in t["basis"] for t in b["themes"])


def test_sector_rotation_is_not_a_derived_basis():
    """"Utilities are leading, so favour utilities" is the thing measured worse than random
    (1,512 configs, picks at p=0.867). It must appear nowhere as a reason to trade."""
    import pathlib
    src = pathlib.Path(__file__).parent.parent / "04_live_system" / "market_basis.py"
    body = src.read_text().split('"""', 2)[-1]        # skip the module docstring
    for banned in ("relative_strength", "rotation_score", "leaders", "laggards"):
        assert banned not in body, banned


def test_a_harmless_macro_event_cannot_mask_a_dangerous_one(monkeypatch):
    """The Labor Day defect, 2026-09-06.

    `_pick_weekly` used to `return` on the FIRST macro event it could clear. The first one in
    the list was "Labor Day — US markets closed" at +1d, which the 2026-09-11 expiry cleared
    trivially, so the function returned "clears Labor Day with 4 days left to work" and never
    looked at the August CPI print landing at 08:30 ON that same expiry. Five of six cards
    were routed onto CPI morning by the rule whose entire purpose is to prevent that.

    Hazards do not take turns. Every event in the window has to be judged, not the first one
    that happens to be satisfiable.
    """
    monkeypatch.setattr(ws, "_expiries", lambda tk: ["2026-09-11", "2026-09-18"])
    monkeypatch.setattr(ws, "_dte", lambda e: {"2026-09-11": 5, "2026-09-18": 12}[e])
    events = [
        {"label": "Labor Day — US markets closed", "date": "2026-09-07", "days_away": 1},
        {"label": "August CPI", "date": "2026-09-11", "days_away": 5},
    ]
    exp, _dte, why = ws._pick_weekly("BAC", [], events)
    assert exp != "2026-09-11", f"routed onto CPI day again: {why}"
    assert "Labor Day" not in why or "CPI" in why


def test_a_clean_expiry_is_the_shortest_one_not_the_longest(monkeypatch):
    """Extra time past a cleared print is theta and exposure, not safety."""
    monkeypatch.setattr(ws, "_expiries", lambda tk: ["2026-09-11", "2026-09-18"])
    monkeypatch.setattr(ws, "_dte", lambda e: {"2026-09-11": 9, "2026-09-18": 16}[e])
    exp, _dte, _why = ws._pick_weekly(
        "QQQ", [], [{"label": "payrolls", "date": "2026-09-04", "days_away": 2}])
    assert exp == "2026-09-11"
