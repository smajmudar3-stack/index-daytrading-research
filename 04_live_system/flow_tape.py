"""flow_tape.py — the data lake, and a deliberate refusal to fit anything to it yet.

WHY THIS EXISTS
===============
Four of the seven voters in `weekly_swing` come from Unusual Whales: flow lean, dark-pool buy
share, short float and insider open buys. `signal_weights` tiers all four "unmeasured" and says
outright that their weight is a PRIOR taken from the literature, not a measurement, because the
endpoints serve today's number and keep no history. There is nothing to backtest against.

That is the single largest hole in this system. `flow_lean` carries the heaviest weight of any
input (0.40) on the strength of Johnson & So (2012) and nothing this repo has verified.

A data lake fixes it the only way it can be fixed: by writing down what the endpoints said,
every day, until there is enough history to test the claim. `earnings_vrp_test.py` was possible
solely because two volatility endpoints happen to serve a year of history; this recorder gives
the other four the same footing, forward rather than backward.

THE DISCIPLINE THAT MAKES THIS SAFE RATHER THAN DANGEROUS
=========================================================
A recorded flow history is also the perfect instrument for fooling yourself. The temptation, as
soon as a few weeks accumulate, is to fit weights to it -- and with seven inputs, a few hundred
observations and a free hand, a model that explains the sample beautifully and predicts nothing
is not a risk, it is the expected outcome. This repo has the receipts: 1,512 sector-rotation
configurations, none better than buy-and-hold; a trend composite whose IC flipped sign across
three consecutive splits; a calibration file that once carried an IC of 0.62.

So this module RECORDS AND DOES NOT FIT. It writes a daily row per name and computes nothing.
Two rules are enforced rather than merely intended:

  MIN_DAYS_TO_MEASURE   no study may run against this until the lake spans this many sessions
  MIN_EVENTS_TO_WEIGHT  no weight may move on it until this many forward outcomes exist

`ready()` returns the honest answer and `study_guard()` refuses on behalf of any caller that
asks too early. The point of writing them down now, months before they can be used, is that
the thresholds get set while there is no result to be tempted by.

WHAT IS RECORDED
================
One row per ticker per session, holding the same five raw numbers `votes_for` reads, plus the
spot price so a forward return can be computed later without a second data source. Raw values
only -- never the vote, never the weighted score. A vote is an interpretation, and storing an
interpretation means a future study measures this code's opinion instead of the market's data.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from idt import db, paths                                      # noqa: E402

ET = ZoneInfo("America/New_York")
DBFILE = "flow_tape.db"

# A cross-sectional signal needs a run of history before its information coefficient means
# anything. Sixty sessions is roughly a quarter -- short, and stated as a floor rather than a
# target. Set here, before any result exists to argue with.
MIN_DAYS_TO_MEASURE = 60
MIN_EVENTS_TO_WEIGHT = 400

SCHEMA = """
CREATE TABLE IF NOT EXISTS flow (
  d TEXT NOT NULL, ticker TEXT NOT NULL,
  spot REAL, flow_lean REAL, dp_buy_share REAL, short_float_pct REAL,
  insider_score REAL, iv_rank REAL, vrp REAL,
  PRIMARY KEY (d, ticker)
);
CREATE INDEX IF NOT EXISTS flow_ticker ON flow(ticker);
CREATE INDEX IF NOT EXISTS flow_date ON flow(d);
"""


def _path():
    return os.path.join(paths.STATE_ROOT, DBFILE)


def _conn():
    c = db.connect(_path()) if hasattr(db, "connect") else sqlite3.connect(_path())
    c.executescript(SCHEMA)
    return c


def record(rows, day=None):
    """Write one session's raw readings. `rows` is [{ticker, spot, flow_lean, ...}].

    Idempotent on (date, ticker): a second scan the same session overwrites rather than
    double-counting, because two rows for one name on one day would silently weight it twice
    in any cross-sectional average built later.
    """
    d = (day or datetime.now(ET).date()).isoformat() if not isinstance(day, str) else day
    cols = ("spot", "flow_lean", "dp_buy_share", "short_float_pct",
            "insider_score", "iv_rank", "vrp")
    n = 0
    with _conn() as c:
        for r in rows or []:
            tk = (r.get("ticker") or "").upper()
            if not tk:
                continue
            vals = []
            for k in cols:
                v = r.get(k)
                try:
                    vals.append(float(v) if v is not None else None)
                except (TypeError, ValueError):
                    vals.append(None)
            if all(v is None for v in vals[1:]):
                continue          # spot alone is not a flow observation
            c.execute(
                f"INSERT OR REPLACE INTO flow (d, ticker, {','.join(cols)}) "
                f"VALUES (?,?,{','.join('?' * len(cols))})", [d, tk, *vals])
            n += 1
    return n


def span():
    """(n_sessions, n_rows, first_day, last_day)."""
    try:
        with _conn() as c:
            r = c.execute("SELECT COUNT(DISTINCT d), COUNT(*), MIN(d), MAX(d) "
                          "FROM flow").fetchone()
        return tuple(r) if r else (0, 0, None, None)
    except sqlite3.Error:
        return (0, 0, None, None)


def ready():
    """Whether the lake is deep enough to measure. Returns (bool, explanation).

    Deliberately conservative and deliberately written now, while there is no result to be
    tempted by. A signal that looks strong after three weeks of data is the single most
    reliable way this repo has found to lose money.
    """
    days, rows, first, last = span()
    if days < MIN_DAYS_TO_MEASURE:
        return False, (f"{days} of {MIN_DAYS_TO_MEASURE} sessions recorded ({rows} rows"
                       + (f", {first} to {last}" if first else "") + "). Not enough history "
                       "to measure an information coefficient that would mean anything. The "
                       "weights stay at their literature priors until it is.")
    return True, (f"{days} sessions, {rows} rows, {first} to {last}. Deep enough to measure — "
                  f"and note that measuring is still not the same as re-weighting: "
                  f"`signal_weights` bands any calibration to 0.25-2.5x the prior and rejects "
                  f"an |IC| above 0.15 outright.")


def study_guard():
    """Raise unless the lake is deep enough. For any study that reads this table.

    A guard rather than a comment, because a comment saying "do not fit this yet" is advice and
    this repo has learned to prefer gates. Seven of its trading gates used to return "allow" on
    an exception; every one of them now fails closed.
    """
    ok, why = ready()
    if not ok:
        raise RuntimeError(f"flow_tape is not ready to be studied: {why}")
    return why


def series(ticker, field="flow_lean"):
    """[(date, value)] for one name, oldest first. For a study, once `ready()` allows it."""
    if field not in ("flow_lean", "dp_buy_share", "short_float_pct",
                     "insider_score", "iv_rank", "vrp", "spot"):
        raise ValueError(f"unknown field {field!r}")
    with _conn() as c:
        return [(d, v) for d, v in c.execute(
            f"SELECT d, {field} FROM flow WHERE ticker=? AND {field} IS NOT NULL "
            f"ORDER BY d", (ticker.upper(),))]


def snapshot_summary():
    """A dict for the dashboard panel. Never raises."""
    try:
        days, rows, first, last = span()
        ok, why = ready()
        with _conn() as c:
            names = c.execute("SELECT COUNT(DISTINCT ticker) FROM flow").fetchone()[0]
            recent = c.execute("SELECT d, COUNT(*) FROM flow GROUP BY d "
                               "ORDER BY d DESC LIMIT 5").fetchall()
        return {"sessions": days, "rows": rows, "names": names, "first": first, "last": last,
                "ready": ok, "why": why, "recent": [{"d": d, "n": n} for d, n in recent],
                "min_days": MIN_DAYS_TO_MEASURE}
    except Exception as e:                                    # noqa: BLE001
        return {"sessions": 0, "rows": 0, "names": 0, "ready": False,
                "why": f"could not read the tape: {type(e).__name__}: {e}",
                "recent": [], "min_days": MIN_DAYS_TO_MEASURE}


if __name__ == "__main__":
    print(json.dumps(snapshot_summary(), indent=2))
