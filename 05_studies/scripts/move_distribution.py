"""How far does price actually move over a hold? The right input to the hurdle.

Two errors need correcting, both mine.

  1. The SPX "median intraday range 0.43%" quoted earlier came from 13
     half-hourly SPXW snapshots. Sampling a day at 13 points misses the
     extremes and understates true range by roughly half. Minute bars put SPY's
     median range at 0.90%.

  2. More seriously, RANGE IS THE WRONG QUANTITY. The break-even formula
     p* = 0.5 + cost/(2*delta*move) uses the move captured from entry to exit.
     High-to-low range is only capturable with perfect timing, so feeding range
     into the hurdle credits the trade with a move it cannot realise -- the same
     error as measuring a breakout from before the breakout (trap #6).

The correct input is the distribution of |return| over the actual hold window.
That is what this measures, at each hold length, against the accuracy the hurdle
requires at that move size.
"""
import glob
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T = pd.Timestamp("09:30").time()
CLOSE_T = pd.Timestamp("16:00").time()

# From theta_hurdle.py, in index points on a ~3,736 spot.
SPREAD_PTS, THETA_PER_HALF_HR, SPOT, DELTA = 0.30, 0.37, 3736.0, 0.50
CEILING = 0.529


def bars(sym):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    return df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)]


def main():
    print("=" * 98)
    print("DISTRIBUTION OF |MOVE| BY HOLD LENGTH  -- vs RANGE, and vs the hurdle")
    print("=" * 98)

    for sym in ("SPY", "QQQ"):
        df = bars(sym)
        df = df.assign(day=pd.DatetimeIndex(df.index).date)
        full = df.groupby("day").size()
        df = df[df.day.isin(full[full >= 380].index)]     # drop half days

        print(f"\n  {sym}   {df.day.nunique()} full sessions")
        print(f"    {'hold':>8s} {'med |move|':>11s} {'p75':>7s} {'p90':>7s}"
              f" {'med RANGE':>11s} {'acc needed':>11s} {'reachable?':>11s}")

        for mins, halves in ((30, 1), (60, 2), (120, 4), (240, 8)):
            movs, rngs = [], []
            for d, g in df.groupby("day"):
                c = g["close"].values
                h, lo = g["high"].values, g["low"].values
                if len(c) < mins + 1:
                    continue
                # every non-overlapping window of this length within the session
                for i in range(0, len(c) - mins, mins):
                    movs.append(abs(c[i + mins] / c[i] - 1) * 100)
                    rngs.append((h[i:i + mins + 1].max() /
                                 lo[i:i + mins + 1].min() - 1) * 100)
            mv = np.array(movs)
            rg = np.array(rngs)
            med = np.median(mv)
            # accuracy required at the MEDIAN move for this hold
            cost = SPREAD_PTS + halves * THETA_PER_HALF_HR
            cap = DELTA * SPOT * med / 100
            need = 0.5 + cost / (2 * cap)
            lab = f"{need*100:.1f}%" if need < 1 else ">100%"
            ok = "yes" if need <= CEILING else "no"
            print(f"    {mins:6d}m  {med:10.2f}% {np.percentile(mv,75):6.2f}%"
                  f" {np.percentile(mv,90):6.2f}% {np.median(rg):10.2f}%"
                  f" {lab:>11s} {ok:>11s}")

        # What fraction of windows are big enough at the ceiling?
        print(f"\n    fraction of 30-min windows clearing the move needed at "
              f"{CEILING*100:.1f}% accuracy:")
        for mins, halves in ((30, 1), (60, 2), (120, 4)):
            movs = []
            for d, g in df.groupby("day"):
                c = g["close"].values
                for i in range(0, len(c) - mins, mins):
                    movs.append(abs(c[i + mins] / c[i] - 1) * 100)
            mv = np.array(movs)
            cost = SPREAD_PTS + halves * THETA_PER_HALF_HR
            need_move = cost / (2 * DELTA * (CEILING - 0.5)) / SPOT * 100
            print(f"      {mins:3d}m hold needs {need_move:5.2f}% -> "
                  f"{(mv >= need_move).mean()*100:5.1f}% of windows qualify "
                  f"(median move {np.median(mv):.2f}%)")

    print("\n" + "=" * 98)
    print("  RANGE runs well above |MOVE| at every hold. Any hurdle analysis fed")
    print("  with range is crediting the trade with a move it cannot capture.")
    print("=" * 98)


if __name__ == "__main__":
    main()
