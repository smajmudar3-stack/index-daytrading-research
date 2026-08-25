"""The payoff of the volatility work: can a forecast pick the tradeable days?

Two things are now established:

  - the 0DTE break-even hurdle is a direct function of move size (0.62% of spot
    for a 30-minute hold at the 52.9% accuracy ceiling)
  - volatility is forecastable at OOS R2 ~40%, unlike direction at ~0

So even though volatility TIMING is not tradeable -- VIX beats HAR outright and
HAR adds nothing to VIX (t = 1.50, insignificant) -- a forecast can still be
useful as a GATE: it may identify which days are large enough to clear the
hurdle at all.

That is a genuinely different question. Timing asks "is implied mispriced."
Gating asks "will today move enough to be worth trading." The second only needs
the forecast to rank days, not to beat the market.

Tested against the honest benchmark: does the forecast beat simply using
yesterday's range, and does it beat using VIX?
"""
import glob
import os

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T = pd.Timestamp("09:30").time()
CLOSE_T = pd.Timestamp("16:00").time()
HURDLE = 0.62          # % of spot needed at a 30-min hold, 52.9% accuracy


def load(sym):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    df = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)]
    px = df["close"].resample("5min").last().dropna()
    r = np.log(px).diff()
    day = pd.DatetimeIndex(r.index).date
    rv = r.groupby(day).apply(lambda s: np.sum(s.values ** 2))
    cnt = r.groupby(day).size()
    rv = rv[(cnt >= 50) & (rv > 0)]

    dd = df.copy()
    dd["day"] = pd.DatetimeIndex(dd.index).date
    rng = dd.groupby("day").apply(
        lambda g: (g["high"].max() / g["low"].min() - 1) * 100)
    return rv, rng.reindex(rv.index).dropna()


def main():
    v = yf.download("^VIX", start="2024-06-01", end="2026-08-20",
                    progress=False, auto_adjust=False)["Close"]
    if isinstance(v, pd.DataFrame):
        v = v.iloc[:, 0]
    v.index = pd.DatetimeIndex(v.index).date

    print("=" * 96)
    print(f"CAN A FORECAST PICK DAYS THAT CLEAR THE {HURDLE}% HURDLE?")
    print("=" * 96)

    for sym in ("SPY", "QQQ"):
        rv, rng = load(sym)
        lrv = np.log(rv)
        d = pd.DataFrame({"rng": rng})
        d["x_d"] = lrv.shift(1)
        d["x_w"] = lrv.shift(1).rolling(5).mean()
        d["x_m"] = lrv.shift(1).rolling(22).mean()
        d["prev_rng"] = rng.shift(1)
        d["vix"] = v.reindex(d.index).shift(1)
        d = d.dropna()

        X = np.column_stack([np.ones(len(d)), d.x_d, d.x_w, d.x_m])
        y = np.log(d.rng.values)
        fc = np.full(len(d), np.nan)
        for i in range(150, len(d)):
            b, *_ = np.linalg.lstsq(X[:i], y[:i], rcond=None)
            fc[i] = X[i] @ b
        d["fc"] = np.exp(fc)
        s = d.dropna()
        big = s.rng >= HURDLE
        base = big.mean()

        print(f"\n  {sym}   n = {len(s)}   median range {s.rng.median():.2f}%")
        print(f"    days clearing {HURDLE}%: {base*100:.1f}% (the base rate)")
        print(f"    {'selector':30s} {'flagged':>9s} {'precision':>11s} "
              f"{'lift':>7s} {'captured':>10s}")

        for nm, key in (("HAR range forecast", "fc"),
                        ("yesterday's range", "prev_rng"),
                        ("VIX level", "vix")):
            # Flag the same NUMBER of days for every selector, so precision is
            # directly comparable rather than a function of threshold choice.
            k = int(base * len(s))
            top = s.nlargest(k, key)
            prec = (top.rng >= HURDLE).mean()
            capt = (top.rng >= HURDLE).sum() / max(big.sum(), 1)
            print(f"    {nm:30s} {k:9d} {prec*100:10.1f}% "
                  f"{prec/base:6.2f}x {capt*100:9.1f}%")

        # How much of the tradeable mass is reachable at all?
        print(f"    top-decile days by HAR forecast: median range "
              f"{s.nlargest(len(s)//10, 'fc').rng.median():.2f}%  "
              f"vs bottom decile {s.nsmallest(len(s)//10, 'fc').rng.median():.2f}%")

    print("\n" + "=" * 96)
    print("  Lift above 1.0 means the selector concentrates tradeable days.")
    print("  A forecast that merely matches VIX adds nothing you cannot read")
    print("  off the screen for free.")
    print("=" * 96)


if __name__ == "__main__":
    main()
