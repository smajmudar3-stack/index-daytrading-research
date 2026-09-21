"""pead.py — post-earnings drift, the one weekly-horizon voter that measured with its
published sign in every split.

02_findings/weekly_predictors.md, 2026-09-21: across 1,845 names and 344 weeks of real
chains, the sign of the earnings-day move, taken within 14 sessions of the print, ranked the
next 5/10/21-day return at IC +0.018 / +0.039 / +0.034 (t +1.8 / +2.6 / +2.2), positive in
all three time splits. Small -- it sits below the multiple-testing bar on its own -- and
registered in `signal_weights` at 0.10 because that is the size it measured, not the size
Bernard & Thomas (1989) quote for a quarterly hold on small caps.

THE VOTE IS THE SIGN OF THE MOVE, NOT ITS SIZE. A +12% print and a +3% print are both "the
market liked it"; scaling the vote to the move would let one name's blowout dominate the
book. tanh(move / 4%) saturates gently so a 2% move votes ~0.46 and anything past 8% votes
~1.0. Outside the 14-session window the voter ABSTAINS (exactly 0.0), which `combine()`
excludes from the denominator, so a name with no recent print is judged on the rest.

The report date comes from Unusual Whales `/api/earnings/{t}` (report_date; the closes it
carries are NULL, so the move is read from the price history the scan already holds). One
call per name, cached for the run.
"""
import math
from datetime import datetime, timedelta

WINDOW_SESSIONS = 14      # measured window: the drift is a two-week effect at most here
SCALE = 0.04              # tanh(move / 4%)

_CACHE = {}


def last_report_date(ticker, now=None):
    """The most recent report date at or before today, or None. Never raises."""
    if ticker in _CACHE:
        return _CACHE[ticker]
    out = None
    try:
        import uw_client
        if uw_client.available():
            rows = uw_client._rows(uw_client._get(f"/api/earnings/{ticker}")) or []
            today = (now or datetime.now()).date()
            dates = []
            for r in rows:
                d = str(r.get("report_date") or "")[:10]
                try:
                    dd = datetime.strptime(d, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if dd <= today:
                    dates.append((dd, (r.get("report_time") or "").lower()))
            if dates:
                out = max(dates)
    except Exception:                                         # noqa: BLE001
        out = None
    _CACHE[ticker] = out
    return out


def score(px, report, now=None):
    """Vote in [-1, +1] from the price history and (report_date, report_time).

    The move is close-to-close ACROSS the print: for an after-close report, the close of the
    report day to the close of the next session; for a pre-market report, the prior close to
    the report day's close. Returns 0.0 (abstain) when the print is older than the window or
    the bars around it are missing.
    """
    if px is None or report is None or "close" not in px:
        return {"score": 0.0, "basis": "no report date"}
    rdate, rtime = report
    idx = [d.date() if hasattr(d, "date") else d for d in px.index]
    closes = list(px["close"].astype(float))
    after = [i for i, d in enumerate(idx) if d > rdate]
    on = [i for i, d in enumerate(idx) if d == rdate]
    before = [i for i, d in enumerate(idx) if d < rdate]
    premarket = rtime.startswith("pre") or rtime in ("bmo", "before")
    if premarket:
        if not on or not before:
            return {"score": 0.0, "basis": "bars around the print are missing"}
        i0, i1 = before[-1], on[0]
    else:
        if not after or not (on or before):
            return {"score": 0.0, "basis": "bars around the print are missing"}
        i0, i1 = (on[0] if on else before[-1]), after[0]
    sessions_since = len(idx) - 1 - i1
    if sessions_since > WINDOW_SESSIONS:
        return {"score": 0.0, "basis": f"last print {sessions_since} sessions ago, outside the "
                                       f"{WINDOW_SESSIONS}-session window"}
    if closes[i0] <= 0:
        return {"score": 0.0, "basis": "bad close"}
    move = closes[i1] / closes[i0] - 1
    return {"score": round(math.tanh(move / SCALE), 3), "move_pct": round(move * 100, 2),
            "report_date": rdate.isoformat(), "sessions_since": sessions_since,
            "basis": f"{move*100:+.1f}% across the {rdate} print, {sessions_since} sessions ago"}


def for_ticker(ticker, px, now=None):
    return score(px, last_report_date(ticker, now=now), now=now)


def _test_dates(now=None):      # for tests: clear the per-run cache
    _CACHE.clear()
    return (now or datetime.now()).date() - timedelta(days=1)
