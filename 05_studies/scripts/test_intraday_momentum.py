"""Baltussen/Da/Lammers/Martens (JFE 2021) market intraday momentum, tested on our own
1,919 sessions of real SPX spot (from data/spxw/data_opt.parquet, 30-min grid 2016-09..2024-05).

Spec (theirs, exactly):
  rLH  = last-half-hour return   = P(16:00)/P(15:30) - 1
  rROD = rest-of-day return      = P(15:30)/P_prev(16:00) - 1
  H0: beta_ROD = 0.  They report beta=6.63 (t=4.78), R2=3.58% on SPX futures 1996-2020
      *conditional on dealer net gamma < 0*; beta=0.82 (t=1.03) when net gamma >= 0.

Also tests the tradeable version: sign(rROD) -> position in last 30 min, and the GEX split,
under a train/validate/test 3-way split (the standard this repo now holds itself to).
"""
import numpy as np
import pandas as pd
from scipy import stats

d = pd.read_parquet(
    "data/spxw/data_opt.parquet",
    columns=["quote_date", "quote_time", "active_underlying_price"],
)
d["quote_time"] = d["quote_time"].astype(str)
px = (d.groupby(["quote_date", "quote_time"])["active_underlying_price"]
        .first().unstack())
px = px.sort_index()

# keep only sessions that actually have both 15:30 and 16:00, THEN take the previous
# such session's close (otherwise shift(1) silently propagates NaNs and halves the sample)
core = px[["15:30:00", "16:00:00"]].dropna()
core.columns = ["p1530", "p1600"]
core["prev"] = core["p1600"].shift(1)
core["gap_days"] = core.index.to_series().diff().dt.days
core = core[core.gap_days <= 4]                      # no month-long holes

df = core.join(px[["10:00:00", "15:00:00"]]).rename(
    columns={"10:00:00": "p1000", "15:00:00": "p1500"}).dropna(subset=["prev"])

# drop day-boundary gaps > 4 calendar days (long holidays) -- prev close still valid, keep.
df["rLH"] = df.p1600 / df.p1530 - 1.0
df["rROD"] = df.p1530 / df.prev - 1.0
df["rONFH"] = df.p1000 / df.prev - 1.0          # ~ first half hour proxy (open->10:00)
df["rSLH"] = df.p1530 / df.p1500 - 1.0          # second-to-last half hour
df = df[(df.rROD.abs() < 0.12) & (df.rLH.abs() < 0.08)]

# dealer gamma (SqueezeMetrics GEX; positive = dealers long gamma). Lagged 1 day.
g = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
g["gz"] = ((g.gex - g.gex.rolling(252, min_periods=60).mean())
           / g.gex.rolling(252, min_periods=60).std()).shift(1)
g["gex_lag"] = g.gex.shift(1)
gmap = g.set_index(g["date"].dt.normalize())[["gz", "gex_lag"]]
df = df.join(gmap, how="left")

n = len(df)
print(f"sessions: {n}  {df.index.min().date()} .. {df.index.max().date()}")
print(f"mean |rLH| = {df.rLH.abs().mean()*1e4:.1f} bps   sd(rLH) = {df.rLH.std()*1e4:.1f} bps")

i1, i2 = int(n * 0.5), int(n * 0.75)
splits = {"train": df.iloc[:i1], "validate": df.iloc[i1:i2], "test": df.iloc[i2:],
          "FULL": df}


def reg(y, x, label):
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 40:
        return f"{label:34s} n={len(x):5d}  (too few)"
    r = stats.linregress(x, y)
    beta = r.slope * 100          # same scaling as the paper (x100)
    return (f"{label:34s} n={len(x):5d}  beta={beta:7.2f}  t={r.slope/r.stderr:+6.2f}  "
            f"R2={r.rvalue**2*100:5.2f}%")


print("\n--- Regression rLH ~ rROD  (paper: beta 6.63, t 4.78 on neg-gamma days) ---")
for name, s in splits.items():
    print(reg(s.rLH, s.rROD, f"[{name}] all days"))

print("\n--- Split by dealer gamma z-score (gz<0 = dealers short gamma = momentum) ---")
for name, s in splits.items():
    lo = s[s.gz < 0]; hi = s[s.gz >= 0]
    print(reg(lo.rLH, lo.rROD, f"[{name}] gz<0  (short gamma)"))
    print(reg(hi.rLH, hi.rROD, f"[{name}] gz>=0 (long gamma)"))

print("\n--- Sign-based trade: long/short MES for the last 30 min on sign(rROD) ---")
print("    (delta-1, no options. ES round-trip cost ~0.5-1.0 bp of notional.)")
for name, s in splits.items():
    for cond, tag in [(s.index == s.index, "all"), (s.gz < 0, "gz<0"), (s.gz >= 0, "gz>=0")]:
        ss = s[cond]
        if len(ss) < 40:
            continue
        pnl = np.sign(ss.rROD) * ss.rLH
        t = pnl.mean() / (pnl.std() / np.sqrt(len(pnl)))
        ann = pnl.mean() * 252
        sharpe = pnl.mean() / pnl.std() * np.sqrt(252)
        print(f"[{name:8s}] {tag:6s} n={len(ss):5d}  hit={np.mean(pnl>0)*100:5.1f}%  "
              f"avg={pnl.mean()*1e4:+6.2f}bp  t={t:+5.2f}  ann={ann*100:+6.2f}%  SR={sharpe:+5.2f}")

print("\n--- Same, net of 1.0 bp round-trip cost ---")
for name, s in splits.items():
    ss = s[s.gz < 0]
    if len(ss) < 40:
        continue
    pnl = np.sign(ss.rROD) * ss.rLH - 1e-4
    t = pnl.mean() / (pnl.std() / np.sqrt(len(pnl)))
    print(f"[{name:8s}] gz<0 net n={len(ss):5d}  avg={pnl.mean()*1e4:+6.2f}bp  t={t:+5.2f}  "
          f"SR={pnl.mean()/pnl.std()*np.sqrt(252):+5.2f}")

print("\n--- Magnitude check: is the conditional move anywhere near the 0.3% 0DTE target? ---")
for q in [0.5, 0.75, 0.9, 0.95]:
    thr = df.rROD.abs().quantile(q)
    ss = df[(df.rROD.abs() >= thr) & (df.gz < 0)]
    if len(ss) < 30:
        continue
    pnl = np.sign(ss.rROD) * ss.rLH
    print(f"|rROD| >= {thr*100:5.2f}%  & gz<0 : n={len(ss):4d}  "
          f"E[rLH signed]={pnl.mean()*1e4:+6.2f}bp   "
          f"P(|rLH|>0.30%)={np.mean(ss.rLH.abs()>0.003)*100:4.1f}%")
