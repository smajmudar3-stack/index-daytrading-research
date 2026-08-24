"""Is the 13:00 -> 15:00 result real, or a half-day artifact?

t = 7.45 with r = 0.318 is far above the noise threshold, and 13:00 appears in
three of the top four pairs. That concentration is the tell: a genuine effect
would not cluster on one clock time in both directions (13:00->15:00 positive,
13:00->14:30 negative).

The suspected cause: on half trading days the market closes at 13:00, but the
minute files carry extended-hours bars out to 19:59. A time-of-day filter of
09:30-16:00 does not exclude those -- so on roughly six days a year the
13:00-16:00 buckets are built from thin post-close prints rather than real
trading.

Three checks:
  1. bars-per-day, to find short sessions directly
  2. the pair's t-stat after removing them
  3. outlier sensitivity -- drop the largest few |moves| and see what survives
"""
import glob
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T, CLOSE_T = pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time()


def load(sym="SPY"):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def panel(df, drop_short=False):
    idx = pd.DatetimeIndex(df.index)
    rth = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)].copy()
    ridx = pd.DatetimeIndex(rth.index)
    rth["day"] = ridx.date

    if drop_short:
        # A full session has ~390 one-minute bars. Anything much shorter is a
        # half day; anything padded with post-close prints still has a real
        # last-trade time well before 16:00 on those days.
        last_real = rth[rth.volume > 0].groupby("day").apply(
            lambda g: pd.DatetimeIndex(g.index).time.max())
        full = last_real[last_real >= pd.Timestamp("15:55").time()].index
        rth = rth[rth["day"].isin(set(full))]
        ridx = pd.DatetimeIndex(rth.index)

    bins = pd.DatetimeIndex(rth.index).floor("30min")
    px = rth.groupby([rth["day"], bins.time])["close"].last().unstack()
    return np.log(px).diff(axis=1).iloc[:, 1:].dropna(how="any")


def report(lr, a, b, label):
    if a not in lr.columns or b not in lr.columns:
        print(f"  {label}: bucket missing"); return
    x, y = lr[a].values, lr[b].values
    sl, _, r, p, se = stats.linregress(x, y)
    t = sl / se if se > 0 else 0
    print(f"  {label:38s} n={len(x):4d}  t={t:+6.2f}  r={r:+.3f}  p={p:.4f}")
    return x, y


def main():
    df = load("SPY")
    A = pd.Timestamp("13:00").time()
    B = pd.Timestamp("15:00").time()

    print("=" * 84)
    print("DIAGNOSING SPY 13:00 -> 15:00  (t = 7.45 in the full-matrix run)")
    print("=" * 84)

    # 1. find short sessions
    idx = pd.DatetimeIndex(df.index)
    rth = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)]
    ridx = pd.DatetimeIndex(rth.index)
    traded = rth[rth.volume > 0]
    last_t = traded.groupby(pd.DatetimeIndex(traded.index).date).apply(
        lambda g: pd.DatetimeIndex(g.index).time.max())
    short = last_t[last_t < pd.Timestamp("15:55").time()]
    print(f"\n  sessions ending before 15:55: {len(short)}")
    for d, t in list(short.items())[:12]:
        print(f"    {d}  last trade {t}")

    print("\n  --- the pair, three ways ---")
    lr_all = panel(df, drop_short=False)
    res = report(lr_all, A, B, "all days (original)")
    lr_cln = panel(df, drop_short=True)
    report(lr_cln, A, B, "excluding short sessions")

    # 3. outlier sensitivity on the cleaned panel
    if A in lr_cln.columns and B in lr_cln.columns:
        x, y = lr_cln[A].values, lr_cln[B].values
        for k in (1, 3, 5, 10):
            keep = np.argsort(-np.abs(x))[k:]
            sl, _, r, p, se = stats.linregress(x[keep], y[keep])
            t = sl / se if se > 0 else 0
            print(f"  {'  after dropping %2d largest |x|' % k:38s} "
                  f"n={len(keep):4d}  t={t:+6.2f}  r={r:+.3f}  p={p:.4f}")

    # 4. does it hold in both halves of the clean sample?
    print("\n  --- split-half stability (clean panel) ---")
    h = len(lr_cln) // 2
    for name, sub in (("first half", lr_cln.iloc[:h]), ("second half", lr_cln.iloc[h:])):
        report(sub, A, B, name)

    # 5. how many pairs beat threshold once short sessions are gone?
    cols = list(lr_cln.columns)
    pairs = [(i, j) for i in range(len(cols)) for j in range(len(cols)) if j > i]
    th = np.sqrt(2 * np.log(len(pairs)))
    beat = 0
    tops = []
    for i, j in pairs:
        sl, _, r, p, se = stats.linregress(lr_cln[cols[i]], lr_cln[cols[j]])
        t = sl / se if se > 0 else 0
        tops.append((abs(t), str(cols[i]), str(cols[j]), t, r))
        beat += abs(t) > th
    tops.sort(reverse=True)
    print(f"\n  clean panel: {beat} of {len(pairs)} pairs beat threshold {th:.2f}")
    for _, a, b, t, r in tops[:5]:
        print(f"    {a} -> {b}:  t={t:+.2f}  r={r:+.3f}")


if __name__ == "__main__":
    main()
