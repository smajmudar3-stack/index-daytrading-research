"""earnings_vrp_test.py — does an expensive option into earnings actually lose?

THE QUESTION. `04_live_system/earnings_vol.py` reads a name's variance risk premium against
its own year and says a high percentile "argues for SELLING the event". That is a plausible
story. This repo's whole method is that a plausible story is worth nothing until it is
measured, and the file that tells the story says so itself.

WHY THIS ONE IS TESTABLE WHEN THE REST OF THE UNUSUAL WHALES VOTE IS NOT
=======================================================================
`flow_lean`, `dp_buy_share` and `insider_open_buys` are served SAME-DAY only. There is no
history, so `signal_weights` tiers them "unmeasured" and says their weight is a prior that can
only be earned forward. That is honest and it is also a dead end: most of the vote cannot be
backtested even in principle.

Two endpoints break that pattern:

    /api/stock/{t}/volatility/variance-risk-premium   ~232 rows, a year of daily premium
    /api/earnings/{t}                                 ~107 rows, PAST reports carrying
                                                      pre_earnings_close, post_earnings_close
                                                      and the realised reaction

So the natural experiment is available: for each past report, where did the premium sit
beforehand, and how did the actual move compare to what was implied?

WHAT IS BEING MEASURED
======================
For every historical earnings date with a readable premium in the days before it:

    implied      the expected move the market priced going in
    realised     |post_earnings_close / pre_earnings_close - 1|
    edge         implied - realised, in points. POSITIVE means the seller won.

Then the only question that matters: does the premium percentile BEFORE the print sort those
outcomes? If rich-percentile events show a materially better seller edge than cheap ones, the
signal is real. If the buckets look alike, `earnings_vol` produces a description and not a
signal, and it must not carry weight in the vote.

WHAT THIS CANNOT SETTLE
=======================
One year of history and one report per quarter means roughly four observations per name. The
sample is built ACROSS names, so it inherits every cross-sectional problem that comes with
that -- a handful of high-vol names can dominate. The t-stats here are weak evidence by
construction and are reported as such. `signal_weights.IC_IMPLAUSIBLE` exists because a
calibration file in this repo once carried an IC of 0.62; anything that looks too good in this
output is a bug, and the first place to look is whether `expected_move_perc` is being read as
a fraction (it is a fraction: 0.0761 means 7.6%).
"""
import os
import statistics
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "04_live_system")
# Explicit rather than a loop: `verify.py`'s import-time-work check flags any `for` at module
# level, because a study that does work on import cannot be safely imported by the gate.
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if LIVE not in sys.path:
    sys.path.insert(0, LIVE)

# How many sessions before the report to read the premium from. The trade is put on before the
# print, so the premium must be the one visible THEN -- reading it on the day of the report
# would be lookahead, the same error that made the gap-and-go study report +1.25%/trade when
# the truth was -0.33%.
LOOKBACK_SESSIONS = 2


def _rows(ep, params=None):
    import uw_client
    if not uw_client.available():
        return None
    try:
        return uw_client._rows(uw_client._get(ep, params or {}))
    except Exception:                                         # noqa: BLE001
        return None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def premium_series(ticker):
    """[(date, premium)] sorted ascending, or []."""
    out = []
    for r in _rows(f"/api/stock/{ticker}/volatility/variance-risk-premium") or []:
        d, p = str(r.get("date") or "")[:10], _f(r.get("risk_premium"))
        if d and p is not None:
            out.append((d, p))
    out.sort()
    return out


def events(ticker, closes=None):
    """Past reports with a usable implied move and a realised reaction.

    THE REALISED MOVE IS COMPUTED FROM PRICE HISTORY, NOT READ OFF THE ENDPOINT.
    `/api/earnings/{t}` carries `report_date` and `expected_move_perc` but leaves
    `pre_earnings_close` and `post_earnings_close` NULL, including on reports that already
    happened -- only the date-keyed `/api/earnings/premarket|afterhours` populate them. Reading
    them here returned zero usable events for all 90 names, which is the silent-zero failure
    this repo keeps paying for: indistinguishable from "no earnings edge exists".

    So the implied move comes from Unusual Whales and the realised move comes from the daily
    closes already batched for the scan. One UW call per name, no extra price calls.
    """
    out = []
    for r in _rows(f"/api/earnings/{ticker}") or []:
        d = str(r.get("report_date") or "")[:10]
        em = _f(r.get("expected_move_perc"))
        if not d or em is None:
            continue
        realised = _realised_move(closes, d)
        if realised is None:
            continue
        # FRACTION, NOT PERCENT. 0.0761 is a 7.6% move.
        implied = em * 100.0
        out.append({"ticker": ticker, "date": d, "implied": implied,
                    "realised": realised, "edge": implied - realised})
    return out


def _realised_move(closes, report_date):
    """|move| across the report, in points, from daily closes. None when not covered.

    The report date is the SESSION THE COMPANY REPORTS, which may be before or after the bell.
    Taking the close before it and the close after it captures the gap either way; taking the
    same-day move would miss an after-hours print entirely.
    """
    if closes is None or len(closes) < 2:
        return None
    try:
        idx = [str(i)[:10] for i in closes.index]
        after = [k for k, day in enumerate(idx) if day > report_date]
        before = [k for k, day in enumerate(idx) if day < report_date]
        if not after or not before:
            return None
        pre, post = float(closes.iloc[before[-1]]), float(closes.iloc[after[0]])
        if pre <= 0:
            return None
        return abs(post / pre - 1.0) * 100.0
    except Exception:                                         # noqa: BLE001
        return None


def with_percentile(ticker, closes=None):
    """Each past report tagged with the premium percentile visible BEFORE it."""
    series = premium_series(ticker)
    if len(series) < 60:
        return []
    out = []
    for ev in events(ticker, closes=closes):
        prior = [(d, p) for d, p in series if d < ev["date"]]
        if len(prior) < 60:
            continue
        # The premium as of a couple of sessions before the print, ranked against everything
        # known at that moment -- never against the full year, which would include the future.
        idx = max(0, len(prior) - LOOKBACK_SESSIONS)
        latest = prior[idx][1]
        hist = [p for _d, p in prior[:idx + 1]]
        if len(hist) < 60:
            continue
        ev["pctile"] = sum(1 for p in hist if p <= latest) / len(hist)
        ev["premium"] = latest
        out.append(ev)
    return out


def _stats(rows, key="edge"):
    vals = [r[key] for r in rows]
    if len(vals) < 2:
        return {"n": len(vals)}
    m = statistics.mean(vals)
    sd = statistics.pstdev(vals) or 1e-9
    return {"n": len(vals), "mean": m, "median": statistics.median(vals),
            "t": m / (sd / (len(vals) ** 0.5)),
            "win": sum(1 for v in vals if v > 0) / len(vals)}


def run(tickers, verbose=True):
    """Batch the price history once, then one UW call per name."""
    import weekly_swing as ws
    if verbose:
        print(f"  prefetching {len(tickers)} price histories...", flush=True)
    ws._prefetch(list(tickers))
    rows = []
    for i, tk in enumerate(tickers, 1):
        px = ws._HIST_CACHE.get(tk)
        got = with_percentile(tk, closes=px["close"] if px is not None else None)
        rows += got
        if verbose and i % 20 == 0:
            print(f"  ... {i}/{len(tickers)} names, {len(rows)} events", flush=True)
    return rows


def report(rows):
    if not rows:
        print("no usable events — Unusual Whales unavailable, or no overlapping history")
        return
    print(f"\n{len(rows)} earnings events across "
          f"{len({r['ticker'] for r in rows})} names\n")

    a = _stats(rows)
    print("ALL EVENTS — seller edge = implied move minus realised move, in points")
    print(f"  mean {a['mean']:+.2f}pt   median {a['median']:+.2f}pt   "
          f"t {a['t']:+.2f}   seller wins {a['win']:.0%}   n {a['n']}")
    print("  (a positive mean means options into earnings were, on average, too expensive —\n"
          "   this is the well-documented variance risk premium and is NOT the claim on test)")

    print("\nTHE CLAIM ON TEST — does the premium percentile BEFORE the print sort outcomes?")
    buckets = [("cheap  <=25%", lambda p: p <= 0.25),
               ("mid 25-75%", lambda p: 0.25 < p < 0.75),
               ("rich   >=75%", lambda p: p >= 0.75)]
    got = {}
    for name, f in buckets:
        sub = [r for r in rows if f(r["pctile"])]
        s = _stats(sub)
        got[name] = s
        if s.get("n", 0) < 2:
            print(f"  {name:<12} n={s.get('n',0)} — too few to say anything")
            continue
        print(f"  {name:<12} mean {s['mean']:+6.2f}pt   median {s['median']:+6.2f}pt   "
              f"t {s['t']:+5.2f}   seller wins {s['win']:.0%}   n {s['n']:4}")

    r_, c_ = got.get("rich   >=75%", {}), got.get("cheap  <=25%", {})
    print()
    if r_.get("n", 0) >= 20 and c_.get("n", 0) >= 20:
        spread = r_["mean"] - c_["mean"]
        print(f"  rich minus cheap: {spread:+.2f}pt")
        if abs(spread) < 0.5:
            print("  VERDICT: the percentile does NOT sort the outcomes. `earnings_vol` is\n"
                  "  describing the pricing, not predicting it — it must not carry weight in\n"
                  "  the vote, and the card should say the event is dated and stop there.")
        elif spread > 0:
            print("  VERDICT: rich premiums did show a better seller edge. Weak evidence —\n"
                  "  check the t-stat and the bucket sizes before letting it carry weight,\n"
                  "  and remember one year gives ~4 reports per name.")
        else:
            print("  VERDICT: BACKWARDS. Cheap premiums showed the better seller edge, which\n"
                  "  is the opposite of what `earnings_vol` tells the user. Fix or remove it.")
    else:
        print("  VERDICT: not enough events in the tails to judge. Widen the universe.")


if __name__ == "__main__":
    from weekly_swing import UNIVERSE
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    names = [t for t in UNIVERSE if t.isalpha()][:n]
    print(f"earnings VRP test — {len(names)} names, "
          f"premium read {LOOKBACK_SESSIONS} sessions before each report")
    print(f"started {datetime.now():%H:%M:%S}", flush=True)
    report(run(names))
