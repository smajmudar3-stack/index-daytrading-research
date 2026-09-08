"""market_basis.py — the dashboard deriving its own basis, for the sectors nobody wrote about.

THE PROBLEM THIS SOLVES. `weekly_swing` requires a macro basis before it will propose
anything, and that basis comes from the Crown desk notes. Those notes are cross-asset macro:
rates, oil, the dollar, gold, banks, refiners, software. Eleven notes over five days reached
five of eleven sectors. Materials, communications, industrials, staples, utilities and health
were refused on arrival -- 123 of 283 names -- not because they were unattractive but because
nobody happened to write about them.

Waiting for a newsletter to mention utilities is not an analysis strategy. This module derives
a basis from data instead.

WHAT COUNTS AS A BASIS, AND WHAT DELIBERATELY DOES NOT
======================================================
The bar is the same one the desk themes clear: a specific, checkable reason this name is worth
looking at THIS week. Two things clear it.

  1. A DATED EVENT INSIDE THE EXPIRY WINDOW. An earnings date is objective, sector-agnostic,
     and the single best reason to hold a weekly option. It is available for every name in
     every sector, which is exactly what the desk notes are not.

  2. MEASURED RATE EXPOSURE. This repo measured sector betas to the 10y on 20 years of daily
     changes and they are stable: KRE +1.09, XLF +0.95, XLRE -0.24 (the only negative). With
     an actual 5-day yield move, that is a MECHANICAL statement about what a position is
     levered to -- not a forecast. The repo already tiers `rate_beta` as a risk flag at 0.05
     for precisely this reason: the exposure is real, the PREDICTION failed (216 cells, zero
     cleared the bar).

WHAT DOES NOT COUNT: sector rotation. "Utilities are leading, so favour utilities" is the
thing this repo measured as WORSE THAN RANDOM (1,512 configurations, none beat buy-and-hold,
picks at p=0.867). Relative strength appears nowhere in this module as a reason to trade.

AN EARNINGS DATE IS NOT A DIRECTION, AND THIS IS THE POINT
==========================================================
A dated event predicts that a LARGE MOVE WILL RESOLVE. It says nothing about which way.
`uw_endpoints` already tiers `fda_date` as "structural" with exactly that wording, and the
same logic applies here.

So a card built on an event basis gets `direction = "neutral"`, which has a useful second
effect: neutral was previously unreachable -- `_decide` always returned bullish or bearish
from the sign of the vote -- and the iron condor, iron butterfly and long straddle branches
of the structure menu all require it. They have never once been able to fire. An event basis
is the honest route to them: no directional view, a dated reason to expect movement, and the
term structure decides whether you buy that movement or sell it.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ET = ZoneInfo("America/New_York")

# Measured on 20 years of daily changes; see signal_weights and macro_panel. Stable, and the
# sign is the whole content: rising yields HELP financials and HURT real estate.
RATE_BETA = {
    "KRE": 1.09, "XLF": 0.95, "XLI": 0.35, "XLB": 0.30, "XLE": 0.25,
    "XLK": -0.10, "XLC": -0.05, "XLY": -0.15, "XLP": -0.18,
    "XLV": -0.12, "XLU": -0.22, "XLRE": -0.24,
}

# A yield move smaller than this is noise, not an exposure worth naming.
RATE_MOVE_MIN_PT = 0.08          # 8bp over 5 sessions
EVENT_WINDOW_DAYS = 16           # must land inside the weekly expiry window to matter


def _today():
    return datetime.now(ET).date()


def next_earnings(ticker, calendar=None):
    """The next earnings date, preferring a prebuilt bulk calendar.

    `calendar` is `{TICKER: {...}}` from `earnings_vol.calendar()`, which covers the whole
    forward window in about two Unusual Whales calls per session covered. Without it this
    falls back to a per-ticker lookup, which cost 1,550 yfinance round trips a scan for a
    fact that changes once a quarter.
    """
    if calendar is not None:
        row = calendar.get(ticker.upper())
        if not row:
            return None
        try:
            return datetime.strptime(str(row["date"])[:10], "%Y-%m-%d").date()
        except (ValueError, KeyError, TypeError):
            return None
    return _next_earnings_slow(ticker)


def _next_earnings_slow(ticker):
    """The next earnings date for a name, or None. Never raises.

    yfinance first: it costs no Unusual Whales quota, and the scan already holds a yfinance
    session for this ticker. UW's `next_earnings_date` is the fallback, read off the insider
    feed the scan fetches anyway rather than spending a separate call.
    """
    try:
        import yfinance as yf
        cal = yf.Ticker(ticker).calendar
        if isinstance(cal, dict):
            d = cal.get("Earnings Date")
            if isinstance(d, list) and d:
                d = d[0]
            if d is not None:
                return d if isinstance(d, type(_today())) else d.date()
    except Exception:                                         # noqa: BLE001
        pass
    try:
        import uw_client
        if uw_client.available():
            rows = uw_client._rows(uw_client._get(
                "/api/insider/transactions", {"ticker_symbol": ticker, "limit": 1}))
            for r in rows or []:
                v = r.get("next_earnings_date")
                if v:
                    return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:                                         # noqa: BLE001
        pass
    return None


def rate_exposure(sector, y10_5d):
    """What a 5-day yield move mechanically does to this sector. Exposure, not forecast."""
    beta = RATE_BETA.get(sector)
    if beta is None or y10_5d is None or abs(y10_5d) < RATE_MOVE_MIN_PT:
        return None
    drift = beta * y10_5d
    if abs(drift) < 0.15:
        return None
    return {
        "beta": beta, "y10_5d": y10_5d, "drift_pct": round(drift, 2),
        "why": (f"the 10y moved {y10_5d:+.2f}pt over five sessions and this sector's MEASURED "
                f"beta to it is {beta:+.2f}, a mechanical {drift:+.1f}% of drift. Twenty "
                f"years of daily changes; the exposure is stable, the PREDICTION is not — "
                f"216 cells were tested and none cleared the bar, so this sizes and frames a "
                f"trade, it never justifies one on its own."),
    }


def y10_change_5d():
    """The 5-session change in the 10y, in points. None when unreadable."""
    try:
        import yfinance as yf
        s = yf.download("^TNX", period="1mo", interval="1d", progress=False,
                        auto_adjust=False, multi_level_index=False)["Close"].dropna()
        if len(s) < 6:
            return None
        # ^TNX IS ALREADY IN PERCENT on this feed: it prints 4.784 for a 4.784% yield, not
        # 47.84. Dividing by ten understated every yield move by an order of magnitude and
        # made the rate-exposure branch permanently unreachable — a 6.4bp week read as 0.6bp
        # and never cleared the 8bp floor. Same class of error as comparing a straddle price
        # to a one-sigma move: the number was right, the units were not.
        return float(s.iloc[-1] - s.iloc[-6])
    except Exception:                                         # noqa: BLE001
        return None


def derive(ticker, sector, y10_5d=None, now=None, calendar=None, vrp_hint=None):
    """A data-derived basis for one name, or None if the data gives no reason to look.

    Returns the same shape `weekly_swing` expects from a desk theme, so a derived basis and a
    written one flow through identical code -- with `derived: True` so a card can never
    present one as the other.
    """
    today = (now or datetime.now(ET)).date()
    themes, side, event = [], 0, None

    d = next_earnings(ticker, calendar=calendar)
    if d is not None:
        days = (d - today).days
        if 0 <= days <= EVENT_WINDOW_DAYS:
            event = {"date": d.isoformat(), "days_away": days,
                     "label": f"{ticker} earnings"}
            # THE MEASURED PART. An earnings date on its own says a move will resolve and
            # nothing else; it is a reason to look, not a reason to trade. What decides
            # whether to BUY that move or SELL it is the variance risk premium, and unlike the
            # rest of the Unusual Whales vote that one has a history and has been measured:
            # 266 events, rich-percentile premiums showed a +3.63pt seller edge against
            # -4.30pt for cheap ones, monotone, holding in all three period splits, with
            # implied flat across buckets so it is forecasting the realised move rather than
            # labelling expensive prices. See 02_findings/earnings_vrp.md.
            #
            # It attaches to the STRUCTURE and never to `side`. The finding is about the SIZE
            # of a move; treating it as directional would be inventing a claim the measurement
            # does not make.
            # DEFERRED ON PURPOSE. `vrp()` is an Unusual Whales call, and basis derivation
            # runs for every name in a 1,550-name universe. Calling it here contributed to 48
            # HTTP 429s on the first wide scan, which starved 325 names of their flow, dark
            # pool and insider inputs and refused them for "only 2 inputs" — a rate limit
            # wearing the costume of a market condition. The caller passes `vrp` in once the
            # name has actually earned the expense.
            vol = vrp_hint
            if vol:
                lean = {"rich": "sell the event", "cheap": "buy the event",
                        "fair": "no volatility view"}[vol["verdict"]]
                extra = (f" The premium sits at the {vol['pctile']:.0%} percentile of this "
                         f"name's own year, which argues to {lean}. Measured: rich premiums "
                         f"showed a +3.63pt seller edge against -4.30pt for cheap ones across "
                         f"266 events, holding in all three period splits.")
            else:
                extra = (" No readable volatility history for this name, so the event is "
                         "dated and the pricing carries no view.")
            themes.append({
                "key": "dated_event",
                "label": f"{ticker} reports in {days} day(s)",
                "stance": "watch",
                "why": (f"Earnings on {d.isoformat()}, inside the expiry window. A dated event "
                        f"predicts that a LARGE MOVE WILL RESOLVE — it says nothing about "
                        f"which way, so this is a basis for a volatility structure and not "
                        f"for a directional one." + extra),
                "basis": "derived from the earnings calendar, not from a desk note",
                "vrp": vol,
            })

    rx = rate_exposure(sector, y10_5d)
    if rx:
        themes.append({
            "key": "rate_exposure",
            "label": (f"{sector} carries a {'positive' if rx['beta'] > 0 else 'negative'} "
                      f"measured beta to the 10y"),
            "stance": "favour" if rx["drift_pct"] > 0 else "avoid",
            "why": rx["why"],
            "basis": "derived from this repo's measured 20-year sector rate betas",
        })
        side = 1 if rx["drift_pct"] > 0 else -1

    if not themes:
        return None
    return {
        "themes": themes, "side": side, "event": event, "derived": True,
        "why": " ".join(t["why"] for t in themes),
        # An event with no rate view is explicitly NON-directional, which is what makes the
        # condor / butterfly / straddle branches reachable at all.
        "neutral": event is not None and side == 0,
        # Surfaced at the top level so the structure menu can read it without walking themes.
        # `None` default, not a bare next(): a rate-exposure basis carries no dated event, so
        # the generator is legitimately empty and StopIteration would take the whole card down.
        "vol_lean": next(((t.get("vrp") or {}).get("verdict")
                          for t in themes if t["key"] == "dated_event"), None),
    }


if __name__ == "__main__":
    import weekly_swing as ws
    y = y10_change_5d()
    print(f"10y 5-session change: {y:+.3f}pt\n" if y is not None else "10y unreadable\n")
    dark = ["JNJ", "PG", "CAT", "LIN", "NEE", "T", "MRK", "UPS", "KO", "DUK"]
    for tk in dark:
        sec = ws.SECTOR_OF.get(tk)
        b = derive(tk, sec, y10_5d=y)
        if not b:
            print(f"  {tk:5} {str(sec):5} — no derived basis")
            continue
        kinds = ", ".join(t["key"] for t in b["themes"])
        print(f"  {tk:5} {str(sec):5} side={b['side']:+d} neutral={b['neutral']}  [{kinds}]"
              + (f"  event {b['event']['date']} (+{b['event']['days_away']}d)"
                 if b["event"] else ""))
