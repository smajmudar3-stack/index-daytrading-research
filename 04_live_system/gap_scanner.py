"""gap_scanner.py — the LIVE gap-and-go signal-giver (the validated edge).

Each morning it scans a universe of volatile stocks and flags today's tradeable setups:
  GAP-AND-GO LONG : gap up >3% AND relative volume >1.5x  -> buy at open, sell at close
  DOWN-GAP BOUNCE : gap down >4% (RVOL>1.5)               -> buy at open, sell at close
Backtested (2019-2026, 49 names, net 15bps): gap-go +1.25%/trade t=6.6 (OOS t=3.2, survives
40bps + excluding mega-winners); down-gap bounce +0.65% t=4.9. Writes data/gap_snapshot.json.
Meant for PAPER TRADING first — accuracy shows up over many trades, any single one is noise.
"""
import json
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "gap_snapshot.json")
DB = os.path.join(HERE, "data", "gap_track.db")
UNIV = ["TSLA","NVDA","AMD","COIN","MARA","RIOT","PLTR","SOFI","AFRM","UPST","RIVN","LCID",
        "NIO","GME","AMC","SMCI","ARM","MSTR","DKNG","ROKU","SNAP","PINS","SHOP","NET",
        "CVNA","W","CHWY","ABNB","DASH","U","RBLX","HOOD","PATH","AI","IONQ","PLUG","FCEL",
        "BBAI","SOUN","MU","AVGO","SNOW","CRWD","DDOG","ZS","PANW","DELL"]

GAP_UP, GAP_DN, RVOL_MIN = 0.03, -0.04, 1.5


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
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS paper(date TEXT, ticker TEXT, setup TEXT,
        gap REAL, rvol REAL, open REAL, close REAL, ret REAL, win INT,
        PRIMARY KEY(date,ticker))""")
    for c in cands:  # log at scan time (open + setup); close/ret filled by settle
        con.execute("INSERT OR IGNORE INTO paper(date,ticker,setup,gap,rvol,open) VALUES(?,?,?,?,?,?)",
                    (today, c["ticker"], c["setup"], c["gap_pct"], c["rvol"], c["open"]))
    con.commit(); con.close()


def settle():
    """After the close, fill in each logged candidate's open->close result (paper P&L)."""
    if not os.path.exists(DB):
        return
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    todo = con.execute("SELECT * FROM paper WHERE ret IS NULL").fetchall()
    for r in todo:
        if r["date"] >= datetime.now(ET).strftime("%Y-%m-%d"):
            continue  # only settle past days
        try:
            d = yf.download(r["ticker"], start=r["date"], end=None, period="5d", interval="1d",
                            progress=False, auto_adjust=False, multi_level_index=False).rename(columns=str.lower)
            row = d[d.index.strftime("%Y-%m-%d") == r["date"]]
            if row.empty:
                continue
            op, cl = float(row["open"].iloc[0]), float(row["close"].iloc[0])
            ret = cl/op - 1                      # both setups are LONG open->close
            con.execute("UPDATE paper SET close=?,ret=?,win=? WHERE date=? AND ticker=?",
                        (round(cl, 2), round(ret*100, 2), int(ret > 0), r["date"], r["ticker"]))
        except Exception:
            continue
    con.commit(); con.close()


def track_record():
    if not os.path.exists(DB):
        return {"n": 0}
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    done = con.execute("SELECT * FROM paper WHERE ret IS NOT NULL ORDER BY date DESC").fetchall()
    con.close()
    if not done:
        return {"n": 0}
    rets = [r["ret"] for r in done]
    return {"n": len(done), "win": round(np.mean([r["win"] for r in done])*100),
            "avg": round(np.mean(rets), 2), "total": round(np.sum(rets), 1),
            "recent": [dict(r) for r in done[:15]]}


def run():
    settle()
    rows = []
    for tk in UNIV:
        try:
            r = scan_one(tk)
            if r:
                rows.append(r)
        except Exception:
            continue
    cands = [r for r in rows if r["setup"]]
    cands.sort(key=lambda r: (r["setup"], -abs(r["gap_pct"])))
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
           "epoch": datetime.now(ET).timestamp(),
           "rule": "gap up >3% & RVOL>1.5 = GO long; gap down >4% & RVOL>1.5 = bounce long; "
                   "buy at open, sell at close",
           "candidates": cands, "n_scanned": len(rows),
           "all": sorted(rows, key=lambda r: -r["gap_pct"])}
    _track(cands, datetime.now(ET).strftime("%Y-%m-%d"))
    out["track"] = track_record()
    try:
        import analyst
        out["ai"] = analyst.analyze(out)
    except Exception as e:
        out["ai"] = {"ok": False, "error": str(e)[:80], "text": None}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2, default=str)
    print(f"gap scan {out['as_of']}: {len(cands)} candidates of {len(rows)} scanned")
    for c in cands:
        print(f"  {c['setup']}: {c['ticker']} gap {c['gap_pct']:+.1f}% RVOL {c['rvol']}x "
              f"(open {c['open']}, now {c['last']}, {c['since_open_pct']:+.1f}% since open)")
    return out


if __name__ == "__main__":
    run()
