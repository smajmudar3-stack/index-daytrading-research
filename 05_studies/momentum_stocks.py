"""Where day-traders ACTUALLY operate: volatile individual stocks, not the index.
Test the real day-trader setups on daily OHLCV (open/close = intraday), with realistic
higher single-stock costs (~15 bps round trip). Looking for a genuine, significant edge.

  GAP-AND-GO   : after a big up-gap on volume, does it CONTINUE (close>open) intraday?
  GAP-FADE     : ...or fade?
  MOMENTUM     : after a big up day on high rel-volume, next-day continuation?
  RVOL BREAKOUT: high relative volume + new high -> continuation?
"""
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

RT = 0.0015  # 15 bps round trip — realistic for volatile single-stock intraday

# volatile, high-beta, catalyst-prone day-trader favourites (mix of caps/sectors)
UNIV = ["TSLA","NVDA","AMD","COIN","MARA","RIOT","PLTR","SOFI","AFRM","UPST","RIVN","LCID",
        "NIO","GME","AMC","SMCI","ARM","MSTR","DKNG","ROKU","SNAP","PINS","SHOP","NET",
        "CVNA","W","CHWY","ABNB","DASH","U","RBLX","HOOD","PATH","AI","IONQ","PLUG","FCEL",
        "BBAI","SOUN","TSM","MU","AVGO","SNOW","CRWD","DDOG","ZS","PANW","ANF","DELL"]


def load(tk):
    d = yf.download(tk, start="2019-01-01", interval="1d", progress=False, auto_adjust=False,
                    multi_level_index=False).rename(columns=str.lower)
    if d is None or len(d) < 250:
        return None
    d["prev_close"] = d["close"].shift(1)
    d["gap"] = d["open"]/d["prev_close"] - 1          # overnight gap
    d["intraday"] = d["close"]/d["open"] - 1          # open->close (the day-trade)
    d["day_ret"] = d["close"]/d["prev_close"] - 1
    d["rvol"] = d["volume"]/d["volume"].rolling(20).mean()
    d["hi20"] = d["high"].rolling(20).max()
    return d.dropna()


def agg(frames, mask_fn, ret_fn, label):
    rets = []
    for d in frames:
        m = mask_fn(d)
        if m.sum():
            rets.append(ret_fn(d)[m])
    r = pd.concat(rets).dropna() if rets else pd.Series(dtype=float)
    if len(r) < 50:
        print(f"  {label:44} n={len(r)} (too few)"); return
    t = r.mean()/(r.std()/np.sqrt(len(r)))
    flag = "  <== EDGE t>2" if t >= 2 else ("  (neg)" if t <= -2 else "")
    print(f"  {label:44} ret {r.mean()*100:+.3f}%  t {t:+.1f}  win {(r>0).mean()*100:.0f}%  n={len(r)}{flag}")


def main():
    frames = [d for d in (load(t) for t in UNIV) if d is not None]
    print(f"loaded {len(frames)} volatile stocks, 2019-2026\n")
    print("=== GAP-AND-GO vs FADE (intraday open->close after an up-gap; net 15bps) ===")
    for g in (0.02, 0.04, 0.07):
        agg(frames, lambda d, g=g: d["gap"] > g, lambda d: d["intraday"] - RT, f"gap>{g*100:.0f}% -> LONG intraday (go)")
        agg(frames, lambda d, g=g: d["gap"] > g, lambda d: -d["intraday"] - RT, f"gap>{g*100:.0f}% -> SHORT intraday (fade)")
    print("=== gap-and-go WITH volume confirmation ===")
    for g in (0.03, 0.05):
        agg(frames, lambda d, g=g: (d["gap"] > g) & (d["rvol"] > 1.5), lambda d: d["intraday"] - RT, f"gap>{g*100:.0f}% & RVOL>1.5 -> LONG")
    print("=== MOMENTUM continuation (next-day, after big up day on volume) ===")
    for g in (0.05, 0.10):
        agg(frames, lambda d, g=g: (d["day_ret"] > g) & (d["rvol"] > 1.5),
            lambda d: (d["day_ret"].shift(-1) - RT), f"up>{g*100:.0f}% & RVOL>1.5 -> next-day LONG")
    print("=== RVOL breakout continuation (new 20d high on high volume -> next day) ===")
    agg(frames, lambda d: (d["close"] >= d["hi20"]) & (d["rvol"] > 2.0),
        lambda d: (d["day_ret"].shift(-1) - RT), "20d-high & RVOL>2 -> next-day LONG")
    print("=== down-gap reversal (oversold bounce intraday) ===")
    for g in (-0.04, -0.07):
        agg(frames, lambda d, g=g: d["gap"] < g, lambda d: d["intraday"] - RT, f"gap<{g*100:.0f}% -> LONG intraday (bounce)")


if __name__ == "__main__":
    main()
