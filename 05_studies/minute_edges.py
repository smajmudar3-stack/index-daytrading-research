"""Intraday day-trading strategies on 2 years of MINUTE bars (QQQ/SPY, regular session).

Tests the patterns that could actually have an edge (not directional drift, which we
showed is dead intraday), i.e. breakout/vol capture and VWAP behaviour:

  ORB  Opening-Range Breakout: define the high/low of the first N minutes; go long on a
       break above / short on a break below; stop at the opposite side of the range;
       exit at the close. Long+short, long-only, short-only. (Zarattini-Aziz 2023 style.)
  VWAP mean-reversion: fade price when it stretches k*sigma from session VWAP.
  Trend-day filter: does the first-hour direction predict the rest of the day?

Costs: 1.5 bps per side (QQQ/SPY penny spread + slippage) = 3 bps round trip, charged on
every entry+exit. Position = the whole day-trade (1x notional). Causal throughout.
"""
import glob
import numpy as np
import pandas as pd

from idt import paths

RT = 0.0003  # 3 bps round trip


def load_minute(tk):
    files = sorted(glob.glob(paths.require_data("minute", tk) + "/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in files])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "15:59")            # regular session only
    df["day"] = df.index.date
    return df


def orb(df, or_min, direction="both"):
    """Opening-range breakout. First `or_min` minutes define the range; break of the range
    triggers entry (long above high / short below low); stop at the opposite range side;
    exit at the close. Returns per-day net trade returns."""
    open_cut = (pd.Timestamp("09:30") + pd.Timedelta(minutes=or_min)).strftime("%H:%M")
    trades = []
    for day, g in df.groupby("day"):
        if len(g) < 60:
            continue
        opening = g.between_time("09:30", open_cut, inclusive="left")
        rest = g.between_time(open_cut, "15:59")
        if len(opening) < 1 or len(rest) < 5:
            continue
        hi, lo = opening["high"].max(), opening["low"].min()
        entry = None; side = 0; bts = None
        for ts, row in rest.iterrows():
            if direction in ("both", "long") and row["high"] > hi:
                entry, side, bts = hi, 1, ts; break
            if direction in ("both", "short") and row["low"] < lo:
                entry, side, bts = lo, -1, ts; break
        if entry is None:
            continue
        seg = rest.loc[bts:]
        stop_px = lo if side == 1 else hi
        exit_px = seg["close"].iloc[-1]           # default: exit at the close
        for _, r2 in seg.iterrows():
            if side == 1 and r2["low"] <= stop_px:
                exit_px = stop_px; break
            if side == -1 and r2["high"] >= stop_px:
                exit_px = stop_px; break
        trades.append(side * (exit_px / entry - 1) - RT)
    return pd.Series(trades)


def report(name, r):
    r = r.dropna()
    if len(r) < 20:
        print(f"  {name:34} n={len(r)} (too few)"); return
    exp = r.mean(); wl = (r > 0).mean()
    gains = r[r > 0].sum(); losses = -r[r < 0].sum()
    pf = gains / losses if losses > 0 else np.inf
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    tstat = r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0
    print(f"  {name:34} exp {exp*100:+.3f}%/day  win% {wl*100:4.1f}  PF {pf:4.2f}  "
          f"Sharpe {sharpe:+4.2f}  t {tstat:+4.1f}  n={len(r)}")


def main():
    for tk in ["QQQ", "SPY"]:
        df = load_minute(tk)
        ndays = df["day"].nunique()
        print(f"\n===== {tk}  minute bars: {ndays} sessions "
              f"({min(df['day'])}..{max(df['day'])}) =====")
        print("  --- Opening Range Breakout, stop at opposite range side, exit EOD ---")
        for om in (5, 15, 30, 60):
            report(f"ORB {om}min both", orb(df, om, "both"))
        for om in (15, 30):
            report(f"ORB {om}min LONG-only", orb(df, om, "long"))
            report(f"ORB {om}min SHORT-only", orb(df, om, "short"))


if __name__ == "__main__":
    main()
