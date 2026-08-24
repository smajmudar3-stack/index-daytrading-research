"""Intraday VWAP mean-reversion — the opposite mechanism to breakout.

Session-anchored VWAP from 09:30. When price stretches k * (intraday sigma) from VWAP,
fade it (buy below / sell above), exit on a VWAP touch, an EOD close, or a stop at 2k.
If the index mean-reverts intraday (which the ORB failure hints at), this is where an edge
would live. Costs 3 bps round trip.
"""
import glob
import numpy as np
import pandas as pd

RT = 0.0003


def load_minute(tk):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"data/minute/{tk}/*.parquet"))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "15:59")
    df["day"] = df.index.date
    return df


def vwap_reversion(df, k=2.0, entry_after="09:45", stop_k=4.0):
    trades = []
    for day, g in df.groupby("day"):
        g = g.copy()
        if len(g) < 60:
            continue
        tp = (g["high"] + g["low"] + g["close"]) / 3
        cumv = g["volume"].cumsum()
        vwap = (tp * g["volume"]).cumsum() / cumv.replace(0, np.nan)
        dev = g["close"] - vwap
        sig = dev.expanding(min_periods=15).std()
        z = dev / sig
        in_pos = 0; entry = 0.0; ez = 0.0
        for ts, (c, zz, vw) in zip(g.index, zip(g["close"], z, vwap)):
            if np.isnan(zz):
                continue
            t = ts.strftime("%H:%M")
            if in_pos == 0 and t >= entry_after and t < "15:45":
                if zz <= -k:
                    in_pos = 1; entry = c; ez = zz
                elif zz >= k:
                    in_pos = -1; entry = c; ez = zz
            elif in_pos != 0:
                hit_vwap = (in_pos == 1 and c >= vw) or (in_pos == -1 and c <= vw)
                stopped = (in_pos == 1 and zz <= -stop_k) or (in_pos == -1 and zz >= stop_k)
                eod = t >= "15:58"
                if hit_vwap or stopped or eod:
                    trades.append(in_pos * (c / entry - 1) - RT)
                    in_pos = 0
    return pd.Series(trades)


def report(name, r):
    r = r.dropna()
    if len(r) < 20:
        print(f"  {name:34} n={len(r)} too few"); return
    exp = r.mean(); wl = (r > 0).mean()
    g = r[r > 0].sum(); l = -r[r < 0].sum()
    pf = g / l if l > 0 else np.inf
    t = r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    print(f"  {name:34} exp {exp*100:+.3f}%  win% {wl*100:4.1f}  PF {pf:4.2f}  t {t:+4.1f}  "
          f"Sharpe(trade) {sh:+4.1f}  n={len(r)}")


for tk in ["QQQ", "SPY"]:
    df = load_minute(tk)
    print(f"\n===== {tk}  ({df['day'].nunique()} sessions) — VWAP mean-reversion =====")
    for k in (1.5, 2.0, 2.5):
        report(f"fade at {k}sigma, exit VWAP", vwap_reversion(df, k=k))
