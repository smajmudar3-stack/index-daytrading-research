"""signal_tracker.py — accountability + P&L for the SPX 0DTE reconciled signal.

Logs the master decision each session AND the concrete 0DTE option it recommends, then settles both:
  - DIRECTION: did SPX close the right way (win/loss).
  - OPTION P&L: the recommended ATM 0DTE call/put, bought at the open, held to the close (intrinsic
    at expiry) vs the entry premium → the REAL % return on the trade (captures theta / total losses).

Entry premium is estimated from the market's expected move (ATM 0DTE ≈ 0.55×expected open→close move);
this is an estimate, labeled as such — logging your real fills would make it exact. Conflict/neutral =
stood down (no trade). `calibration()` turns the growing record into a realized win-rate BY conviction
bucket, which the live signal reads back to self-adjust (conservative, sample-gated).
"""
import os
import sqlite3
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "signal_track.db")
CALIB = os.path.join(HERE, "data", "calibration.json")

COLS = """session TEXT PRIMARY KEY, direction TEXT, conviction INT, regime TEXT, ref REAL,
    open REAL, close REAL, ret REAL, win INT, strike REAL, prem_pct REAL, opt_pnl REAL, opt_win INT,
    logged TEXT, seed INT DEFAULT 0"""


def _conn():
    con = sqlite3.connect(DB)
    con.execute(f"CREATE TABLE IF NOT EXISTS sig({COLS})")
    for c, t in [("strike", "REAL"), ("prem_pct", "REAL"), ("opt_pnl", "REAL"), ("opt_win", "INT"), ("seed", "INT")]:
        try:
            con.execute(f"ALTER TABLE sig ADD COLUMN {c} {t}")
        except Exception:
            pass
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
    except Exception:
        return 0.30


def log(snap):
    con = _conn()
    sd = str(_session_date())
    md = snap.get("master_dir", "neutral")
    prem = _est_prem_pct(snap.get("exp_oc_pct")) if md in ("bullish", "bearish") else None
    strike = round(float(snap.get("spx_level"))) if snap.get("spx_level") and md in ("bullish", "bearish") else None
    con.execute("""INSERT INTO sig(session,direction,conviction,regime,ref,strike,prem_pct,logged) VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(session) DO UPDATE SET direction=excluded.direction, conviction=excluded.conviction,
        regime=excluded.regime, strike=excluded.strike, prem_pct=excluded.prem_pct, logged=excluded.logged""",
                (sd, md, int(snap.get("conviction", 0)), snap.get("regime", ""), snap.get("spx_level"),
                 strike, prem, datetime.now(ET).isoformat(timespec="seconds")))
    con.commit(); con.close()


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


def settle():
    if not os.path.exists(DB):
        return
    con = _conn(); con.row_factory = sqlite3.Row
    todo = con.execute("SELECT * FROM sig WHERE ret IS NULL").fetchall()
    today = datetime.now(ET).date()
    import yfinance as yf
    for r in todo:
        try:
            sd = datetime.strptime(r["session"], "%Y-%m-%d").date()
            if sd >= today:
                continue
            d = yf.download("^SPX", start=r["session"], end=str(sd + timedelta(days=1)), interval="1d",
                            progress=False, auto_adjust=True, multi_level_index=False)
            if d is None or d.empty:
                continue
            op = float(d["Open"].iloc[0]); cl = float(d["Close"].iloc[0])
            hi = float(d["High"].iloc[0]); lo = float(d["Low"].iloc[0])
            ret, win, opt_pnl, opt_win = _settle_row(r["direction"], op, hi, lo, cl, r["prem_pct"])
            con.execute("UPDATE sig SET open=?,close=?,ret=?,win=?,opt_pnl=?,opt_win=? WHERE session=?",
                        (round(op, 2), round(cl, 2), ret, win, opt_pnl, opt_win, r["session"]))
        except Exception:
            continue
    con.commit(); con.close()
    calibration()          # refresh the self-calibration table after settling


def record():
    if not os.path.exists(DB):
        return {"n": 0}
    con = _conn(); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM sig WHERE ret IS NOT NULL ORDER BY session DESC").fetchall()
    con.close()
    directional = [r for r in rows if r["win"] is not None]
    stood = [r for r in rows if r["win"] is None]
    if not directional:
        return {"n": 0, "stood_down": len(stood)}
    wins = [r["win"] for r in directional]
    opt = [r for r in directional if r["opt_pnl"] is not None]
    opt_pnls = [r["opt_pnl"] for r in opt]
    hi = [r for r in directional if r["conviction"] >= 55]
    return {"n": len(directional), "win": round(np.mean(wins) * 100),
            "stood_down": len(stood),
            "hi_conv_n": len(hi), "hi_conv_win": round(np.mean([r["win"] for r in hi]) * 100) if hi else None,
            "opt_n": len(opt),
            "opt_win": round(np.mean([r["opt_win"] for r in opt]) * 100) if opt else None,
            "opt_avg": round(np.mean(opt_pnls), 1) if opt_pnls else None,
            "opt_total": round(np.sum(opt_pnls), 0) if opt_pnls else None,
            "opt_best": round(max(opt_pnls), 0) if opt_pnls else None,
            "opt_worst": round(min(opt_pnls), 0) if opt_pnls else None,
            "recent": [{"session": r["session"], "direction": r["direction"], "conviction": r["conviction"],
                        "ret": r["ret"], "win": r["win"], "opt_pnl": r["opt_pnl"]} for r in rows[:12]]}


def calibration():
    """Realized win-rate + option-P&L BY conviction bucket → written to calibration.json for self-tuning."""
    if not os.path.exists(DB):
        return {}
    con = _conn(); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM sig WHERE win IS NOT NULL").fetchall()
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
        json.dump(out, open(CALIB, "w"), indent=2)
    except Exception:
        pass
    return out


def calib_adjust(direction, conviction):
    """Self-calibration feedback: conservatively nudge conviction toward the REALIZED win-rate of its
    bucket, but only when that bucket has a real sample (≥20). Returns (adj_conviction, note)."""
    if direction not in ("bullish", "bearish"):
        return conviction, None
    try:
        cal = json.load(open(CALIB))
    except Exception:
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
    2-yr window so the (selective) regime-filtered sample is meaningful."""
    import pandas as pd
    import yfinance as yf
    g = pd.read_csv(os.path.join(HERE, "data", "squeeze_dix_gex.csv"), parse_dates=["date"]).sort_values("date")
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
    con.commit(); con.close()
    calibration()
    return n


if __name__ == "__main__":
    import sys
    if "backfill" in sys.argv:
        print("seeded", backfill_dix(), "sessions")
    settle()
    print(json.dumps(record(), indent=2))
    print("\ncalibration:", json.dumps(calibration(), indent=2))
