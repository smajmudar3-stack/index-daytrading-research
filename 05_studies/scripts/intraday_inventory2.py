"""Second pass: the timestamps live where the first pass did not look.

Minute bars carry their timestamp in the INDEX, not a column, and SPXW's
quote_time is a time-of-day field that does not parse as a full datetime. Both
matter, because intraday time-of-day is exactly the axis these rules are
conditioned on.
"""
import glob
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")


def main():
    print("=" * 78)
    print("MINUTE BARS -- timestamp is the index")
    print("=" * 78)
    for sym in ("SPY", "QQQ", "IWM", "DIA"):
        files = sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))
        if not files:
            continue
        a, z = pd.read_parquet(files[0]), pd.read_parquet(files[-1])
        days, n = set(), 0
        for f in files:
            df = pd.read_parquet(f)
            n += len(df)
            days |= set(pd.DatetimeIndex(df.index).date)
        print(f"\n  {sym}: {n:,} bars over {len(days):,} trading days")
        print(f"    index dtype : {a.index.dtype}")
        print(f"    range       : {a.index.min()}  ->  {z.index.max()}")
        idx = pd.DatetimeIndex(a.index)
        print(f"    session     : {idx.time.min()} -> {idx.time.max()}  "
              f"(bars/day ~ {n // max(len(days), 1)})")

    print("\n" + "=" * 78)
    print("SPXW -- quote_time is time-of-day")
    print("=" * 78)
    df = pd.read_parquet(os.path.join(ROOT, "data", "spxw", "data_opt.parquet"),
                         columns=["quote_date", "quote_time", "mnes_rel", "bas",
                                  "delta", "active_underlying_price"])
    print(f"  rows {len(df):,}")
    print(f"  quote_time sample: {df.quote_time.dropna().unique()[:12]}")
    print(f"  distinct quote_time values: {df.quote_time.nunique()}")
    d = pd.to_datetime(df.quote_date)
    print(f"  dates: {d.min().date()} -> {d.max().date()}  ({d.dt.date.nunique():,} days)")
    print(f"  underlying: {df.active_underlying_price.min():.0f} -> "
          f"{df.active_underlying_price.max():.0f}")
    print(f"  bid-ask spread (bas): median {df.bas.median():.3f}, "
          f"p90 {df.bas.quantile(0.9):.3f}")


if __name__ == "__main__":
    main()
