"""
Base-rate check for the conditional dip-buying result.

Question: the reported 64-70% win rates at a 21-day horizon on SPY -- are they
above the UNCONDITIONAL base rate, or are they the base rate?

Rule 3 of the methodology: conditional accuracy is not expected return.
"""
import pandas as pd
import numpy as np

from idt import paths

PANEL = "swing/panel.parquet"  # path under DATA_ROOT, resolved at the read site
H = 21  # trading days


SPLITS = {
    "train  1998-2011": ("1998-01-01", "2011-12-31"),
    "valid  2012-2019": ("2012-01-01", "2019-12-31"),
    "test   2020-2026": ("2020-01-01", "2026-12-31"),
    "ALL    1998-2026": ("1998-01-01", "2026-12-31"),
}


def stats(mask, lo, hi):
    m = (df.date >= lo) & (df.date <= hi) & mask & df.fwd.notna()
    x = df.loc[m, "fwd"]
    if len(x) < 5:
        return None
    return len(x), (x > 0).mean() * 100, x.mean() * 100, x.median() * 100


def main():
    # these were module-level before the guard; the functions above
    # still read them, so they stay global — only the work moved.
    global df

    d = pd.read_parquet(paths.require_data(PANEL))
    spy = d[d.ticker == "SPY"].sort_values("date").reset_index(drop=True)
    vix = d[d.ticker == "^VIX"].sort_values("date")[["date", "close"]].rename(
        columns={"close": "vix"})
    vix3m = d[d.ticker == "^VIX3M"].sort_values("date")[["date", "close"]].rename(
        columns={"close": "vix3m"})

    df = spy[["date", "close"]].merge(vix, on="date", how="left").merge(
        vix3m, on="date", how="left")

    # forward 21-trading-day return
    df["fwd"] = df["close"].shift(-H) / df["close"] - 1.0

    # features
    df["ma50"] = df["close"].rolling(50).mean()
    df["ma200"] = df["close"].rolling(200).mean()
    df["above50"] = df["close"] > df["ma50"]
    df["golden"] = df["ma50"] > df["ma200"]
    df["ret3"] = df["close"] / df["close"].shift(3) - 1.0
    df["ret1"] = df["close"].pct_change()
    # "dip3": 3-day decline
    df["dip3"] = df["ret3"] < 0
    # 3 consecutive down days (stricter reading of dip3)
    df["dip3c"] = (df["ret1"] < 0) & (df["ret1"].shift(1) < 0) & (df["ret1"].shift(2) < 0)
    # VIX term-structure backwardation
    df["backward"] = df["vix"] > df["vix3m"]

    CONDS = {
        "UNCONDITIONAL (base rate)": pd.Series(True, index=df.index),
        "dip3 (3d ret < 0)": df.dip3,
        "dip3c (3 down days)": df.dip3c,
        "above50 only": df.above50,
        "golden only": df.golden,
        "above50 + dip3": df.above50 & df.dip3,
        "above50 + dip3c": df.above50 & df.dip3c,
        "golden + dip3": df.golden & df.dip3,
        "backward + golden": df.backward & df.golden,
        "backward + golden + dip3": df.backward & df.golden & df.dip3,
    }

    for name, (lo, hi) in SPLITS.items():
        print(f"\n=== {name} ===")
        print(f"{'condition':<28}{'n':>6}{'win%':>8}{'mean%':>9}{'med%':>8}"
              f"{'edge_vs_base_pp':>17}{'ret_edge_pp':>13}")
        base = stats(CONDS["UNCONDITIONAL (base rate)"], lo, hi)
        for cname, cmask in CONDS.items():
            s = stats(cmask, lo, hi)
            if s is None:
                continue
            n, win, mean, med = s
            dwin = win - base[1]
            dret = mean - base[2]
            print(f"{cname:<28}{n:>6}{win:>8.1f}{mean:>9.2f}{med:>8.2f}"
                  f"{dwin:>17.1f}{dret:>13.2f}")

    # How many INDEPENDENT observations are behind these numbers?
    print("\n=== effective sample size ===")
    for name, (lo, hi) in SPLITS.items():
        m = (df.date >= lo) & (df.date <= hi) & df.above50 & df.dip3 & df.fwd.notna()
        n = int(m.sum())
        span_days = (df.loc[m, "date"].max() - df.loc[m, "date"].min()).days if n else 0
        # non-overlapping equivalent: 21-day holding periods over the span
        indep = span_days / 30.4 / (H / 21.0) if span_days else 0
        print(f"{name}: n={n} overlapping signals, "
              f"~{indep:.0f} non-overlapping 21-day windows in the span")


if __name__ == "__main__":
    main()
