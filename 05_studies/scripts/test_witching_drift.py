"""Test the "derivative payoff bias" / third-Friday AM-settlement drift on our own SPX data.

Claim (Baltussen, Terstegge & Whelan, AFA 2025, SSRN 4562800): SPX drifts UP into the
third-Friday AM settlement (SOQ) and reverts during the session.
  Thu close -> Fri open   +26.4 bps (t=4.36)  [quarterly / triple witch]
  Fri open  -> Fri close  -37.2 bps (t=-3.54) [quarterly]
  off-quarterly open->close only -6.7 bps (t=-1.03, insignificant)
Bogousslavsky's AFA discussion replicates on SPY and gets a much smaller overnight leg when
measured to the 10:00 midquote: +7.99 bps (t=1.94), and 9:30->noon of -13.5 bps (t=-3.18).

Our SPXW panel's first grid point is 10:00, so we test exactly Bogousslavsky's weaker
specification: prev close -> 10:00, and 10:00 -> 16:00 close.
"""
import numpy as np
import pandas as pd
from scipy import stats

d = pd.read_parquet("data/spxw/data_opt.parquet",
                    columns=["quote_date", "quote_time", "active_underlying_price"])
d["quote_time"] = d["quote_time"].astype(str)
px = (d.groupby(["quote_date", "quote_time"])["active_underlying_price"]
        .first().unstack().sort_index())

# The same-day leg (10:00 -> close) needs no prior session, so build it on the WIDEST
# possible sample; the overnight leg is only defined where the previous session is present
# and adjacent, which costs a lot of rows.
df = px[["10:00:00", "16:00:00"]].dropna()
df.columns = ["p1000", "close"]
prev = df["close"].shift(1)
adj = df.index.to_series().diff().dt.days <= 4

df["session"] = df.close / df.p1000 - 1                                 # 10:00 -> close
df["overnight"] = np.where(adj, df.p1000 / prev - 1, np.nan)            # prev close -> 10:00
df["full"] = np.where(adj, df.close / prev - 1, np.nan)

# third Friday of the month; quarterly = Mar/Jun/Sep/Dec (triple witching)
idx = df.index
df["dow"] = idx.dayofweek
df["dom"] = idx.day
df["month"] = idx.month
df["third_fri"] = (df.dow == 4) & (df.dom >= 15) & (df.dom <= 21)
df["quarterly"] = df.third_fri & df.month.isin([3, 6, 9, 12])
df["monthly_only"] = df.third_fri & ~df.quarterly

print(f"sessions {len(df)}  {idx.min().date()} .. {idx.max().date()}")
print(f"third Fridays: {df.third_fri.sum()}  (quarterly {df.quarterly.sum()}, "
      f"other monthly {df.monthly_only.sum()})\n")


def show(mask, label):
    s = df[mask]
    if len(s) < 5:
        print(f"{label:22s} n={len(s)} too few"); return
    for col, nm in [("overnight", "prev close->10:00"), ("session", "10:00->close"),
                    ("full", "prev close->close")]:
        v = s[col].dropna()
        if len(v) < 4:
            print(f"{label:22s} {nm:18s} n={len(v)} too few"); continue
        t = v.mean() / (v.std() / np.sqrt(len(v)))
        print(f"{label:22s} {nm:18s} n={len(v):4d}  mean={v.mean()*1e4:+7.2f}bp  "
              f"t={t:+5.2f}  median={v.median()*1e4:+7.2f}bp  pos={np.mean(v>0)*100:4.1f}%")
    print()


show(df.quarterly, "QUARTERLY (witch)")
show(df.monthly_only, "monthly non-quarterly")
show(df.third_fri, "all third Fridays")
show(~df.third_fri, "all other days")

print("--- difference vs the all-other-days baseline (Welch t) ---")
base = df[~df.third_fri]
for mask, label in [(df.quarterly, "quarterly"), (df.third_fri, "all third Fri")]:
    s = df[mask]
    for col in ["overnight", "session"]:
        tt = stats.ttest_ind(s[col].dropna(), base[col].dropna(), equal_var=False)
        print(f"{label:14s} {col:10s} diff={(s[col].mean()-base[col].mean())*1e4:+7.2f}bp  "
              f"t={tt.statistic:+5.2f}  p={tt.pvalue:.3f}")

print("\n--- split-half stability of the quarterly session leg ---")
q = df[df.quarterly]
h = len(q) // 2
for nm, s in [("first half", q.iloc[:h]), ("second half", q.iloc[h:])]:
    v = s.session.dropna()
    print(f"{nm:12s} n={len(v):3d}  mean={v.mean()*1e4:+7.2f}bp  "
          f"t={v.mean()/(v.std()/np.sqrt(len(v))):+5.2f}")
