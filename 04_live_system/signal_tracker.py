"""signal_tracker.py — accountability + P&L for the SPX 0DTE reconciled signal.

Logs the master decision each session AND the concrete 0DTE option it recommends, then settles both:
  - DIRECTION: did SPX close the right way (win/loss).
  - OPTION P&L: the recommended ATM 0DTE call/put, bought at the open, held to the close (intrinsic
    at expiry) vs the entry premium → the REAL % return on the trade (captures theta / total losses).

Entry premium is estimated from the market's expected move (ATM 0DTE ≈ 0.55×expected open→close move);
this is an estimate, labeled as such — logging your real fills would make it exact. Conflict/neutral =
stood down (no trade). `calibration()` turns the growing record into a realized win-rate BY conviction
bucket, which the live signal reads back to self-adjust (conservative, sample-gated).

A settle that fails is counted, never forgotten. Every unsettled row carries settle_attempts and
settle_error, and settle() reports the ones that have given up — the old version swallowed every
failure with `continue`, so a session whose price data never arrived stayed pending forever and the
win-rate panel simply never mentioned it.
"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np

from idt import db, paths

# LOG, not log: this module already exports a public log(snap) that writes today's call to the book.
LOG = logging.getLogger("signal_tracker")

ET = ZoneInfo("America/New_York")
# Under STATE_ROOT, created on demand. Was HERE/"data" plus a bare sqlite3 handle: no WAL, 5-second
# lock, no directory, which is how a fresh clone raised "unable to open database file" in a render.
DB = paths.state("signal_track.db")
CALIB = paths.state("calibration.json")

COLS = """session TEXT PRIMARY KEY, direction TEXT, conviction INT, regime TEXT, ref REAL,
    open REAL, close REAL, ret REAL, win INT, strike REAL, prem_pct REAL, opt_pnl REAL, opt_win INT,
    logged TEXT, seed INT DEFAULT 0, settle_attempts INT DEFAULT 0, settle_error TEXT"""

# Columns added after the table shipped. Applied by comparing against PRAGMA table_info instead of
# running ALTER inside a try/except that swallowed everything — that pattern made a real schema error
# indistinguishable from "the column is already there".
_MIGRATIONS = [("strike", "REAL"), ("prem_pct", "REAL"), ("opt_pnl", "REAL"), ("opt_win", "INT"),
               ("seed", "INT"), ("settle_attempts", "INT DEFAULT 0"), ("settle_error", "TEXT")]

# After this many failed attempts a row is reported as stuck rather than retried in silence forever.
MAX_SETTLE_ATTEMPTS = 3


def _conn():
    try:
        con = db.connect(DB)
    except sqlite3.Error as e:
        LOG.error("signal_tracker: cannot open the signal book at %s: %s", DB, e)
        raise
    con.execute(f"CREATE TABLE IF NOT EXISTS sig({COLS})")
    have = {r[1] for r in con.execute("PRAGMA table_info(sig)").fetchall()}
    for c, t in _MIGRATIONS:
        if c not in have:
            con.execute(f"ALTER TABLE sig ADD COLUMN {c} {t}")
    con.commit()
    return con


def _session_date():
    n = datetime.now(ET); mins = n.hour * 60 + n.minute
    d = n.date()
    if n.weekday() < 5 and mins < 960:
        return d
    while True:
        d = d + timedelta(days=1)
        if d.weekday() < 5:
            return d


def _est_prem_pct(exp_oc_pct):
    """ATM 0DTE option premium ≈ 0.55 × the expected open→close move %. Floor at a realistic 0.15%."""
    try:
        return max(0.15, round(0.55 * float(exp_oc_pct), 3))
    except (TypeError, ValueError):
        # The premium sets the leverage in _settle_row, so a fabricated 0.30% silently changes every
        # option P&L for that session. Same number as before, but it now says it happened.
        LOG.warning("signal_tracker: no usable expected move (%r) — assuming a 0.30%% ATM premium, "
                    "so this session's option P&L is a guess on top of an estimate", exp_oc_pct)
        return 0.30


def log(snap):
    """Record today's master call. Returns {"ok": ...} — an unlogged session is a hole in the record."""
    try:
        conv = int(snap.get("conviction", 0) or 0)
    except (TypeError, ValueError):
        LOG.warning("signal_tracker.log: unreadable conviction %r — recorded as 0", snap.get("conviction"))
        conv = 0
    sd = str(_session_date())
    md = snap.get("master_dir", "neutral")
    prem = _est_prem_pct(snap.get("exp_oc_pct")) if md in ("bullish", "bearish") else None
    try:
        strike = round(float(snap.get("spx_level"))) if snap.get("spx_level") and md in ("bullish", "bearish") else None
    except (TypeError, ValueError):
        LOG.warning("signal_tracker.log: unreadable spx_level %r — no strike recorded", snap.get("spx_level"))
        strike = None
    try:
        con = _conn()
    except sqlite3.Error as e:
        LOG.error("signal_tracker.log: session %s call NOT recorded: %s", sd, e)
        return {"ok": False, "session": sd, "reason": f"{type(e).__name__}: {e}"}
    try:
        con.execute("""INSERT INTO sig(session,direction,conviction,regime,ref,strike,prem_pct,logged) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(session) DO UPDATE SET direction=excluded.direction, conviction=excluded.conviction,
            regime=excluded.regime, strike=excluded.strike, prem_pct=excluded.prem_pct, logged=excluded.logged""",
                    (sd, md, conv, snap.get("regime", ""), snap.get("spx_level"),
                     strike, prem, datetime.now(ET).isoformat(timespec="seconds")))
        con.commit()
    except sqlite3.Error as e:
        LOG.error("signal_tracker.log: session %s call NOT recorded: %s", sd, e)
        return {"ok": False, "session": sd, "reason": f"{type(e).__name__}: {e}"}
    finally:
        con.close()
    return {"ok": True, "session": sd, "direction": md, "conviction": conv}


def _settle_row(direction, op, hi, lo, cl, prem_pct, tp=50.0):
    """Direction win + REALISTIC 0DTE option P&L. A near-money 0DTE option has delta ~0.5 and high
    gamma, so it moves ~(50/premium%) per 1% underlying — a SMALL favorable move is a big % gain, and
    the trade is taken quickly. Model: leverage on the favorable excursion, disciplined take-profit at
    +50%; if TP not reached, mark the close at leverage (floored -100%). Matches how these are traded."""
    ret = (cl / op - 1) * 100
    if direction == "bullish":
        win = int(ret > 0); fav = (hi - op) / op * 100; close_fav = ret
    elif direction == "bearish":
        win = int(ret < 0); fav = (op - lo) / op * 100; close_fav = -ret
    else:
        return round(ret, 2), None, None, None
    if prem_pct and prem_pct > 0:
        lev = 50.0 / prem_pct                  # % option move per 1% underlying move (delta ~0.5)
        peak = lev * fav * 1.3                 # gamma boost on the favorable side
        if peak >= tp:
            opt_pnl = tp                       # disciplined take-profit hit intraday
        else:
            opt_pnl = round(max(-100.0, lev * close_fav), 1)   # mark the close at leverage
        opt_win = int(opt_pnl > 0)
    else:
        opt_pnl = opt_win = None
    return round(ret, 2), win, opt_pnl, opt_win


def _bump_attempt(con, session, why):
    """Count a failed settle on the row itself. Without this a row that can never settle is retried
    forever, in silence, and 'pending' and 'broken' look identical."""
    try:
        con.execute("UPDATE sig SET settle_attempts=COALESCE(settle_attempts,0)+1, settle_error=? "
                    "WHERE session=?", (str(why)[:200], session))
        con.commit()
    except sqlite3.Error as e:
        LOG.error("signal_tracker.settle: could not even record the failure for %s: %s", session, e)


def settle():
    """Settle every past session that is still open. Returns what happened, including what is stuck."""
    if not os.path.exists(DB):
        return {"settled": 0, "pending": 0, "stuck": [], "note": "no signal book yet"}
    try:
        con = _conn()
    except sqlite3.Error as e:
        # An unreadable book is not an empty one, so it does not get to return a clean zero.
        return {"settled": 0, "pending": 0, "failed": 0, "stuck": [],
                "error": f"signal book unreadable: {type(e).__name__}: {e}"}
    con.row_factory = sqlite3.Row
    out = {"settled": 0, "pending": 0, "failed": 0, "stuck": []}
    try:
        todo = con.execute("SELECT * FROM sig WHERE ret IS NULL").fetchall()
        today = datetime.now(ET).date()
        import yfinance as yf
        for r in todo:
            session = r["session"]
            try:
                sd = datetime.strptime(session, "%Y-%m-%d").date()
            except (TypeError, ValueError) as e:
                LOG.error("signal_tracker.settle: row %r has an unparseable session date (%s) and can "
                          "never settle", session, e)
                _bump_attempt(con, session, f"unparseable session date: {e}")
                out["failed"] += 1
                continue
            if sd >= today:
                out["pending"] += 1          # not due yet; the session has not finished
                continue
            try:
                d = yf.download("^SPX", start=session, end=str(sd + timedelta(days=1)), interval="1d",
                                progress=False, auto_adjust=True, multi_level_index=False)
            except Exception as e:
                LOG.warning("signal_tracker.settle: %s not settled — quote fetch failed (%s: %s)",
                            session, type(e).__name__, e)
                _bump_attempt(con, session, f"{type(e).__name__}: {e}")
                out["failed"] += 1
                continue
            if d is None or d.empty:
                # Usually a market holiday that got logged as a session, or a symbol/API change.
                LOG.warning("signal_tracker.settle: %s not settled — no daily bar came back for ^SPX",
                            session)
                _bump_attempt(con, session, "no daily bar returned")
                out["failed"] += 1
                continue
            try:
                op = float(d["Open"].iloc[0]); cl = float(d["Close"].iloc[0])
                hi = float(d["High"].iloc[0]); lo = float(d["Low"].iloc[0])
                ret, win, opt_pnl, opt_win = _settle_row(r["direction"], op, hi, lo, cl, r["prem_pct"])
                con.execute("UPDATE sig SET open=?,close=?,ret=?,win=?,opt_pnl=?,opt_win=?,settle_error=NULL "
                            "WHERE session=?",
                            (round(op, 2), round(cl, 2), ret, win, opt_pnl, opt_win, session))
                con.commit()
                out["settled"] += 1
            except (KeyError, IndexError, ValueError, TypeError, ZeroDivisionError, sqlite3.Error) as e:
                LOG.error("signal_tracker.settle: %s NOT settled — %s: %s", session, type(e).__name__, e)
                _bump_attempt(con, session, f"{type(e).__name__}: {e}")
                out["failed"] += 1
        stuck = con.execute("SELECT session, settle_attempts, settle_error FROM sig WHERE ret IS NULL "
                            "AND COALESCE(settle_attempts,0) >= ?", (MAX_SETTLE_ATTEMPTS,)).fetchall()
        out["stuck"] = [dict(x) for x in stuck]
    finally:
        con.close()
    if out["stuck"]:
        LOG.error("signal_tracker.settle: %d session(s) have failed to settle %d+ times and are stuck: %s",
                  len(out["stuck"]), MAX_SETTLE_ATTEMPTS,
                  ", ".join(f"{s['session']} ({s['settle_error']})" for s in out["stuck"]))
    calibration()          # refresh the self-calibration table after settling
    return out


def record():
    if not os.path.exists(DB):
        return {"n": 0}
    try:
        con = _conn()
    except sqlite3.Error as e:
        return {"n": 0, "error": f"signal book unreadable: {type(e).__name__}: {e}"}
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM sig WHERE ret IS NOT NULL ORDER BY session DESC").fetchall()
        unsettled = con.execute("SELECT session, settle_attempts, settle_error FROM sig "
                                "WHERE ret IS NULL ORDER BY session").fetchall()
    finally:
        con.close()
    # Pending vs stuck, on the panel rather than only in the log: a signal that can never settle used
    # to vanish from every count in this file.
    stuck = [dict(x) for x in unsettled if (x["settle_attempts"] or 0) >= MAX_SETTLE_ATTEMPTS]
    directional = [r for r in rows if r["win"] is not None]
    stood = [r for r in rows if r["win"] is None]
    # The backtest seed and the live record live in the same table. They are counted separately here
    # because "512 settled sessions" reads as live experience when 500 of them are seeded history.
    seed_n = sum(1 for r in directional if (r["seed"] or 0))
    base = {"unsettled": len(unsettled), "stuck": stuck}
    if not directional:
        return {"n": 0, "stood_down": len(stood), "seed_n": 0, "live_n": 0, **base}
    wins = [r["win"] for r in directional]
    opt = [r for r in directional if r["opt_pnl"] is not None]
    opt_pnls = [r["opt_pnl"] for r in opt]
    hi = [r for r in directional if r["conviction"] >= 55]
    return {"n": len(directional), "win": round(np.mean(wins) * 100),
            "stood_down": len(stood),
            "seed_n": seed_n, "live_n": len(directional) - seed_n,
            "hi_conv_n": len(hi), "hi_conv_win": round(np.mean([r["win"] for r in hi]) * 100) if hi else None,
            "opt_n": len(opt),
            "opt_win": round(np.mean([r["opt_win"] for r in opt]) * 100) if opt else None,
            "opt_avg": round(np.mean(opt_pnls), 1) if opt_pnls else None,
            "opt_total": round(np.sum(opt_pnls), 0) if opt_pnls else None,
            "opt_best": round(max(opt_pnls), 0) if opt_pnls else None,
            "opt_worst": round(min(opt_pnls), 0) if opt_pnls else None,
            "recent": [{"session": r["session"], "direction": r["direction"], "conviction": r["conviction"],
                        "ret": r["ret"], "win": r["win"], "opt_pnl": r["opt_pnl"]} for r in rows[:12]],
            **base}


def calibration():
    """Realized win-rate + option-P&L BY conviction bucket → written to calibration.json for self-tuning."""
    if not os.path.exists(DB):
        return {}
    try:
        con = _conn()
    except sqlite3.Error as e:
        return {"error": f"signal book unreadable: {type(e).__name__}: {e}"}
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT * FROM sig WHERE win IS NOT NULL").fetchall()
    finally:
        con.close()
    buckets = {"low (<45)": (0, 45), "mid (45-60)": (45, 60), "high (60+)": (60, 999)}
    out = {}
    for name, (lo, hi) in buckets.items():
        b = [r for r in rows if lo <= r["conviction"] < hi]
        if b:
            opt = [r["opt_pnl"] for r in b if r["opt_pnl"] is not None]
            out[name] = {"n": len(b), "dir_win": round(np.mean([r["win"] for r in b]) * 100),
                         "opt_win": round(np.mean([1 if p > 0 else 0 for p in opt]) * 100) if opt else None,
                         "opt_avg": round(np.mean(opt), 1) if opt else None}
    try:
        with open(CALIB, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
    except OSError as e:
        # calib_adjust reads this file to nudge live conviction. A stale one keeps nudging on old
        # numbers, which is worse than not nudging at all, so it may not fail quietly.
        LOG.error("signal_tracker.calibration: could not write %s: %s — calib_adjust will keep using "
                  "the previous file", CALIB, e)
    return out


def calib_adjust(direction, conviction):
    """Self-calibration feedback: conservatively nudge conviction toward the REALIZED win-rate of its
    bucket, but only when that bucket has a real sample (≥20). Returns (adj_conviction, note)."""
    if direction not in ("bullish", "bearish"):
        return conviction, None
    try:
        with open(CALIB, encoding="utf-8") as fh:
            cal = json.load(fh)
    except FileNotFoundError:
        return conviction, None        # nothing settled yet: no calibration is the honest answer
    except (OSError, json.JSONDecodeError) as e:
        LOG.warning("signal_tracker.calib_adjust: %s is unreadable (%s) — conviction left unadjusted",
                    CALIB, e)
        return conviction, None
    name = "high (60+)" if conviction >= 60 else "mid (45-60)" if conviction >= 45 else "low (<45)"
    b = cal.get(name)
    if not b or b.get("n", 0) < 20:
        return conviction, None
    realized = b["dir_win"]                       # e.g. 58 (%)
    # blend the current conviction with the realized win-rate (75% prior / 25% realized), gentle
    adj = int(round(0.75 * conviction + 0.25 * realized))
    note = f"self-calibrated: {name} bucket realized {realized}% win over {b['n']} trades"
    return adj, note


def backfill_dix(days=500):
    """Seed with the BACKTESTED regime-filtered DIX signal + estimated option P&L (VIX-based premium).
    2-yr window so the (selective) regime-filtered sample is meaningful.

    Seeded rows carry seed=1. record() counts them separately: they are backtest history, not the
    live track record, and blending the two overstates how much has actually been observed."""
    import pandas as pd
    import yfinance as yf
    src = paths.state("squeeze_dix_gex.csv")
    if not os.path.exists(src):
        raise FileNotFoundError(
            f"backfill needs {src}, which is not here.\n"
            f"  It is the DIX/GEX history the seed is derived from; see 06_data_guide/DATA.md.\n"
            f"  Without it the seed cannot be reconstructed, and the live record is what remains.")
    g = pd.read_csv(src, parse_dates=["date"]).sort_values("date")
    g["dz"] = (g["dix"] - g["dix"].rolling(252, min_periods=60).mean()) / g["dix"].rolling(252, min_periods=60).std()
    g["gz"] = (g["gex"] - g["gex"].rolling(252, min_periods=60).mean()) / g["gex"].rolling(252, min_periods=60).std()
    g["dz1"] = g["dz"].shift(1); g["gz1"] = g["gz"].shift(1)
    px = yf.download(["^SPX", "^VIX"], period="2y", interval="1d", progress=False, auto_adjust=True)
    spx = pd.DataFrame({"open": px["Open"]["^SPX"], "high": px["High"]["^SPX"], "low": px["Low"]["^SPX"],
                        "close": px["Close"]["^SPX"], "vix": px["Close"]["^VIX"]})
    spx.index = pd.to_datetime(spx.index).tz_localize(None)
    con = _conn()
    gi = g.set_index(g["date"].dt.date)
    n = 0
    try:
        for dt, row in spx.tail(days).iterrows():
            sd = dt.date()
            if sd not in gi.index or pd.isna(gi.loc[sd, "dz1"]):
                continue
            dz1 = gi.loc[sd, "dz1"]; gz1 = gi.loc[sd, "gz1"]
            # REGIME-FILTERED: only buy premium when DIX is bullish AND gamma is low (big-range day).
            # High-gamma (pin) days = stand down even if DIX is bullish — that's where premium buying dies.
            bullish = (dz1 > 0.5) and (gz1 < 0)
            direction = "bullish" if bullish else "neutral"
            conv = 62 if (dz1 > 0.5 and gz1 < -0.5) else 55 if bullish else 30
            op = float(row["open"]); cl = float(row["close"]); vix = float(row["vix"])
            hi = float(row["high"]); lo = float(row["low"])
            prem = round(max(0.15, 0.4 * vix / 15.87), 3) if bullish else None   # VIX-based ATM 0DTE premium %
            ret, win, opt_pnl, opt_win = _settle_row(direction, op, hi, lo, cl, prem)
            con.execute("""INSERT OR IGNORE INTO sig(session,direction,conviction,regime,ref,open,close,ret,win,
                strike,prem_pct,opt_pnl,opt_win,logged,seed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                        (str(sd), direction, conv, "backtest seed", round(op, 2), round(op, 2), round(cl, 2),
                         ret, win, round(op), prem, opt_pnl, opt_win, "seed"))
            n += 1
        con.commit()
    finally:
        con.close()
    calibration()
    return n


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if "backfill" in sys.argv:
        print("seeded", backfill_dix(), "sessions")
    print("settle:", json.dumps(settle(), indent=2))
    print(json.dumps(record(), indent=2))
    print("\ncalibration:", json.dumps(calibration(), indent=2))
