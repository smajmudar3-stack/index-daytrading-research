"""Independent, genuinely-recent check of market intraday momentum on SPY 1-minute data
(2024-07 .. 2026-07) -- a period entirely AFTER both Baltussen et al.'s sample (ends May 2020)
and our SPXW panel (ends May 2024). Tests both specs:
  Gao/Han/Li/Zhou (JFE 2018):  rLH ~ rONFH   (first half hour -> last half hour)
  Baltussen et al. (JFE 2021): rLH ~ rROD    (whole rest of day -> last half hour)
"""
import glob
import numpy as np
import pandas as pd
from scipy import stats

rows = []
for f in sorted(glob.glob("data/minute/SPY/*.parquet")):
    m = pd.read_parquet(f)
    m = m.between_time("09:30", "16:00")
    for day, g in m.groupby(m.index.date):
        if len(g) < 300:
            continue
        c = g["close"]
        try:
            o = c.iloc[0]
            p1000 = c.between_time("09:59", "10:01").iloc[-1]
            p1530 = c.between_time("15:29", "15:31").iloc[-1]
            p1600 = c.iloc[-1]
        except Exception:
            continue
        rows.append({"date": pd.Timestamp(day), "open": o, "p1000": p1000,
                     "p1530": p1530, "close": p1600})

df = pd.DataFrame(rows).set_index("date").sort_index()
df["prev"] = df["close"].shift(1)
df["gap"] = df.index.to_series().diff().dt.days
df = df[(df.gap <= 4) & df.prev.notna()]

df["rLH"] = df.close / df.p1530 - 1
df["rROD"] = df.p1530 / df.prev - 1
df["rONFH"] = df.p1000 / df["open"] - 1          # first half hour, open->10:00
df["rONFH_pc"] = df.p1000 / df.prev - 1          # prev close->10:00 (Gao et al. use this)

g = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
g["gz"] = ((g.gex - g.gex.rolling(252, min_periods=60).mean())
           / g.gex.rolling(252, min_periods=60).std()).shift(1)
df = df.join(g.set_index(g["date"].dt.normalize())[["gz"]], how="left")

print(f"sessions: {len(df)}  {df.index.min().date()} .. {df.index.max().date()}"
      f"   gz coverage: {df.gz.notna().sum()}")
print(f"mean |rLH| = {df.rLH.abs().mean()*1e4:.1f} bps")

half = len(df) // 2
for name, s in [("H1", df.iloc[:half]), ("H2", df.iloc[half:]), ("FULL", df)]:
    for xcol in ["rONFH", "rONFH_pc", "rROD"]:
        x, y = s[xcol].values, s.rLH.values
        m = np.isfinite(x) & np.isfinite(y)
        r = stats.linregress(x[m], y[m])
        pnl = np.sign(s[xcol]) * s.rLH
        print(f"[{name:4s}] rLH ~ {xcol:9s} n={m.sum():4d}  beta={r.slope*100:+6.2f} "
              f"t={r.slope/r.stderr:+5.2f}  R2={r.rvalue**2*100:4.2f}%   "
              f"| sign-trade hit={np.mean(pnl>0)*100:5.1f}% avg={pnl.mean()*1e4:+5.2f}bp "
              f"t={pnl.mean()/(pnl.std()/np.sqrt(len(pnl))):+5.2f}")
    print()

print("--- gz<0 (dealers short gamma) subset, rROD spec ---")
for name, s in [("H1", df.iloc[:half]), ("H2", df.iloc[half:]), ("FULL", df)]:
    ss = s[s.gz < 0]
    if len(ss) < 30:
        print(f"[{name}] n={len(ss)} too few"); continue
    pnl = np.sign(ss.rROD) * ss.rLH
    print(f"[{name:4s}] n={len(ss):4d}  hit={np.mean(pnl>0)*100:5.1f}%  "
          f"avg={pnl.mean()*1e4:+5.2f}bp  t={pnl.mean()/(pnl.std()/np.sqrt(len(pnl))):+5.2f}")
