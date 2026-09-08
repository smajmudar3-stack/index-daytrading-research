"""One scorecard for every tab: what it said, what happened, was it right.

Each panel already emits a call. Nothing was checking them afterwards, which
means conviction numbers were assertions rather than claims with a track record.
This records every call at the moment it is made, settles it when the horizon
closes, and reports per-tab accuracy.

THREE THINGS IT MEASURES, and the third is the one that matters most:

  HIT RATE   how often the direction was right
  EXPECTANCY average realised move in the called direction — because a 70% hit
             rate that wins small and loses big is a losing strategy, which is
             the exact trap the credit structures fell into
  CALIBRATION does a stated conviction of 70 actually win ~70% of the time?
             A panel that says 70 and hits 50 is not unlucky, it is miscalibrated,
             and that is fixable in a way that bad luck is not.

Settled results feed back into signal_weights, so a tab that keeps being wrong
loses influence over the combined score on its own.

WHY THE DB PATH AND THE PANEL GUARD LOOK PARANOID: on a fresh clone this module
raised `sqlite3.OperationalError: unable to open database file` because data/ did
not exist. gap_dashboard.render() interpolates panel() straight into an f-string
with no guard, so one missing directory returned the ENTIRE page as HTTP 000 and
zero bytes. The path now goes through idt.paths.state(), which creates the
directory, and panel() cannot raise at all.
"""
import sqlite3
import sys
from datetime import datetime, timezone

from idt import db as _db, paths

DB = paths.state("scorecard.db")

# Horizon each tab is judged over, in calendar days.
HORIZON = {"0dte": 1, "desk": 21, "swing": 21, "blackswan": 42,
           "tickets": 63}   # 63d = where the short-interest IC was measured


class ScorecardUnavailable(RuntimeError):
    """The scorecard database could not be opened or read.

    Deliberately different from an EMPTY scorecard. Empty means no call has been
    logged yet and the honest report is "nothing to show". Unavailable means the
    record exists and we cannot see it, and reporting that as "nothing to show"
    would hide a broken track record behind a clean-looking panel."""


def _warn(msg):
    print(f"[scorecard] WARNING: {msg}", file=sys.stderr)


def _con():
    """WAL, synchronous=NORMAL and a 15s busy timeout, via idt.db. scan_all writes
    this file on every 5-minute cycle while the dashboard reads it, and sqlite's
    default 5-second lock was the only thing between them."""
    try:
        c = _db.connect(DB)
        c.execute("""create table if not exists calls(
            id integer primary key autoincrement,
            ts text, tab text, ticker text, direction text,
            conviction real, structure text, entry_px real,
            horizon_days integer, note text,
            settled_ts text, exit_px real, move_pct real, correct integer)""")
        c.execute("create index if not exists ix_open on calls(settled_ts)")
        return c
    except (sqlite3.Error, OSError) as e:
        raise ScorecardUnavailable(f"{DB}: {type(e).__name__}: {e}") from e


def record(tab, ticker, direction, conviction=None, structure=None,
           entry_px=None, note=""):
    """Log a call at the moment it is made. Raises ScorecardUnavailable if the
    call could not be written: an unrecorded call is a silently missing row in
    the hit rate, which is the one number this file exists to keep honest."""
    if direction in (None, "", "neutral", "conflict"):
        return None          # a stand-down is not a prediction
    c = _con()
    try:
        # ONE CALL PER TAB/TICKER/DIRECTION PER DAY.
        # The scanner runs every 5 minutes, so without this the same standing call
        # is logged ~120 times a day. That does not just inflate the count -- it
        # corrupts the statistics, because one lucky call would be counted 120 times
        # in the hit rate. Re-stating a view is not a new prediction.
        from datetime import date as _date
        today = _date.today().isoformat()
        dup = c.execute(
            "select id from calls where tab=? and ticker=? and direction=? "
            "and substr(ts,1,10)=?", (tab, ticker, direction, today)).fetchone()
        if dup:
            # Keep the LATEST conviction for the day, but not a second row.
            c.execute("update calls set conviction=?, note=? where id=?",
                      (conviction, note, dup[0]))
            c.commit()
            return dup[0]

        cur = c.execute(
            "insert into calls(ts,tab,ticker,direction,conviction,structure,"
            "entry_px,horizon_days,note) values(?,?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), tab, ticker, direction,
             conviction, structure, entry_px, HORIZON.get(tab, 21), note))
        c.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        raise ScorecardUnavailable(f"could not record {tab}/{ticker} call: "
                                   f"{type(e).__name__}: {e}") from e
    finally:
        c.close()


def settle(price_fn=None):
    """Close out any call whose horizon has passed. Returns the number settled.

    Rows are skipped for two very different reasons and they are no longer
    treated the same: a call whose window is still open is expected and silent,
    while a call we CANNOT settle (no price history for the ticker, not enough
    bars) is reported on stderr. A call that can never be settled sits in the
    pending count forever and quietly flatters the record by staying unjudged."""
    import pandas as pd
    c = _con()
    try:
        rows = c.execute(
            "select id,ts,tab,ticker,direction,entry_px,horizon_days "
            "from calls where settled_ts is null").fetchall()
        if not rows:
            return 0

        if price_fn is None:
            import warnings, yfinance as yf
            warnings.filterwarnings("ignore")

            def price_fn(tks, start):
                px = yf.download(list(tks), start=start, progress=False,
                                 auto_adjust=True, threads=False)
                px = px["Close"] if "Close" in px else px
                return px.to_frame() if hasattr(px, "to_frame") and px.ndim == 1 else px

        tickers = sorted({r[3] for r in rows})
        start = min(pd.Timestamp(r[1]).tz_localize(None) for r in rows) - pd.Timedelta(days=5)
        px = price_fn(tickers, start.strftime("%Y-%m-%d"))

        n = 0
        unsettleable = []
        now = pd.Timestamp.utcnow().tz_localize(None)
        for cid, ts, tab, tk, direction, entry, hz in rows:
            t0 = pd.Timestamp(ts).tz_localize(None)
            if (now - t0).days < hz:
                continue                              # window still open
            if tk not in getattr(px, "columns", []):
                unsettleable.append(f"{tab}/{tk}#{cid}: no price history returned")
                continue
            s = px[tk].dropna()
            after = s[s.index >= t0]
            if len(after) < 2:
                unsettleable.append(f"{tab}/{tk}#{cid}: fewer than 2 bars after the call")
                continue
            e = float(entry) if entry else float(after.iloc[0])
            later = after[after.index >= t0 + pd.Timedelta(days=hz)]
            if later.empty:
                unsettleable.append(f"{tab}/{tk}#{cid}: no bar at or after the horizon")
                continue
            x = float(later.iloc[0])
            move = (x - e) / e * 100
            # "Right" means the market moved the way the call said.
            correct = int((move > 0) if direction == "bullish" else (move < 0))
            c.execute("update calls set settled_ts=?,exit_px=?,move_pct=?,correct=? "
                      "where id=?",
                      (datetime.now(timezone.utc).isoformat(), x, move, correct, cid))
            n += 1
        c.commit()
        if unsettleable:
            _warn(f"{len(unsettleable)} call(s) past their horizon could not be settled and stay "
                  f"pending: {'; '.join(unsettleable[:5])}"
                  + (f" (+{len(unsettleable) - 5} more)" if len(unsettleable) > 5 else ""))
        return n
    except sqlite3.Error as e:
        raise ScorecardUnavailable(f"could not settle calls: {type(e).__name__}: {e}") from e
    finally:
        c.close()


def report():
    """Per-tab accuracy, expectancy and calibration.

    An empty dict means no call has ever been logged. That is a real answer and
    callers should say so out loud. If the database itself cannot be read this
    raises ScorecardUnavailable rather than returning {}, because the two used to
    be indistinguishable and only one of them is fine."""
    c = _con()
    try:
        out = {}
        for (tab,) in c.execute("select distinct tab from calls").fetchall():
            rows = c.execute(
                "select direction,conviction,move_pct,correct from calls "
                "where tab=? and settled_ts is not null", (tab,)).fetchall()
            pend = c.execute("select count(*) from calls where tab=? and settled_ts is null",
                             (tab,)).fetchone()[0]
            if not rows:
                out[tab] = {"settled": 0, "pending": pend}
                continue
            n = len(rows)
            hit = sum(r[3] for r in rows) / n
            # Expectancy is signed BY the call, so a correct bearish call is a gain.
            exp = sum((r[2] if r[0] == "bullish" else -r[2]) for r in rows) / n
            # Calibration: high-conviction calls should win more than low ones.
            hi = [r for r in rows if (r[1] or 0) >= 60]
            lo = [r for r in rows if (r[1] or 0) < 60]
            out[tab] = {
                "settled": n, "pending": pend,
                "hit_rate": round(hit * 100, 1),
                "expectancy_pct": round(exp, 3),
                "hi_conv_hit": round(sum(r[3] for r in hi) / len(hi) * 100, 1) if hi else None,
                "lo_conv_hit": round(sum(r[3] for r in lo) / len(lo) * 100, 1) if lo else None,
                "calibrated": (round(sum(r[3] for r in hi) / len(hi) * 100, 1) >
                               round(sum(r[3] for r in lo) / len(lo) * 100, 1))
                              if (hi and lo) else None,
            }
        return out
    except sqlite3.Error as e:
        raise ScorecardUnavailable(f"could not read the scorecard: {type(e).__name__}: {e}") from e
    finally:
        c.close()


_STYLE = """
<style>
 #score table{width:100%;border-collapse:collapse;font-size:12px;margin-top:9px}
 #score th{text-align:right;padding:5px 7px;color:rgba(128,128,128,.75);
   font-weight:600;border-bottom:1px solid rgba(128,128,128,.16)}
 #score th:first-child{text-align:left}
 #score td{padding:4px 7px;text-align:right;font-variant-numeric:tabular-nums;
   border-bottom:1px solid rgba(128,128,128,.07)}
 #score td:first-child{text-align:left;font-weight:600}
 #score .g{color:#16a34a} #score .r{color:#dc2626}
 #score .mut{color:rgba(128,128,128,.7);text-align:left;font-size:11px}
 #score .sub{font-size:12px;color:rgba(128,128,128,.75);line-height:1.5}
 #score .foot{margin-top:10px;font-size:11px;color:rgba(128,128,128,.7);line-height:1.55}
 #score .bad{color:#dc2626;font-weight:600}
 #score code{font-size:11px;background:rgba(128,128,128,.12);padding:1px 4px;border-radius:3px}
</style>"""


def _card(title, body):
    return f"""
<section class="card" id="score">
  <h2>{title}</h2>
  {body}
{_STYLE}
</section>"""


def _unavailable_card(detail):
    """The scorecard is the track record. If it cannot be read, the page has to
    say that in the scorecard's own slot, because an absent panel reads as
    'nothing to report yet' and that is the opposite of what happened."""
    return _card("Scorecard &mdash; unavailable",
                 f'<div class="sub"><span class="bad">The track record could not be read.</span> '
                 f'Every number this panel would show is therefore unknown, not zero.</div>'
                 f'<div class="foot">{detail}<br>Database: <code>{DB}</code></div>')


def _empty_card():
    """A fresh clone has no calls at all. Naming the file and the command is the
    difference between 'this looks broken' and 'this has not run yet'."""
    return _card("Scorecard &mdash; nothing logged yet",
                 '<div class="sub">No call has been recorded, so there is no hit rate, no '
                 'expectancy and no calibration to show. This is the honest state of a system '
                 'that has not run, not a failure.</div>'
                 f'<div class="foot">Calls are written by the scanner. Run '
                 f'<code>venv/bin/python 04_live_system/scan_all.py</code> to record today\'s, '
                 f'then <code>venv/bin/python 04_live_system/scorecard.py</code> to settle any '
                 f'whose horizon has closed.<br>Database: <code>{DB}</code></div>')


def _rows_html(rep):
    rows = ""
    for tab, r in sorted(rep.items()):
        if not r.get("settled"):
            rows += (f"<tr><td>{tab}</td><td colspan=5 class=mut>"
                     f"no settled calls yet &middot; {r.get('pending',0)} pending</td></tr>")
            continue
        cal = r.get("calibrated")
        cal_txt = ("&#10003; yes" if cal else "&#10007; no") if cal is not None else "&mdash;"
        exp = r["expectancy_pct"]
        rows += (f"<tr><td>{tab}</td><td class=num>{r['settled']}</td>"
                 f"<td class=num>{r['hit_rate']:.0f}%</td>"
                 f"<td class='num {'g' if exp>0 else 'r'}'>{exp:+.2f}%</td>"
                 f"<td class=num>{r['hi_conv_hit'] if r['hi_conv_hit'] is not None else '—'}"
                 f"{'%' if r['hi_conv_hit'] is not None else ''}</td>"
                 f"<td class=num>{cal_txt}</td></tr>")
    return rows


def panel():
    """Render the scorecard for the dashboard. This function never raises.

    It is interpolated directly into gap_dashboard.render()'s f-string with no
    guard around it, so anything that escapes here takes the whole page with it:
    that is exactly how a fresh clone returned HTTP 000 and zero bytes. Every
    failure mode below renders as a card that says what went wrong."""
    try:
        rep = report()
    except Exception as e:
        _warn(f"report() failed: {type(e).__name__}: {e}")
        return _unavailable_card(f"{type(e).__name__}: {e}")
    if not rep:
        return _empty_card()
    try:
        rows = _rows_html(rep)
    except Exception as e:
        # A malformed row must cost one panel, not the page. The stats above are
        # computed here, so a shape change in report() lands here first.
        _warn(f"panel() could not render the rows: {type(e).__name__}: {e}")
        return _unavailable_card(f"rows could not be rendered: {type(e).__name__}: {e}")
    return f"""
<section class="card" id="score">
  <h2>Scorecard &mdash; how right each tab has been</h2>
  <div class="sub">Every call is logged when made and settled when its horizon
    closes. <b>Expectancy matters more than hit rate</b>: a 70% hit rate that wins
    small and loses big is a losing strategy &mdash; that is precisely how the
    credit structures failed.</div>
  <table>
    <thead><tr><th>tab</th><th>settled</th><th>hit rate</th><th>expectancy</th>
      <th>hi-conv hit</th><th>calibrated?</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="foot">Calibrated = calls stated at conviction &ge;60 actually win more
    often than those below it. A panel that says 70 and hits 50 is miscalibrated,
    not unlucky &mdash; and that is fixable. Settled results feed back into the
    weights, so a tab that keeps being wrong loses influence on its own.</div>
{_STYLE}
</section>"""


if __name__ == "__main__":
    import json as _j
    try:
        print("settled:", settle())
        print(_j.dumps(report(), indent=1))
    except ScorecardUnavailable as e:
        print(f"scorecard unavailable: {e}", file=sys.stderr)
        raise SystemExit(1) from e
