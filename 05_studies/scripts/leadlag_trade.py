"""Honest test of the IWM -> QQQ lead-lag that showed up in leadlag_test.py.

Rules of engagement (the standard FINDINGS.md establishes):
  - NON-OVERLAPPING bets only. Overlapping windows inflate t-stats by ~sqrt(overlap).
  - train / validate / test 3-way chronological split. A result must hold on all three.
  - real costs: QQQ 1c spread on ~$600 = 1.7bp round trip; be generous and use 1.0bp.
  - judge against the BASE RATE, and report expected return, not conditional accuracy.
"""
import glob
import numpy as np
import pandas as pd


def load(sym):
    fs = sorted(glob.glob(f"data/minute/{sym}/*.parquet"))
    m = pd.concat([pd.read_parquet(f) for f in fs]).sort_index()
    return m[~m.index.duplicated()]["close"].between_time("09:35", "15:55")


px = pd.DataFrame({s: load(s) for s in ["SPY", "QQQ", "IWM", "DIA"]}).dropna()
lp = np.log(px)

K, H = 30, 60                       # signal window, holding window (minutes)
rows = []
for d, g in lp.groupby(lp.index.date):
    g = g.sort_index()
    if len(g) < 340:
        continue
    # non-overlapping: decision points every H minutes, each needs K minutes of history
    for i in range(K, len(g) - H, H):
        rows.append({
            "date": pd.Timestamp(d), "t": g.index[i],
            "iwm_lag": g.IWM.iloc[i] - g.IWM.iloc[i - K],
            "qqq_lag": g.QQQ.iloc[i] - g.QQQ.iloc[i - K],
            "spy_lag": g.SPY.iloc[i] - g.SPY.iloc[i - K],
            "qqq_fwd": g.QQQ.iloc[i + H] - g.QQQ.iloc[i],
            "spy_fwd": g.SPY.iloc[i + H] - g.SPY.iloc[i],
        })
b = pd.DataFrame(rows)
print(f"non-overlapping bets: {len(b)}  over {b.date.nunique()} sessions "
      f"({b.date.min().date()} .. {b.date.max().date()})")
print(f"bets/day = {len(b)/b.date.nunique():.1f}   "
      f"sd(qqq_fwd) = {b.qqq_fwd.std()*100:.3f}%\n")

n = len(b)
i1, i2 = int(n * .5), int(n * .75)
splits = [("train", b.iloc[:i1]), ("validate", b.iloc[i1:i2]),
          ("test", b.iloc[i2:]), ("FULL", b)]

COST = 1.0e-4
for sig, tgt in [("iwm_lag", "qqq_fwd"), ("iwm_lag", "spy_fwd"),
                 ("qqq_lag", "qqq_fwd"), ("spy_lag", "spy_fwd")]:
    print(f"--- signal = sign({sig})  ->  {tgt} ---")
    for name, s in splits:
        pnl = np.sign(s[sig]) * s[tgt] - COST
        gross = np.sign(s[sig]) * s[tgt]
        t = pnl.mean() / (pnl.std() / np.sqrt(len(pnl)))
        sr = pnl.mean() / pnl.std() * np.sqrt(len(b) / b.date.nunique() * 252)
        print(f"  [{name:8s}] n={len(s):5d} hit={np.mean(gross>0)*100:5.1f}% "
              f"gross={gross.mean()*1e4:+6.2f}bp net={pnl.mean()*1e4:+6.2f}bp "
              f"t={t:+5.2f} SR={sr:+5.2f}")
    print()
