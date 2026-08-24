"""ORB evaluated the way it is actually traded: RISK-NORMALISED (R-multiples).

Each day risk 1 unit; entry on the range break, stop at the opposite range side, so the
stop distance = range width. Position size = 1/width -> every trade risks the same. Payoff
is measured in R (multiples of risk). This is where ORB's asymmetric edge (small stops,
occasional big trend-day winners) shows up if it exists.

Variants:
  - exit: EOD, or a profit target of T*R (then trail/hold), stop always -1R
  - trend filter: only take breakouts aligned with the daily trend
      (long only if open > prior close; short only if open < prior close)  [gap/trend align]
  - long-only (bull-market realistic for QQQ)
Costs: 3 bps round trip converted to R using the stop distance.
"""
import glob
import numpy as np
import pandas as pd

RT = 0.0003


def load_minute(tk):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"data/minute/{tk}/*.parquet"))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "15:59")
    df["day"] = df.index.date
    return df


def prior_close(df):
    daily = df.groupby("day")["close"].last()
    return daily.shift(1)


def orb_R(df, or_min=15, direction="both", target_R=None, trend_filter=False):
    open_cut = (pd.Timestamp("09:30") + pd.Timedelta(minutes=or_min)).strftime("%H:%M")
    pc = prior_close(df)
    Rs = []
    for day, g in df.groupby("day"):
        if len(g) < 60:
            continue
        opening = g.between_time("09:30", open_cut, inclusive="left")
        rest = g.between_time(open_cut, "15:59")
        if len(opening) < 1 or len(rest) < 5:
            continue
        hi, lo = opening["high"].max(), opening["low"].min()
        width = hi - lo
        if width <= 0:
            continue
        day_open = opening["open"].iloc[0]
        pcl = pc.get(day, np.nan)
        allow_long = direction in ("both", "long") and (not trend_filter or (not np.isnan(pcl) and day_open >= pcl))
        allow_short = direction in ("both", "short") and (not trend_filter or (not np.isnan(pcl) and day_open < pcl))
        entry = None; side = 0; bts = None
        for ts, row in rest.iterrows():
            if allow_long and row["high"] > hi:
                entry, side, bts = hi, 1, ts; break
            if allow_short and row["low"] < lo:
                entry, side, bts = lo, -1, ts; break
        if entry is None:
            continue
        stop_px = lo if side == 1 else hi
        risk = abs(entry - stop_px)              # = width
        target_px = entry + side * target_R * risk if target_R else None
        seg = rest.loc[bts:]
        exit_px = seg["close"].iloc[-1]
        for _, r2 in seg.iterrows():
            if side == 1:
                if r2["low"] <= stop_px:
                    exit_px = stop_px; break
                if target_px and r2["high"] >= target_px:
                    exit_px = target_px; break
            else:
                if r2["high"] >= stop_px:
                    exit_px = stop_px; break
                if target_px and r2["low"] <= target_px:
                    exit_px = target_px; break
        R = side * (exit_px - entry) / risk - (RT * entry / risk)
        Rs.append(R)
    return pd.Series(Rs)


def report(name, R):
    R = R.dropna()
    if len(R) < 20:
        print(f"  {name:40} n={len(R)} too few"); return
    exp = R.mean(); wl = (R > 0).mean()
    gains = R[R > 0].sum(); losses = -R[R < 0].sum()
    pf = gains / losses if losses > 0 else np.inf
    t = R.mean() / (R.std() / np.sqrt(len(R))) if R.std() > 0 else 0
    ann = R.mean() * len(R) / 2  # ~2yrs of data -> per-year R
    print(f"  {name:40} exp {exp:+.3f}R  win% {wl*100:4.1f}  PF {pf:4.2f}  t {t:+4.1f}  "
          f"~{ann:+.0f}R/yr  n={len(R)}")


for tk in ["QQQ", "SPY"]:
    df = load_minute(tk)
    print(f"\n===== {tk}  ({df['day'].nunique()} sessions) — ORB in R-multiples =====")
    print("  --- baseline (EOD exit, stop opposite side) ---")
    report("ORB15 both", orb_R(df, 15, "both"))
    report("ORB30 both", orb_R(df, 30, "both"))
    print("  --- with TREND filter (align with gap direction) ---")
    report("ORB15 both + trend", orb_R(df, 15, "both", trend_filter=True))
    report("ORB30 both + trend", orb_R(df, 30, "both", trend_filter=True))
    print("  --- with profit TARGET (10R) + trend ---")
    report("ORB15 both +trend +10R", orb_R(df, 15, "both", target_R=10, trend_filter=True))
    report("ORB30 both +trend +5R", orb_R(df, 30, "both", target_R=5, trend_filter=True))
    print("  --- long-only + trend (bull-market realistic) ---")
    report("ORB15 long +trend", orb_R(df, 15, "long", trend_filter=True))
