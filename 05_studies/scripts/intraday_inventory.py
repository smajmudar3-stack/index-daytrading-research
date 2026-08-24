"""What intraday data can we actually test a directional rule against?

Worth knowing BEFORE the research comes back: a rule we cannot evaluate is not
a finding. Sample size is the binding constraint here -- time-of-day effects
need many days, and two years of minute bars is ~500 of them, which is thin for
anything conditioned on a specific 5-minute bucket.
"""
import glob
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")


def main():
    print("=" * 78)
    print("MINUTE BARS")
    print("=" * 78)
    for sym in sorted(os.listdir(MIN)):
        d = os.path.join(MIN, sym)
        if not os.path.isdir(d):
            continue
        files = sorted(glob.glob(os.path.join(d, "*.parquet")))
        if not files:
            continue
        first, last = pd.read_parquet(files[0]), pd.read_parquet(files[-1])
        tcol = next((c for c in first.columns
                     if "time" in c.lower() or "date" in c.lower()), None)
        n = sum(len(pd.read_parquet(f)) for f in files)
        print(f"\n  {sym}: {len(files)} months, {n:,} bars")
        print(f"    columns: {list(first.columns)}")
        if tcol:
            t0 = pd.to_datetime(first[tcol]).min()
            t1 = pd.to_datetime(last[tcol]).max()
            print(f"    range  : {t0}  ->  {t1}")
            # Trading days is the sample size that matters for any rule
            # conditioned on time-of-day.
            days = set()
            for f in files:
                days |= set(pd.to_datetime(pd.read_parquet(f)[tcol]).dt.date)
            print(f"    trading days: {len(days):,}   <-- the real sample size")

    print("\n" + "=" * 78)
    print("SPXW REAL-QUOTE OPTION CHAINS")
    print("=" * 78)
    p = os.path.join(ROOT, "data", "spxw", "data_opt.parquet")
    if os.path.exists(p):
        df = pd.read_parquet(p)
        print(f"  rows: {len(df):,}")
        print(f"  columns: {list(df.columns)}")
        for c in df.columns:
            if "date" in c.lower() or "time" in c.lower():
                s = pd.to_datetime(df[c], errors="coerce")
                print(f"    {c}: {s.min()} -> {s.max()}  ({s.dt.date.nunique():,} days)")


if __name__ == "__main__":
    main()
