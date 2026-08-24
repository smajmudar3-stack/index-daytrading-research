"""The actual Gao-Han-Li-Zhou intraday momentum rule, on minute bars.

The SPXW panel starts at 10:00, so it can only proxy the published rule. The
published rule is specifically:

    first half-hour return (09:30 -> 10:00) predicts
    last  half-hour return (15:30 -> 16:00)

with the trade being: at 15:30, go long if the first half-hour was up, short if
it was down, and close at 16:00. Minute bars carry the 09:30 open, so the real
rule is testable here -- 500 trading days of SPY/QQQ/IWM/DIA, 2024-2026, which
is entirely OUT OF SAMPLE relative to the 2018 publication.

That last point is the whole value of this test. Intraday seasonality effects
are notorious for dying once published, and this data postdates publication by
six years.

Also tested: the twelfth-half-hour predictor the paper prefers (14:30->15:00),
and every other ordered bucket pair, with the same multiple-testing threshold
used elsewhere in this repo.
"""
import glob
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
RTH_OPEN, RTH_CLOSE = pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time()


def half_hour_panel(sym):
    """Regular-hours half-hour returns, one row per day."""
    frames = []
    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet"))):
        frames.append(pd.read_parquet(f))
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    idx = pd.DatetimeIndex(df.index)
    # Regular trading hours only. Extended-hours bars are thin and would
    # contaminate an open-to-close bucket scheme.
    df = df[(idx.time >= RTH_OPEN) & (idx.time <= RTH_CLOSE)]
    idx = pd.DatetimeIndex(df.index)
    df = df.assign(day=idx.date, t=idx.time)

    # Last close within each half-hour bin, plus the true 09:30 open.
    bins = pd.to_datetime(df.index).floor("30min")
    px = df.groupby([df.day, bins.time])["close"].last().unstack()
    opens = df[df.t == RTH_OPEN].groupby("day")["open"].first()
    px.insert(0, "OPEN", opens)
    px = px.dropna(how="any")
    return np.log(px).diff(axis=1).iloc[:, 1:]


def main():
    print("=" * 90)
    print("GAO, HAN, LI & ZHOU (2018) INTRADAY MOMENTUM -- OUT-OF-SAMPLE TEST")
    print("=" * 90)
    print("  Rule: at 15:30 take the sign of the 09:30-10:00 return, hold to 16:00.")
    print("  Data postdates the 2018 publication by six years.\n")

    for sym in ("SPY", "QQQ", "IWM", "DIA"):
        try:
            lr = half_hour_panel(sym)
        except (ValueError, KeyError) as e:
            print(f"  {sym}: skipped ({e})")
            continue
        cols = list(lr.columns)
        if len(cols) < 4:
            print(f"  {sym}: too few buckets"); continue
        first, last = cols[0], cols[-1]
        x, y = lr[first].values, lr[last].values

        sl, ic, r, p, se = stats.linregress(x, y)
        t = sl / se if se > 0 else 0.0

        # The tradeable version: sign-following, which is what you can execute.
        pos = np.sign(x)
        pnl = pos * y
        n = len(pnl)
        hit = (pnl > 0).mean()
        tt = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(n)) if pnl.std() > 0 else 0.0

        print(f"  {sym}  ({n} days, buckets {first} .. {last})")
        print(f"    regression  : r = {r:+.4f}   t = {t:+.2f}   p = {p:.3f}")
        print(f"    sign-follow : hit {hit*100:5.1f}%   mean {pnl.mean()*1e4:+6.2f} bp/day"
              f"   t = {tt:+.2f}")
        # A round trip in SPY options costs far more than a few bp; state the bar.
        print(f"    total over {n} days: {pnl.sum()*1e4:+.0f} bp "
              f"({'below' if abs(pnl.mean()*1e4) < 5 else 'above'} a 5bp cost floor)\n")

    # Full matrix on SPY, same discipline as the SPXW test.
    lr = half_hour_panel("SPY")
    cols = list(lr.columns)
    pairs = [(i, j) for i in range(len(cols)) for j in range(len(cols)) if j > i]
    thresh = np.sqrt(2 * np.log(len(pairs)))
    rows = []
    for i, j in pairs:
        sl, _, r, p, se = stats.linregress(lr[cols[i]], lr[cols[j]])
        rows.append((str(cols[i]), str(cols[j]), sl / se if se > 0 else 0, r))
    res = pd.DataFrame(rows, columns=["pred", "out", "t", "r"])
    res = res.sort_values("t", key=abs, ascending=False)

    print("=" * 90)
    print(f"  SPY FULL MATRIX: {len(pairs)} pairs, noise threshold "
          f"sqrt(2*ln({len(pairs)})) = {thresh:.2f}")
    print("=" * 90)
    print(f"  {'predictor':>10s} -> {'outcome':<10s} {'t':>7s} {'r':>8s}")
    for _, q in res.head(8).iterrows():
        flag = "  <-- beats threshold" if abs(q.t) > thresh else ""
        print(f"  {q.pred:>10s} -> {q.out:<10s} {q.t:7.2f} {q.r:8.3f}{flag}")
    n_beat = (res.t.abs() > thresh).sum()
    print(f"\n  {n_beat} of {len(pairs)} pairs beat the threshold "
          f"({'consistent with pure noise' if n_beat <= 1 else 'worth a closer look'}).")


if __name__ == "__main__":
    main()
