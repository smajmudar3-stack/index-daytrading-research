"""earnings_vol.py — the earnings volatility scan, and the first UW signal with a history.

WHAT THIS IS FOR. Two separate problems, one source.

  1. THE NEUTRAL STRUCTURES HAVE NEVER FIRED. The iron condor, iron butterfly and long
     straddle branches of `weekly_structures.menu()` all require `direction == "neutral"`, and
     until `market_basis` landed nothing could produce one. An earnings date is the honest
     route to neutral -- a dated event says a LARGE MOVE WILL RESOLVE and says nothing about
     which way -- but "there is an earnings date" is not on its own a reason to trade. The
     term structure has to say whether that move is worth buying or worth selling.

  2. EARNINGS DATES COST TOO MUCH TO FETCH. `market_basis.next_earnings` calls yfinance once
     per ticker. At 283 names that was tolerable; at 1,550 it is 1,550 round trips for a fact
     that changes about once a quarter. `/api/earnings/premarket` and `/api/earnings/afterhours`
     take a DATE and return every company reporting that session, so the whole forward calendar
     costs about two calls per day covered.

WHY THE VARIANCE RISK PREMIUM MATTERS MORE THAN THE REST OF IT
=============================================================
Every Unusual Whales input this engine already uses -- `flow_lean`, `dp_buy_share`,
`insider_open_buys` -- is served SAME-DAY ONLY. There is no history, so `signal_weights` tiers
them "unmeasured" and says outright that their weight is a prior which can only be earned
forward. That is an honest position and a frustrating one: it means most of the vote cannot be
backtested even in principle.

`/api/stock/{t}/volatility/variance-risk-premium` returns 232 rows. `/volatility/realized`
returns 252, with implied AND realized side by side. These are HISTORIES. Whether a rich
premium into earnings actually predicts anything is therefore a measurable question rather than
a plausible story, and `05_studies/earnings_vrp_test.py` is where it gets answered.

Nothing here claims an edge. This module produces a measurement and a clearly-labelled prior;
the weight it earns comes from the study, not from this file.
"""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ET = ZoneInfo("America/New_York")

# How far ahead to walk the earnings calendar. Matches the weekly expiry window so a name is
# only picked up when its report can actually land inside a tradable expiry.
CALENDAR_DAYS = 18

# A variance risk premium is the gap between what options imply and what the stock went on to
# do. Positive means options were expensive. These are percentile cuts on a name's OWN year of
# history, not absolute levels: "expensive for this stock" is the only comparison that means
# anything across a 1,550-name universe of very different vol regimes.
RICH_PCTILE = 0.75
CHEAP_PCTILE = 0.25


def _rows(ep, params=None):
    try:
        import uw_client
        if not uw_client.available():
            return None
        return uw_client._rows(uw_client._get(ep, params or {}))
    except Exception:                                         # noqa: BLE001
        return None


def calendar(days=CALENDAR_DAYS, now=None):
    """Every company reporting in the next `days` sessions: {TICKER: {...}}.

    Two calls per session covered, against one per ticker for the yfinance route. Weekend
    dates are skipped rather than requested: companies do not report on a Sunday, and the
    empty response costs the same as a real one.
    """
    today = (now or datetime.now(ET)).date()
    out = {}
    for i in range(days + 1):
        d = today + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        for ep, when in (("/api/earnings/premarket", "premarket"),
                         ("/api/earnings/afterhours", "afterhours")):
            for r in _rows(ep, {"date": d.isoformat()}) or []:
                tk = (r.get("ticker") or r.get("symbol") or "").upper()
                if not tk or not r.get("has_options"):
                    continue
                # `expected_move_perc` ARRIVES AS A FRACTION, and as a string: "0.0761" means
                # a 7.6% move, not 0.076%. Rendered raw it read "the market is pricing a 0.1%
                # move" for every name reporting, which is absurd on its face for an earnings
                # print and is the same units error that made ^TNX understate every yield move
                # tenfold and made a straddle price look like a one-sigma move. The number was
                # right; the units were not. This repo has now paid for that mistake three
                # times, which is why it is called out here rather than quietly corrected.
                try:
                    em = float(r["expected_move_perc"]) * 100.0 if r.get("expected_move_perc") \
                        else None
                except (TypeError, ValueError):
                    em = None
                # marketcap arrives as a STRING on this endpoint. Sorting on it unconverted
                # raised a TypeError; coercing it silently to 0 would have been worse, since
                # every name would then have ranked identically and the ordering would have
                # looked deliberate.
                try:
                    cap = float(r["marketcap"]) if r.get("marketcap") else None
                except (TypeError, ValueError):
                    cap = None
                out.setdefault(tk, {
                    "ticker": tk, "date": d.isoformat(), "days_away": (d - today).days,
                    "when": when, "expected_move_pct": em,
                    "marketcap": cap, "name": r.get("full_name"),
                })
    return out


def vrp(ticker):
    """Where this name's variance risk premium sits in its OWN year. None when unreadable.

    Returns the latest premium, its percentile against that history, and a verdict. An
    absolute premium is uninterpretable across a wide universe -- a utility and a biotech do
    not carry comparable numbers -- so everything here is relative to the ticker itself.
    """
    rows = _rows(f"/api/stock/{ticker}/volatility/variance-risk-premium")
    if not rows or len(rows) < 60:
        return None
    vals = []
    for r in rows:
        try:
            vals.append((str(r.get("date")), float(r["risk_premium"])))
        except (TypeError, ValueError, KeyError):
            continue
    if len(vals) < 60:
        return None
    vals.sort(key=lambda x: x[0])
    series = [v for _d, v in vals]
    latest = series[-1]
    pct = sum(1 for v in series if v <= latest) / len(series)
    if pct >= RICH_PCTILE:
        verdict, why = "rich", ("options are expensive against this name's own year of "
                                "implied-vs-realised history")
    elif pct <= CHEAP_PCTILE:
        verdict, why = "cheap", ("options are cheap against this name's own year of "
                                 "implied-vs-realised history")
    else:
        verdict, why = "fair", "the premium is unremarkable for this name"
    return {"premium": round(latest, 4), "pctile": round(pct, 3), "verdict": verdict,
            "n": len(series), "why": why}


def scan(tickers=None, days=CALENDAR_DAYS, now=None, max_names=60):
    """Names reporting inside the window, ranked by how extreme their vol premium is.

    The calendar is walked first and the per-name volatility history is fetched only for what
    it returns -- a handful of names a day, not the universe. That ordering is the whole
    reason this is affordable, and it is the same discipline the main scan uses: cheap gates
    before paid ones.
    """
    cal = calendar(days=days, now=now)
    if tickers is not None:
        keep = {t.upper() for t in tickers}
        cal = {k: v for k, v in cal.items() if k in keep}
    ranked = sorted(cal.values(), key=lambda r: (r["days_away"], -(r.get("marketcap") or 0)))
    out = []
    for row in ranked[:max_names]:
        v = vrp(row["ticker"])
        if v is None:
            row["vrp"] = None
            row["read"] = "no readable volatility history — no vol view, event only"
        else:
            row["vrp"] = v
            row["read"] = _read(v, row.get("expected_move_pct"))
        out.append(row)
    return out


def _read(v, expected_move_pct):
    """What the premium argues for, in the engine's own vocabulary.

    Deliberately phrased as a structure preference and not as a direction. An earnings date is
    a statement that a move will resolve, never a statement about its sign, and every place
    this repo has blurred those two has cost it money.
    """
    em = f" The market is pricing a {expected_move_pct:.1f}% move." if expected_move_pct else ""
    if v["verdict"] == "rich":
        return (f"IV sits at the {v['pctile']:.0%} percentile of this name's own year — "
                f"{v['why']}. That argues for SELLING the event (condor, butterfly, credit "
                f"spread) rather than buying it.{em}")
    if v["verdict"] == "cheap":
        return (f"IV sits at the {v['pctile']:.0%} percentile of this name's own year — "
                f"{v['why']}. That argues for BUYING the event (straddle, calendar, debit "
                f"spread).{em}")
    return (f"IV is at the {v['pctile']:.0%} percentile of its own year, which is not a "
            f"volatility view. The event is dated; the pricing is unremarkable.{em}")


if __name__ == "__main__":
    rows = scan(max_names=int(sys.argv[1]) if len(sys.argv) > 1 else 25)
    if not rows:
        print("no companies with listed options reporting in the window "
              "(or Unusual Whales is unavailable)")
    for r in rows:
        v = r.get("vrp") or {}
        print(f"\n{r['ticker']:6} {r['date']} (+{r['days_away']}d, {r['when']})  "
              f"vrp={v.get('verdict','—'):5} pctile={v.get('pctile','—')}")
        print(f"   {r['read']}")
