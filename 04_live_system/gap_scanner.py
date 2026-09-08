"""gap_scanner.py — the LIVE gap-and-go signal-giver (the validated edge).

Each morning it scans a universe of volatile stocks and names the ONE setup that measured
positive, with its direction:

  DOWN-GAP BOUNCE, LONG : gap down between -4% and -20% -> buy at open, flat at the close
                          +0.76%/trade net of 15bp, t = +5.45, n = 2,325
  GAP UP                : STAND ASIDE. Long measured -0.33% (t = -3.52), short +0.03%
                          (t = +0.35). Neither side is a trade.

THE PREVIOUS VERSION OF THIS FILE HAD IT BACKWARDS. It emitted "GAP-AND-GO LONG" on up-gaps,
which is the significantly negative side, and it gated the down-gap bounce behind an
RVOL >= 1.5 filter that destroys it (+0.71% -> -0.20%). That filter was also LOOKAHEAD: it
used today's full-day volume, which is unknown at the open when the trade is entered, and it
is where the old docstring's "+1.25%/trade t=6.6" came from. See
`05_studies/gap_direction_test.py` and the two 2026-09-03 entries in docs/VERDICT_LOG.md.

Writes data/gap_snapshot.json. Meant for PAPER TRADING first — accuracy shows up over many
trades, any single one is noise, and a 100bp round trip kills this edge outright.

Every scan reports how many names it could NOT fetch. A quote outage used to return "0 candidates of
0 scanned", which reads exactly like a calm market, and the paper record just skipped a day.
"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import yfinance as yf

from idt import db, paths

log = logging.getLogger("gap_scanner")

ET = ZoneInfo("America/New_York")
# Under STATE_ROOT, created on demand. Was HERE/"data" with a bare sqlite3 handle: no directory,
# no WAL, and a 5-second lock against scan_all writing the same file.
OUT = paths.state("gap_snapshot.json")
DB = paths.state("gap_track.db")
UNIV = ["TSLA","NVDA","AMD","COIN","MARA","RIOT","PLTR","SOFI","AFRM","UPST","RIVN","LCID",
        "NIO","GME","AMC","SMCI","ARM","MSTR","DKNG","ROKU","SNAP","PINS","SHOP","NET",
        "CVNA","W","CHWY","ABNB","DASH","U","RBLX","HOOD","PATH","AI","IONQ","PLUG","FCEL",
        "BBAI","SOUN","MU","AVGO","SNOW","CRWD","DDOG","ZS","PANW","DELL"]

# MEASURED 2026-09-03 by 05_studies/gap_direction_test.py on this exact universe, 47 names,
# 67,858 name-days, 2020-09 to 2026-09, net of 15bp round trip:
#
#   gap up   >3%, LONG   -0.33%/trade  t = -3.52   <- what this scanner used to emit as a BUY
#   gap up   >3%, SHORT  +0.03%/trade  t = +0.35   <- nothing; not a short either
#   gap down >4%, LONG   +0.71%/trade  t = +5.04   <- the one real edge
#   gap down >4%, SHORT  -1.01%/trade  t = -7.16
#
# THE OLD RVOL GATE WAS LOOKAHEAD. RVOL >= 1.5 computed from TODAY'S FULL-DAY volume turns
# the gap-up long into +1.07% at t = +5.39, which is where the docstring's "+1.25%, t=6.6"
# came from. You cannot know today's full-day volume at the open, which is when the trade is
# entered; conditioning on "today turned out to be a huge volume day" selects the days that
# trended. The same filter DESTROYS the real edge: the down-gap bounce goes from +0.71%
# (t=+5.04) to -0.20% (t=-0.72) once it is applied. So RVOL is now CONTEXT, never a gate.
#
# Depth banding replaces it, and unlike volume it IS knowable at the open:
#   -4 to -6%: +0.51%   -6 to -10%: +1.10%   -10 to -20%: +1.15%   beyond -20%: -1.08%
# Catastrophic gaps do not bounce, so the band is floored.
GAP_DN_MAX = -0.04     # at least this deep to qualify
GAP_DN_FLOOR = -0.20   # ...and no deeper
GAP_UP_MIN = 0.03      # retained only to LABEL up-gaps as stand-asides

# The measured expectancy of the one tradeable band, carried onto every candidate so the
# size of the claim is visible at the moment of reading it.
EDGE = {"band": "-4% to -20% gap down, long the open, flat at the close",
        "mean_pct": 0.76, "t": 5.45, "n": 2325, "win": 0.53,
        "note": ("+0.76%/trade net of 15bp over 2,325 trades, t=+5.45. Positive in both "
                 "halves of the sample (+1.03% then +0.39%) and in 30 of 44 names. "
                 "Survives to 50bp round trip; dead at 100bp. UNVERIFIED beyond this one "
                 "study — no VERDICT_LOG entry yet.")}

# Kept for the paper-track schema and for display only. NOT a gate.
GAP_UP, GAP_DN, RVOL_MIN = GAP_UP_MIN, GAP_DN_MAX, 1.5

# After this many failed attempts a logged candidate is reported as stuck instead of being retried
# forever in silence. A paper trade that never settles is a hole in the win rate, not a zero.
MAX_SETTLE_ATTEMPTS = 3

_MIGRATIONS = [("settle_attempts", "INT DEFAULT 0"), ("settle_error", "TEXT")]


def _conn():
    try:
        con = db.connect(DB)
    except sqlite3.Error as e:
        log.error("gap_scanner: cannot open the paper book at %s: %s", DB, e)
        raise
    con.execute("""CREATE TABLE IF NOT EXISTS paper(date TEXT, ticker TEXT, setup TEXT,
        gap REAL, rvol REAL, open REAL, close REAL, ret REAL, win INT,
        settle_attempts INT DEFAULT 0, settle_error TEXT,
        PRIMARY KEY(date,ticker))""")
    have = {r[1] for r in con.execute("PRAGMA table_info(paper)").fetchall()}
    for col, ddl in _MIGRATIONS:
        if col not in have:
            con.execute(f"ALTER TABLE paper ADD COLUMN {col} {ddl}")
    con.commit()
    return con


def _live_quote(tk):
    """Today's last print and cumulative volume, against the SAME CLOCK TIME on prior days.

    WHY THIS EXISTS. `scan_one` used to read `open.iloc[-1]` and `close.iloc[-2]` off DAILY
    bars. Before the open there is no bar for today, so `iloc[-1]` is YESTERDAY, and the
    scanner served yesterday's gap as today's setup every cycle until the open. On
    2026-09-03 at 06:47 that meant DELL was still listed as "GAP-AND-GO LONG, +8.72%" from
    its earnings pop the previous session, while the actual pre-market print was 484.29
    against a 492.20 close -- a gap of MINUS 1.6%. The panel looked frozen because it was
    re-deriving a stale gap, not because the file had stopped being written.

    THE SECOND BUG THIS FIXES. RVOL was today's cumulative volume over a 20-day average of
    FULL-DAY volume. Those are not comparable until the closing bell. DELL on 2026-09-02 was
    a genuine 6.3x volume day (36.6M against a 5.8M average), but at 09:45 -- when a
    "buy at open" trade is actually entered -- the 6.4M done so far against the 5.8M full-day
    average gives RVOL 1.1, under the 1.5 threshold. The setup could only confirm hours after
    the entry it was supposed to trigger. Comparing like for like, today's volume by 09:45
    against prior sessions' volume by 09:45, is valid at any hour of the day.

    Returns None when today has no prints at all, which is the correct answer on a weekend or
    a holiday and must not be confused with "no setups today".
    """
    try:
        m = yf.download(tk, period="7d", interval="1m", prepost=True, progress=False,
                        multi_level_index=False)
    except Exception:                                         # noqa: BLE001
        return None
    if m is None or not len(m):
        return None
    m = m.rename(columns=str.lower)
    if m.index.tz is None:
        m.index = m.index.tz_localize("UTC")
    m.index = m.index.tz_convert(ET)

    today = datetime.now(ET).date()
    cur = m[m.index.date == today]
    if not len(cur):
        return None

    price = float(cur["close"].iloc[-1])
    vol = float(cur["volume"].sum())
    cutoff = cur.index[-1].time()

    # Baseline: cumulative volume by the SAME clock time on the prior sessions in the window.
    # NOTE: this feed reports ZERO volume on pre-market bars. That is a real limitation, not
    # a bug to code around -- before the open there is no volume to compare, so `rvol` comes
    # back None and no setup can be named. Saying "unknown" is correct; inventing a ratio
    # from a zero denominator is not.
    prior = []
    for _day, g in m[m.index.date != today].groupby(m[m.index.date != today].index.date):
        upto = g[g.index.time <= cutoff]
        if len(upto):
            prior.append(float(upto["volume"].sum()))
    baseline = float(np.median(prior)) if prior else None
    return {"price": price, "volume": vol, "baseline_volume": baseline,
            "n_baseline_sessions": len(prior), "cutoff": cutoff.strftime("%H:%M"),
            "as_of": cur.index[-1].strftime("%Y-%m-%d %H:%M ET")}


def scan_one(tk):
    d = yf.download(tk, period="2mo", interval="1d", progress=False, auto_adjust=False,
                    multi_level_index=False).rename(columns=str.lower)
    if d is None or len(d) < 21:
        return None

    # IS THE NEWEST DAILY BAR ACTUALLY TODAY'S? Everything below turns on this question and
    # the old code never asked it.
    today = datetime.now(ET).date()
    newest = d.index[-1].date()
    intraday = newest == today

    q = _live_quote(tk)
    if intraday:
        prev_close = float(d["close"].iloc[-2])
        today_open = float(d["open"].iloc[-1])
        last = float(q["price"]) if q else float(d["close"].iloc[-1])
        premarket = False
        quote_as_of = q["as_of"] if q else f"{newest} daily bar"
    else:
        # Pre-market (or a non-session day). The last daily bar IS the previous close, and
        # today's price has to come from a live print rather than a bar that does not exist.
        if q is None:
            return None                       # no prints today: not a session, not a setup
        prev_close = float(d["close"].iloc[-1])
        today_open = None                     # there is no open yet, and inventing one lies
        last = q["price"]
        premarket = True
        quote_as_of = q["as_of"]

    # ONE RVOL, TIME-OF-DAY AWARE, used in both states. Falls back to the full-day average
    # only when the minute feed is unavailable, and says so via `rvol_basis`.
    if q and q["baseline_volume"]:
        rvol = q["volume"] / q["baseline_volume"]
        rvol_basis = f"vs prior sessions by {q['cutoff']} ({q['n_baseline_sessions']} days)"
    elif intraday:
        avg_vol = float(d["volume"].iloc[-21:-1].mean())
        tv = float(d["volume"].iloc[-1])
        rvol = tv / avg_vol if avg_vol > 0 else None
        rvol_basis = "vs 20-day FULL-DAY average — understated before the close"
    else:
        rvol = None                           # unknown, and unknown is not zero
        rvol_basis = "no volume is reported on pre-market bars"

    gap = (today_open if today_open is not None else last) / prev_close - 1
    # DIRECTION COMES FROM THE MEASUREMENT, and where nothing was measured it says so
    # rather than filling the slot. There is no short setup here because there is no short
    # edge here: gap-up short measured +0.03% at t=+0.35, which is nothing.
    setup = direction = edge_note = None
    if GAP_DN_FLOOR <= gap <= GAP_DN_MAX:
        setup, direction = "DOWN-GAP BOUNCE", "LONG"
        edge_note = EDGE["note"]
    elif gap < GAP_DN_FLOOR:
        setup, direction = "TOO DEEP — STAND ASIDE", "NONE"
        edge_note = ("Beyond -20% the bounce reverses: -1.08%/trade on 64 trades. A gap "
                     "this size is usually news that has not finished repricing.")
    elif gap >= GAP_UP_MIN:
        setup, direction = "GAP UP — STAND ASIDE", "NONE"
        edge_note = ("Buying an up-gap at the open measured -0.33%/trade at t=-3.52 over "
                     "4,822 trades, negative in 5 of 7 years. Shorting it measured +0.03% "
                     "at t=+0.35, which is not a signal either. This scanner used to emit "
                     "the long side of this as a BUY.")
    # The one tradeable setup is BULLISH intraday (buy open, sell close). The vehicle for a
    # fast directional day-move is a LONG CALL (positive delta + gamma), NOT a short put.
    atm = round(today_open if today_open is not None else last)
    option_play = (f"LONG CALL — buy the ~${atm} call, nearest weekly expiry (ATM/1-strike-ITM). "
                   f"Defined-risk alt: call debit spread (buy ${atm}C / sell ~${atm+max(1,round(atm*0.03))}C). "
                   f"Simplest: 100 shares. NOT a short put — you want long delta+gamma for a fast intraday move, "
                   f"not a slow premium-collection play.") if direction == "LONG" else None
    return {"ticker": tk, "prev_close": round(prev_close, 2),
            "open": round(today_open, 2) if today_open is not None else None,
            "last": round(last, 2), "gap_pct": round(gap*100, 2),
            "rvol": round(rvol, 1) if rvol is not None else None,
            # Meaningless before the open, so it is None rather than a number computed
            # against a price that has not happened yet.
            "since_open_pct": (round((last/today_open-1)*100, 2)
                               if today_open is not None else None),
            "premarket": premarket, "quote_as_of": quote_as_of, "rvol_basis": rvol_basis,
            "setup": setup, "direction": direction, "edge_note": edge_note,
            "tradeable": direction == "LONG", "option_play": option_play}


def _track(cands, today):
    """Log today's candidates at scan time (open + setup); close/ret are filled by settle().

    Returns how many rows are on the book for today. This is the paper record the win-rate panel
    reads, so a write that fails is reported rather than skipped."""
    if not cands:
        return {"ok": True, "logged": 0}
    # A TRADE ON A DAY THE MARKET WAS SHUT IS NOT A TRADE.
    #
    # Every one of the twenty paper trades stuck in the settle loop was dated a Saturday or a
    # Sunday: 2026-08-08, 08-09, 08-22, 08-23, 08-29, 08-30. They could never settle because
    # there is no daily bar for a weekend, so each was retried on every cycle — 371 attempts
    # apiece — and all twenty sat permanently outside the win rate, which is the single number
    # the gap-and-go edge is judged on.
    #
    # The scanner has no holiday calendar, so this catches weekends only; a holiday still books
    # and is voided by `settle()` on the first attempt rather than retried forever.
    if datetime.strptime(today, "%Y-%m-%d").weekday() >= 5:
        log.info("gap_scanner: %d candidate(s) NOT booked for %s — the market was shut that "
                 "day, and a paper trade on a non-trading day can never settle",
                 len(cands), today)
        return {"ok": True, "logged": 0, "note": "non-trading day"}
    try:
        con = _conn()
    except sqlite3.Error as e:
        log.error("gap_scanner: %d candidate(s) for %s NOT written — the paper book could not be "
                  "opened: %s", len(cands), today, e)
        return {"ok": False, "logged": 0, "error": f"{type(e).__name__}: {e}"}
    try:
        for c in cands:
            con.execute("INSERT OR IGNORE INTO paper(date,ticker,setup,gap,rvol,open) VALUES(?,?,?,?,?,?)",
                        (today, c["ticker"], c["setup"], c["gap_pct"], c["rvol"], c["open"]))
        con.commit()
        n = con.execute("SELECT COUNT(*) FROM paper WHERE date=?", (today,)).fetchone()[0]
    except sqlite3.Error as e:
        log.error("gap_scanner: %d candidate(s) for %s NOT written to the paper book: %s",
                  len(cands), today, e)
        return {"ok": False, "logged": 0, "error": f"{type(e).__name__}: {e}"}
    finally:
        con.close()
    return {"ok": True, "logged": n}


def _void(con, date, ticker, why):
    """Mark a paper trade as impossible to settle, so it stops being retried.

    `ret` stays NULL -- a voided trade has no return and must never be scored as one -- and the
    error column carries the reason so the win-rate panel can say how many were voided and why.
    The distinction that matters: a voided trade is EXCLUDED from the record with a stated
    reason, which is a different thing from a trade that is still pending.
    """
    try:
        con.execute("UPDATE paper SET settle_error=?, settle_attempts=-1 "
                    "WHERE date=? AND ticker=?", (f"VOID: {why}", date, ticker))
        con.commit()
    except sqlite3.Error as e:
        log.error("gap_scanner: could not void %s %s: %s", date, ticker, e)


def _bump_attempt(con, date, ticker, why):
    """Count a failed settle on the row itself, so 'not due yet' and 'can never settle' stop looking
    the same."""
    try:
        con.execute("UPDATE paper SET settle_attempts=COALESCE(settle_attempts,0)+1, settle_error=? "
                    "WHERE date=? AND ticker=?", (str(why)[:200], date, ticker))
        con.commit()
    except sqlite3.Error as e:
        log.error("gap_scanner.settle: could not even record the failure for %s %s: %s", date, ticker, e)


def settle():
    """After the close, fill in each logged candidate's open->close result (paper P&L)."""
    if not os.path.exists(DB):
        return {"settled": 0, "pending": 0, "failed": 0, "stuck": [], "note": "no paper book yet"}
    try:
        con = _conn()
    except sqlite3.Error as e:
        # An unreadable book is not an empty one, so it does not get to return a clean zero.
        return {"settled": 0, "pending": 0, "failed": 0, "stuck": [],
                "error": f"paper book unreadable: {type(e).__name__}: {e}"}
    con.row_factory = sqlite3.Row
    out = {"settled": 0, "pending": 0, "failed": 0, "stuck": []}
    try:
        # `settle_attempts = -1` marks a VOIDED row: no bar exists and none ever will, so it is
        # excluded here rather than picked up on every cycle. `ret` stays NULL because a voided
        # trade has no return, which means this filter is the only thing standing between the
        # void and an infinite retry loop.
        todo = con.execute("SELECT * FROM paper WHERE ret IS NULL "
                           "AND COALESCE(settle_attempts, 0) >= 0").fetchall()
        today = datetime.now(ET).strftime("%Y-%m-%d")
        for r in todo:
            if r["date"] >= today:
                out["pending"] += 1          # only settle past days
                continue
            try:
                # `start` AND `period` TOGETHER IS THE BUG. yfinance honours `period` and
                # ignores `start`, so this asked for the LAST five days regardless of the trade
                # date — and any paper trade older than five sessions could therefore never be
                # found. It failed with "no daily bar for that date", bumped its attempt count,
                # and came back next cycle to fail identically. Twenty trades were stuck in that
                # loop and silently missing from the win rate, which is the one number the
                # gap-and-go edge is judged on.
                #
                # An explicit window around the trade date fixes it. `end` is exclusive, so it
                # is pushed a few days out to cover a weekend or a holiday either side.
                _d0 = datetime.strptime(r["date"], "%Y-%m-%d")
                d = yf.download(r["ticker"], start=r["date"],
                                end=(_d0 + timedelta(days=5)).strftime("%Y-%m-%d"),
                                interval="1d", progress=False, auto_adjust=False,
                                multi_level_index=False).rename(columns=str.lower)
                row = d[d.index.strftime("%Y-%m-%d") == r["date"]]
            except Exception as e:
                log.warning("gap_scanner.settle: %s %s not settled — quote fetch failed (%s: %s)",
                            r["date"], r["ticker"], type(e).__name__, e)
                _bump_attempt(con, r["date"], r["ticker"], f"{type(e).__name__}: {e}")
                out["failed"] += 1
                continue
            if row.empty:
                # NO BAR AND NO PROSPECT OF ONE. If the date is not a trading day, or the window
                # around it came back empty for a name that has data either side, then no amount
                # of retrying will produce a bar. Retrying anyway is what put twenty trades on
                # 371 attempts each while quietly excluding them from the win rate.
                #
                # Voiding is honest where retrying was not: the row is marked unsettleable with
                # the reason, so it stops consuming cycles and stops pretending it is still
                # pending. A voided trade is reported, never counted as a win or a loss.
                weekend = datetime.strptime(r["date"], "%Y-%m-%d").weekday() >= 5
                if weekend or not d.empty:
                    why = ("the market was shut that day" if weekend
                           else "no bar for this date although the window returned others")
                    log.warning("gap_scanner.settle: %s %s VOIDED — %s",
                                r["date"], r["ticker"], why)
                    _void(con, r["date"], r["ticker"], why)
                    out["voided"] = out.get("voided", 0) + 1
                    continue
                log.warning("gap_scanner.settle: %s %s not settled — no daily bar for that date",
                            r["date"], r["ticker"])
                _bump_attempt(con, r["date"], r["ticker"], "no daily bar for that date")
                out["failed"] += 1
                continue
            try:
                op, cl = float(row["open"].iloc[0]), float(row["close"].iloc[0])
                ret = cl/op - 1                      # both setups are LONG open->close
                con.execute("UPDATE paper SET close=?,ret=?,win=?,settle_error=NULL WHERE date=? AND ticker=?",
                            (round(cl, 2), round(ret*100, 2), int(ret > 0), r["date"], r["ticker"]))
                con.commit()
                out["settled"] += 1
            except (KeyError, IndexError, ValueError, TypeError, ZeroDivisionError, sqlite3.Error) as e:
                log.error("gap_scanner.settle: %s %s NOT settled — %s: %s",
                          r["date"], r["ticker"], type(e).__name__, e)
                _bump_attempt(con, r["date"], r["ticker"], f"{type(e).__name__}: {e}")
                out["failed"] += 1
        stuck = con.execute("SELECT date, ticker, settle_attempts, settle_error FROM paper "
                            "WHERE ret IS NULL AND COALESCE(settle_attempts,0) >= ?",
                            (MAX_SETTLE_ATTEMPTS,)).fetchall()
        out["stuck"] = [dict(x) for x in stuck]
    finally:
        con.close()
    if out["stuck"]:
        log.error("gap_scanner.settle: %d paper trade(s) have failed to settle %d+ times and are "
                  "missing from the win rate: %s", len(out["stuck"]), MAX_SETTLE_ATTEMPTS,
                  ", ".join(f"{s['date']} {s['ticker']} ({s['settle_error']})" for s in out["stuck"]))
    return out


def track_record():
    if not os.path.exists(DB):
        return {"n": 0}
    try:
        con = _conn()
    except sqlite3.Error as e:
        return {"n": 0, "error": f"paper book unreadable: {type(e).__name__}: {e}"}
    con.row_factory = sqlite3.Row
    try:
        done = con.execute("SELECT * FROM paper WHERE ret IS NOT NULL ORDER BY date DESC").fetchall()
        unsettled = con.execute("SELECT date, ticker, settle_attempts, settle_error FROM paper "
                                "WHERE ret IS NULL ORDER BY date").fetchall()
    finally:
        con.close()
    # Unsettled rows are shown next to the record: without them a stuck trade is simply absent, and
    # absent reads as "never happened" rather than "we lost the result".
    base = {"unsettled": len(unsettled),
            "stuck": [dict(x) for x in unsettled if (x["settle_attempts"] or 0) >= MAX_SETTLE_ATTEMPTS]}
    if not done:
        return {"n": 0, **base}
    rets = [r["ret"] for r in done]
    return {"n": len(done), "win": round(np.mean([r["win"] for r in done])*100),
            "avg": round(np.mean(rets), 2), "total": round(np.sum(rets), 1),
            "recent": [dict(r) for r in done[:15]], **base}


def run():
    try:
        settle_result = settle()
    except Exception as e:
        # The scan is still worth running even if yesterday's paper trades cannot be settled, but the
        # snapshot has to carry the failure: scan_all calls run() at module level with no guard.
        log.error("gap_scanner: settle failed (%s: %s) — today's scan continues, the paper record "
                  "does not advance", type(e).__name__, e)
        settle_result = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    rows = []
    failed = []
    for tk in UNIV:
        try:
            r = scan_one(tk)
        except Exception as e:
            # One name failing is normal; the whole universe failing is an outage, and it used to be
            # indistinguishable from a quiet morning with no setups.
            log.warning("gap_scanner: %s could not be scanned (%s: %s)", tk, type(e).__name__, e)
            failed.append({"ticker": tk, "error": f"{type(e).__name__}: {str(e)[:80]}"})
            continue
        if r:
            rows.append(r)
        else:
            failed.append({"ticker": tk, "error": "fewer than 21 daily bars returned"})
    if failed:
        log.warning("gap_scanner: %d of %d names did not scan — today's candidate list is incomplete",
                    len(failed), len(UNIV))
    cands = [r for r in rows if r.get("tradeable")]
    # Deepest first inside the band: -6 to -20% measured roughly double the -4 to -6% band.
    cands.sort(key=lambda r: r["gap_pct"])
    stand_aside = [r for r in rows if r.get("setup") and not r.get("tradeable")]
    # WHICH SESSION STATE ARE WE IN? The panel needs this to tell an empty candidate list
    # apart from a broken scan. Pre-market with no named setups is the CORRECT state, not a
    # failure, and the two used to render identically.
    premkt = [r for r in rows if r.get("premarket")]
    if not rows:
        session_state = "unknown"
    elif len(premkt) == len(rows):
        session_state = "premarket"
    elif premkt:
        session_state = "mixed"
    else:
        session_state = "session"

    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
           "epoch": datetime.now(ET).timestamp(),
           "session_date": datetime.now(ET).strftime("%Y-%m-%d"),
           "session_state": session_state,
           "premarket_note": (
               "Pre-market. Gaps below are live prints against the previous close, but this "
               "feed reports NO VOLUME on pre-market bars, so relative volume cannot be "
               "confirmed and no setup is named until the opening bell. An empty candidate "
               "list right now is the correct answer, not a failed scan."
               if session_state == "premarket" else None),
           "rule": ("LONG a gap down between -4% and -20%: buy at the open, flat at the "
                    "close. No volume filter — the RVOL gate was lookahead and it destroyed "
                    "this edge. Up-gaps are a STAND ASIDE: long measured -0.33% (t=-3.52) "
                    "and short +0.03% (t=+0.35)."),
           "candidates": cands, "stand_aside": stand_aside, "edge": EDGE,
           "n_scanned": len(rows),
           "n_universe": len(UNIV), "n_failed": len(failed), "failed": failed,
           "all": sorted(rows, key=lambda r: -r["gap_pct"])}
    out["settle"] = settle_result
    out["paper_log"] = _track(cands, datetime.now(ET).strftime("%Y-%m-%d"))
    try:
        out["track"] = track_record()
    except Exception as e:
        log.error("gap_scanner: the paper track record could not be read (%s: %s)", type(e).__name__, e)
        out["track"] = {"n": 0, "error": f"{type(e).__name__}: {str(e)[:120]}"}
    try:
        import analyst
        out["ai"] = analyst.analyze(out)
    except Exception as e:
        log.warning("gap_scanner: analyst read unavailable (%s: %s)", type(e).__name__, e)
        out["ai"] = {"ok": False, "error": str(e)[:80], "text": None}
    try:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, default=str)
    except OSError as e:
        # The dashboard reads this file. A failed write leaves the last scan on screen looking current.
        log.error("gap_scanner: could not write %s: %s", OUT, e)
        out["write_error"] = f"{type(e).__name__}: {e}"
    print(f"gap scan {out['as_of']}: {len(cands)} candidates of {len(rows)} scanned"
          + (f" ({len(failed)} of {len(UNIV)} names failed to fetch)" if failed else ""))
    for c in cands:
        since = (f", {c['since_open_pct']:+.1f}% since open"
                 if c.get("since_open_pct") is not None else "")
        rv = f"RVOL {c['rvol']}x" if c.get("rvol") is not None else "RVOL n/a"
        print(f"  {c['direction']} {c['setup']}: {c['ticker']} gap {c['gap_pct']:+.1f}% "
              f"{rv} (open {c['open']}, now {c['last']}{since})")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
