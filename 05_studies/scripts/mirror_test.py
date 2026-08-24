"""The mirror test: is a breakout "hit rate" directional, or just volatility?

The most useful diagnostic to come out of the pattern literature. ES 5-minute
opening-range breakouts reach a 1.0x extension 64.3% of the time to the upside
and 62.9% to the downside. Quoted alone, "64% hit rate" sounds like a
directional edge. Quoted next to its mirror image, it is obviously a statement
about how far price travels, not which way.

Any conditional statistic that is the same in both directions contains no
directional information. This runs that check on our own SPY/QQQ minute bars so
the conclusion rests on our data rather than on someone else's table.

Three measurements per instrument:
  1. after the FIRST break of the 09:30-10:00 range, does the close finish in
     the direction of that break -- separately for up-breaks and down-breaks
  2. does price reach a 1.0x range extension -- up vs down
  3. the drift-adjusted version: the up-minus-down gap compared against the
     unconditional share of up days, which is where equity drift lives
"""
import glob
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T = pd.Timestamp("09:30").time()
ORB_END = pd.Timestamp("10:00").time()
CLOSE_T = pd.Timestamp("16:00").time()


def sessions(sym):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    df = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)].copy()
    df["day"] = pd.DatetimeIndex(df.index).date
    df["t"] = pd.DatetimeIndex(df.index).time
    for d, g in df.groupby("day"):
        if g["t"].iloc[-1] < pd.Timestamp("15:55").time():
            continue                      # half day
        orb = g[g.t <= ORB_END]
        rest = g[g.t > ORB_END]
        if len(orb) < 25 or len(rest) < 100:
            continue
        yield d, orb, rest


def main():
    print("=" * 90)
    print("MIRROR TEST -- opening range 09:30-10:00, first break, outcome by close")
    print("=" * 90)

    for sym in ("SPY", "QQQ"):
        rows = []
        for d, orb, rest in sessions(sym):
            hi, lo = orb["high"].max(), orb["low"].min()
            rng = hi - lo
            if rng <= 0:
                continue
            close = rest["close"].iloc[-1]
            up_i = rest.index[rest["high"] > hi]
            dn_i = rest.index[rest["low"] < lo]
            first_up = up_i[0] if len(up_i) else None
            first_dn = dn_i[0] if len(dn_i) else None
            if first_up is None and first_dn is None:
                continue
            if first_dn is None or (first_up is not None and first_up < first_dn):
                d_break, ref = +1, hi
            else:
                d_break, ref = -1, lo
            # extension of one full range beyond the break level
            if d_break > 0:
                ext = rest["high"].max() >= hi + rng
            else:
                ext = rest["low"].min() <= lo - rng
            rows.append(dict(day=d, dirn=d_break,
                             follow=np.sign(close - ref) == d_break,
                             ext=bool(ext)))

        r = pd.DataFrame(rows)
        up, dn = r[r.dirn > 0], r[r.dirn < 0]
        print(f"\n  {sym}  ({len(r)} sessions with a break)")
        print(f"    {'':22s} {'UP break':>12s} {'DOWN break':>12s} {'gap':>9s}")
        for lab, col in (("closes beyond break", "follow"), ("reaches 1.0x ext", "ext")):
            a, b = up[col].mean(), dn[col].mean()
            print(f"    {lab:22s} {a*100:11.1f}% {b*100:11.1f}% {(a-b)*100:+8.1f}pp")
        print(f"    {'n':22s} {len(up):11,d}  {len(dn):11,d}")

        # Where the asymmetry actually comes from.
        base_up = (r.dirn > 0).mean()
        print(f"    first break is UP on {base_up*100:.1f}% of days")
        se = np.sqrt(0.25 * (1 / max(len(up), 1) + 1 / max(len(dn), 1))) * 100
        gap = (up["follow"].mean() - dn["follow"].mean()) * 100
        print(f"    follow-through gap {gap:+.1f}pp against a standard error of "
              f"{se:.1f}pp  ->  {'inside noise' if abs(gap) < 2*se else 'OUTSIDE noise'}")

    print("\n" + "=" * 90)
    print("  A directional edge shows up as a LARGE, one-sided gap. Similar")
    print("  numbers in both columns mean the statistic is measuring how far")
    print("  price travels, which is volatility, and is not tradeable as direction.")
    print("=" * 90)


if __name__ == "__main__":
    main()
