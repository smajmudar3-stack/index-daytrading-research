"""gap_scanner.py — the LIVE gap-and-go signal-giver (the validated edge).

Each morning it scans a universe of volatile stocks and flags today's tradeable setups:
  GAP-AND-GO LONG : gap up >3% AND relative volume >1.5x  -> buy at open, sell at close
  DOWN-GAP BOUNCE : gap down >4% (RVOL>1.5)               -> buy at open, sell at close
Backtested (2019-2026, 49 names, net 15bps): gap-go +1.25%/trade t=6.6 (OOS t=3.2, survives
40bps + excluding mega-winners); down-gap bounce +0.65% t=4.9. Writes data/gap_snapshot.json.
Meant for PAPER TRADING first — accuracy shows up over many trades, any single one is noise.

Every scan reports how many names it could NOT fetch. A quote outage used to return "0 candidates of
0 scanned", which reads exactly like a calm market, and the paper record just skipped a day.
"""
import json
import logging
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
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

GAP_UP, GAP_DN, RVOL_MIN = 0.03, -0.04, 1.5

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


def scan_one(tk):
    d = yf.download(tk, period="2mo", interval="1d", progress=False, auto_adjust=False,
                    multi_level_index=False).rename(columns=str.lower)
    if d is None or len(d) < 21:
        return None
    prev_close = float(d["close"].iloc[-2])
    today_open = float(d["open"].iloc[-1])
    today_vol = float(d["volume"].iloc[-1])
    avg_vol = float(d["volume"].iloc[-21:-1].mean())
    last = float(d["close"].iloc[-1])
    gap = today_open / prev_close - 1
    rvol = today_vol / avg_vol if avg_vol > 0 else 0
    setup = None
    if gap >= GAP_UP and rvol >= RVOL_MIN:
        setup = "GAP-AND-GO LONG"
    elif gap <= GAP_DN and rvol >= RVOL_MIN:
        setup = "DOWN-GAP BOUNCE"
    # both setups are BULLISH intraday (buy open, sell close). The vehicle for a fast
    # directional day-move is a LONG CALL (positive delta + gamma), NOT a short put.
    atm = round(today_open)
    option_play = (f"LONG CALL — buy the ~${atm} call, nearest weekly expiry (ATM/1-strike-ITM). "
                   f"Defined-risk alt: call debit spread (buy ${atm}C / sell ~${atm+max(1,round(atm*0.03))}C). "
                   f"Simplest: 100 shares. NOT a short put — you want long delta+gamma for a fast intraday move, "
                   f"not a slow premium-collection play.") if setup else None
    return {"ticker": tk, "prev_close": round(prev_close, 2), "open": round(today_open, 2),
            "last": round(last, 2), "gap_pct": round(gap*100, 2), "rvol": round(rvol, 1),
            "since_open_pct": round((last/today_open-1)*100, 2), "setup": setup,
            "option_play": option_play}


def _track(cands, today):
    """Log today's candidates at scan time (open + setup); close/ret are filled by settle().

    Returns how many rows are on the book for today. This is the paper record the win-rate panel
    reads, so a write that fails is reported rather than skipped."""
    if not cands:
        return {"ok": True, "logged": 0}
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
        todo = con.execute("SELECT * FROM paper WHERE ret IS NULL").fetchall()
        today = datetime.now(ET).strftime("%Y-%m-%d")
        for r in todo:
            if r["date"] >= today:
                out["pending"] += 1          # only settle past days
                continue
            try:
                d = yf.download(r["ticker"], start=r["date"], end=None, period="5d", interval="1d",
                                progress=False, auto_adjust=False, multi_level_index=False).rename(columns=str.lower)
                row = d[d.index.strftime("%Y-%m-%d") == r["date"]]
            except Exception as e:
                log.warning("gap_scanner.settle: %s %s not settled — quote fetch failed (%s: %s)",
                            r["date"], r["ticker"], type(e).__name__, e)
                _bump_attempt(con, r["date"], r["ticker"], f"{type(e).__name__}: {e}")
                out["failed"] += 1
                continue
            if row.empty:
                # The 5-day window has moved past this date, or the ticker stopped trading.
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
    cands = [r for r in rows if r["setup"]]
    cands.sort(key=lambda r: (r["setup"], -abs(r["gap_pct"])))
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
           "epoch": datetime.now(ET).timestamp(),
           "rule": "gap up >3% & RVOL>1.5 = GO long; gap down >4% & RVOL>1.5 = bounce long; "
                   "buy at open, sell at close",
           "candidates": cands, "n_scanned": len(rows),
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
        print(f"  {c['setup']}: {c['ticker']} gap {c['gap_pct']:+.1f}% RVOL {c['rvol']}x "
              f"(open {c['open']}, now {c['last']}, {c['since_open_pct']:+.1f}% since open)")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
