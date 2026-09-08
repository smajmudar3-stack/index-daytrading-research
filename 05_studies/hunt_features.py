"""hunt_features.py — build the full intraday feature matrix and test EVERY feature for directional
predictive power.

Target (the owner's spec): a clean one-sided move of >=25 SPX pts / >=80 NDX pts inside a horizon of
10 min to 2 hours. Label = +1 if the up-threshold is hit without the down-threshold, -1 if the
reverse, 0 if neither or both.

Discipline, because this is a wide search on a small sample and that is exactly how people fool
themselves:
  - Every feature is built from information available AT OR BEFORE the bar. No forward fills, no
    same-bar future data. The label uses bars strictly AFTER the entry bar.
  - Time-ordered TRAIN/TEST split, never random CV — random CV on overlapping intraday windows leaks
    massively and is the single most common way these results turn out fake.
  - Overlapping labels are acknowledged: consecutive bars share future windows, so effective sample
    size is far below the bar count and naive t-stats are inflated. Reported accordingly.
  - Every result is shown against the base rate, not against 50%.
"""
import glob
import numpy as np
import pandas as pd

import backtest_0dte_rules as B

from idt import paths

SPY_MULT, QQQ_MULT = 10.0, 41.0
SPX_TICKS, NDX_TICKS = 25.0, 80.0


def load(sym):
    fs = sorted(glob.glob(paths.require_data("minute", sym) + "/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in fs])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df["date"] = df.index.normalize().tz_localize(None)
    df["mins"] = df.index.hour * 60 + df.index.minute
    return df[(df.mins >= 570) & (df.mins < 960)].copy()


def add_features(df):
    """All features use ONLY current-and-past information."""
    g = df.groupby("date", group_keys=False)
    out = df.copy()

    # --- momentum over multiple lookbacks -------------------------------------------------
    for w in (1, 3, 5, 15, 30, 60):
        out[f"ret{w}"] = g.close.apply(lambda s: s.pct_change(w))
    # acceleration: is momentum itself increasing
    out["accel"] = out.ret5 - out.ret15
    # consecutive directional bars
    sign = np.sign(out.close.diff())
    out["streak"] = g.close.apply(
        lambda s: np.sign(s.diff()).groupby((np.sign(s.diff()) != np.sign(s.diff()).shift()).cumsum()).cumcount() + 1
    ) * sign

    # --- VWAP ---------------------------------------------------------------------------
    out["vwap_dist"] = (out.close - out.vwap) / out.close
    out["vwap_slope"] = g.vwap.apply(lambda s: s.diff(5) / s)

    # --- volume -------------------------------------------------------------------------
    out["vol_ma"] = g.volume.apply(lambda s: s.rolling(30, min_periods=5).mean())
    out["rvol"] = out.volume / out.vol_ma
    out["rvol5"] = g.volume.apply(lambda s: s.rolling(5, min_periods=2).sum()) / (out.vol_ma * 5)
    out["dollar_vol"] = out.volume * out.close
    # volume trend: is participation building
    out["vol_trend"] = g.volume.apply(lambda s: s.rolling(10, min_periods=3).mean() /
                                      s.rolling(60, min_periods=10).mean())

    # --- volatility / range --------------------------------------------------------------
    out["tr"] = (out.high - out.low) / out.close
    g2 = out.groupby("date", group_keys=False)
    out["atr"] = g2.tr.apply(lambda s: s.rolling(15, min_periods=3).mean())
    out["rv30"] = g2.ret1.apply(lambda s: s.rolling(30, min_periods=5).std())
    g3 = out.groupby("date", group_keys=False)
    out["rv_ratio"] = out.rv30 / g3.rv30.apply(lambda s: s.rolling(120, min_periods=20).mean())
    # bar shape: body vs wick — decisive bars have big bodies
    rng = (out.high - out.low).replace(0, np.nan)
    out["body"] = (out.close - out.open) / rng
    out["upper_wick"] = (out.high - out[["open", "close"]].max(axis=1)) / rng
    out["lower_wick"] = (out[["open", "close"]].min(axis=1) - out.low) / rng

    # --- session structure ----------------------------------------------------------------
    out["tod"] = out.mins
    day_open = g.open.transform("first")
    out["since_open"] = (out.close - day_open) / day_open
    out["day_hi"] = g.high.cummax()
    out["day_lo"] = g.low.cummin()
    rngd = (out.day_hi - out.day_lo).replace(0, np.nan)
    out["range_pos"] = (out.close - out.day_lo) / rngd          # 0 = at lows, 1 = at highs
    out["range_pct"] = rngd / day_open
    # opening range (9:30-10:00)
    ormask = out.mins < 600
    or_hi = out[ormask].groupby("date").high.max()
    or_lo = out[ormask].groupby("date").low.min()
    out["or_hi"] = out.date.map(or_hi)
    out["or_lo"] = out.date.map(or_lo)
    out["or_pos"] = (out.close - out.or_lo) / (out.or_hi - out.or_lo).replace(0, np.nan)
    out["or_width"] = (out.or_hi - out.or_lo) / day_open

    # --- mean reversion / extension --------------------------------------------------------
    out["ma20"] = g.close.apply(lambda s: s.rolling(20, min_periods=5).mean())
    out["ext20"] = (out.close - out.ma20) / out.close
    out["ma60"] = g.close.apply(lambda s: s.rolling(60, min_periods=10).mean())
    out["ext60"] = (out.close - out.ma60) / out.close
    # RSI-ish
    g4 = out.groupby("date", group_keys=False)
    up_ = g4.ret1.apply(lambda s: s.clip(lower=0).rolling(14, min_periods=5).mean())
    dn_ = g4.ret1.apply(lambda s: (-s).clip(lower=0).rolling(14, min_periods=5).mean())
    out["rsi"] = 100 - 100 / (1 + up_ / dn_.replace(0, np.nan))
    return out


def add_daily(df):
    """Daily conditioning: dealer gamma z, DIX z, confluence, causal vol forecast."""
    d = B.build_panel()
    d = B.add_signals(d)
    d["date"] = pd.to_datetime(d.date)
    keep = d.set_index("date")[["gz", "dz", "conf", "sig_hat", "vix"]] if "vix" in d.columns \
        else d.set_index("date")[["gz", "dz", "conf", "sig_hat"]]
    for c in keep.columns:
        df[c] = df.date.map(keep[c])
    # prior-day gap
    return df


def label(df, mult, ticks, horizon):
    thr = ticks / mult
    lab = []
    for date, g in df.groupby("date"):
        c = g.close.values
        hi, lo = g.high.values, g.low.values
        n = len(c)
        y = np.zeros(n)
        for i in range(n):
            j = min(i + horizon, n - 1)
            if j <= i:
                y[i] = np.nan
                continue
            up = hi[i + 1:j + 1].max() - c[i]
            dn = lo[i + 1:j + 1].min() - c[i]
            hit_u, hit_d = up >= thr, dn <= -thr
            y[i] = 1 if (hit_u and not hit_d) else (-1 if (hit_d and not hit_u) else 0)
        lab.append(pd.Series(y, index=g.index))
    return pd.concat(lab)


FEATURES = ["ret1", "ret3", "ret5", "ret15", "ret30", "ret60", "accel", "streak",
            "vwap_dist", "vwap_slope", "rvol", "rvol5", "vol_trend",
            "tr", "atr", "rv30", "rv_ratio", "body", "upper_wick", "lower_wick",
            "tod", "since_open", "range_pos", "range_pct", "or_pos", "or_width",
            "ext20", "ext60", "rsi", "gz", "dz", "conf", "sig_hat"]


def univariate(df, ycol, feats, split_date):
    """For each feature: split into deciles on TRAIN, then measure directional accuracy on TEST
    in the extreme deciles. Accuracy is P(up | moved) among bars where a clean move occurred."""
    tr = df[df.date < split_date]
    te = df[df.date >= split_date]
    moved_te = te[te[ycol] != 0]
    base = (moved_te[ycol] == 1).mean() * 100
    print(f"\nTEST base rate: of {len(moved_te):,} bars with a clean move, {base:.1f}% were UP")
    print(f"{'feature':14}{'trainQ1 up%':>12}{'trainQ10 up%':>13}{'testQ1 up%':>12}"
          f"{'testQ10 up%':>13}{'spread':>9}{'n test':>9}")
    print("-" * 82)
    rows = []
    for f in feats:
        if f not in df.columns:
            continue
        s_tr = tr[f].replace([np.inf, -np.inf], np.nan)
        if s_tr.notna().sum() < 500:
            continue
        try:
            edges = np.nanpercentile(s_tr, [10, 90])
        except Exception:
            continue
        if not np.isfinite(edges).all() or edges[0] == edges[1]:
            continue
        def acc(frame, lo_side):
            m = (frame[f] <= edges[0]) if lo_side else (frame[f] >= edges[1])
            sub = frame[m & (frame[ycol] != 0)]
            return ((sub[ycol] == 1).mean() * 100, len(sub)) if len(sub) >= 30 else (np.nan, len(sub))
        a1, _ = acc(tr, True); a10, _ = acc(tr, False)
        b1, n1 = acc(te, True); b10, n10 = acc(te, False)
        if not np.isfinite([a1, a10, b1, b10]).all():
            continue
        spread = b10 - b1
        rows.append((f, a1, a10, b1, b10, spread, min(n1, n10)))
    rows.sort(key=lambda r: -abs(r[5]))
    for f, a1, a10, b1, b10, sp, n in rows:
        print(f"{f:14}{a1:>11.1f}%{a10:>12.1f}%{b1:>11.1f}%{b10:>12.1f}%{sp:>+8.1f}{n:>9}")
    return rows


def main():
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    horizon = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    mult, ticks = (QQQ_MULT, NDX_TICKS) if sym == "QQQ" else (SPY_MULT, SPX_TICKS)
    print(f"FEATURE HUNT — {sym}, target {ticks:.0f} index pts within {horizon} min")
    df = load(sym)
    df = add_features(df)
    df = add_daily(df)
    df["y"] = label(df, mult, ticks, horizon)
    df = df[df.y.notna()]
    dates = sorted(df.date.unique())
    split = dates[len(dates) // 2]
    print(f"bars {len(df):,} | sessions {len(dates)} | split at {split.date()}")
    univariate(df, "y", FEATURES, split)


if __name__ == "__main__":
    main()
