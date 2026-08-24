"""One day is generating the entire intraday "edge". Identify it and re-test.

Dropping the single largest 13:00 move collapsed t from +7.45 to +0.84, and the
effect lives entirely in the first half of the sample. That is the signature of
a single extreme session, not a tradeable regularity: on a day when the market
moves violently, every half-hour bucket moves together, which manufactures
correlation across MANY bucket pairs at once. That is why 13:00 appeared in
three of the top four pairs with inconsistent signs.

This script:
  1. names the day
  2. re-runs the full pair matrix with that day removed
  3. re-runs it on Spearman rank correlation, which is immune to single outliers
  4. compares the count of threshold-beating pairs against what noise predicts
"""
import glob
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T, CLOSE_T = pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time()


def panel(sym="SPY"):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    rth = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)].copy()
    rth["day"] = pd.DatetimeIndex(rth.index).date
    bins = pd.DatetimeIndex(rth.index).floor("30min")
    px = rth.groupby([rth["day"], bins.time])["close"].last().unstack()
    return np.log(px).diff(axis=1).iloc[:, 1:].dropna(how="any")


def matrix(lr, method="pearson"):
    cols = list(lr.columns)
    pairs = [(i, j) for i in range(len(cols)) for j in range(len(cols)) if j > i]
    th = np.sqrt(2 * np.log(len(pairs)))
    out = []
    for i, j in pairs:
        x, y = lr[cols[i]].values, lr[cols[j]].values
        if method == "spearman":
            r, p = stats.spearmanr(x, y)
            t = r * np.sqrt((len(x) - 2) / max(1e-12, 1 - r * r))
        else:
            sl, _, r, p, se = stats.linregress(x, y)
            t = sl / se if se > 0 else 0.0
        out.append((str(cols[i]), str(cols[j]), t, r))
    res = pd.DataFrame(out, columns=["pred", "out", "t", "r"])
    return res.sort_values("t", key=abs, ascending=False), th, len(pairs)


def summarise(tag, lr, method="pearson"):
    res, th, n = matrix(lr, method)
    beat = (res.t.abs() > th).sum()
    # Under the null, the number of pairs exceeding |t|>th is ~n*P(|t|>th).
    exp = n * 2 * (1 - stats.norm.cdf(th))
    print(f"\n  {tag}  [{method}]  n_days={len(lr)}")
    print(f"    {beat} of {n} pairs beat |t|>{th:.2f}   (noise predicts ~{exp:.1f})")
    for _, q in res.head(4).iterrows():
        print(f"      {q.pred} -> {q.out}:  t={q.t:+.2f}  r={q.r:+.3f}")
    return beat, exp


def main():
    lr = panel("SPY")
    A, B = pd.Timestamp("13:00").time(), pd.Timestamp("15:00").time()

    print("=" * 84)
    print("THE OUTLIER DAY")
    print("=" * 84)
    big = lr[A].abs().sort_values(ascending=False).head(6)
    print(f"  largest 13:00-bucket moves:")
    for d, v in big.items():
        print(f"    {d}   13:00 bucket {lr.loc[d, A]*100:+7.2f}%   "
              f"15:00 bucket {lr.loc[d, B]*100:+7.2f}%")

    worst = big.index[0]
    print(f"\n  -> the single day driving t=+7.45 is {worst}")

    print("\n" + "=" * 84)
    print("MATRIX WITH AND WITHOUT IT")
    print("=" * 84)
    summarise("all days", lr)
    summarise(f"excluding {worst}", lr.drop(index=worst))
    summarise("excluding 5 largest-range days",
              lr.drop(index=lr.abs().max(axis=1).sort_values(ascending=False).head(5).index))
    # Rank correlation cannot be moved by one extreme value.
    summarise("all days", lr, method="spearman")

    print("\n" + "=" * 84)
    print("  A real intraday effect would survive removing one session.")
    print("  If the threshold-beating count falls to roughly what noise predicts,")
    print("  the apparent predictability was one day of shared volatility.")
    print("=" * 84)


if __name__ == "__main__":
    main()
