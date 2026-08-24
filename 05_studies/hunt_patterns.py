"""hunt_patterns.py — discrete PRICE-ACTION setups, not indicator deciles.

Everything tested so far treated features as continuous variables cut into deciles. That is a very
different search space from the way a discretionary trader actually sees a chart: rare, discrete
events with a specific shape. A pattern that fires 60 times a year and wins 65% is invisible to decile
analysis but is exactly what a person trades.

Library built here (each detected on a resampled bar series, direction-aware):

  SINGLE BAR    doji, hammer, shooting star, marubozu, long-wick rejection
  TWO BAR       engulfing, harami, piercing / dark cloud, tweezer, inside bar, outside bar
  THREE BAR     morning / evening star, three soldiers / crows, three-bar reversal
  STRUCTURE     failed breakout (break a level then close back inside), double top / bottom,
                exhaustion (new extreme, weak close), range compression then expansion,
                VWAP rejection, round-number rejection, opening-drive continuation vs reversal
  VOLUME        climax reversal, volume dry-up then expansion, price/volume divergence

Each pattern yields a direction. Forward outcome is measured as the clean one-sided move the owner
targets. Three-way time split; a pattern must hold its sign on all three to be reported.
"""
import glob
import numpy as np
import pandas as pd

TICKS = {"SPY": 2.5, "QQQ": 1.95, "IWM": 0.6}      # ~25 SPX / 80 NDX equivalents


def load(sym, freq="5min"):
    fs = sorted(glob.glob(f"data/minute/{sym}/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in fs])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df["mins"] = df.index.hour * 60 + df.index.minute
    df = df[(df.mins >= 570) & (df.mins < 960)]
    o = df.resample(freq).agg({"open": "first", "high": "max", "low": "min", "close": "last",
                               "volume": "sum", "vwap": "mean"}).dropna()
    o["date"] = o.index.normalize().tz_localize(None)
    o["mins"] = o.index.hour * 60 + o.index.minute
    return o[(o.mins >= 570) & (o.mins < 960)].copy()


def prep(d):
    g = d.groupby("date", group_keys=False)
    d["rng"] = (d.high - d.low).replace(0, np.nan)
    d["body"] = (d.close - d.open)
    d["body_abs"] = d.body.abs()
    d["body_frac"] = d.body_abs / d.rng
    d["uw"] = (d.high - d[["open", "close"]].max(axis=1)) / d.rng
    d["lw"] = (d[["open", "close"]].min(axis=1) - d.low) / d.rng
    d["bull"] = (d.close > d.open).astype(int)
    d["atr"] = g.rng.apply(lambda s: s.rolling(12, min_periods=4).mean())
    d["vol_ma"] = g.volume.apply(lambda s: s.rolling(12, min_periods=4).mean())
    d["rvol"] = d.volume / d.vol_ma
    d["day_hi"] = g.high.cummax()
    d["day_lo"] = g.low.cummin()
    d["vwap_dist"] = (d.close - d.vwap) / d.close
    for c in ("open", "high", "low", "close", "bull", "body_abs", "rng", "uw", "lw", "volume", "body_frac"):
        d[f"p_{c}"] = g[c].shift(1)
        d[f"p2_{c}"] = g[c].shift(2)
    return d


def patterns(d):
    """Return {name: (mask, direction_series)}. direction +1 = expect up, -1 = expect down."""
    P = {}
    big = d.rng > d.atr                       # only meaningful bars
    up1 = pd.Series(1, index=d.index)
    dn1 = pd.Series(-1, index=d.index)

    # ---- single bar -------------------------------------------------------------------
    P["hammer"] = ((d.lw > 0.55) & (d.body_frac < 0.35) & big, up1)
    P["shooting_star"] = ((d.uw > 0.55) & (d.body_frac < 0.35) & big, dn1)
    P["doji"] = ((d.body_frac < 0.12) & big, up1 * 0)          # neutral -> tested both ways below
    P["marubozu_up"] = ((d.body_frac > 0.85) & (d.bull == 1) & big, up1)
    P["marubozu_dn"] = ((d.body_frac > 0.85) & (d.bull == 0) & big, dn1)

    # ---- two bar ----------------------------------------------------------------------
    P["bull_engulf"] = ((d.bull == 1) & (d.p_bull == 0) & (d.close > d.p_open) & (d.open < d.p_close) & big, up1)
    P["bear_engulf"] = ((d.bull == 0) & (d.p_bull == 1) & (d.close < d.p_open) & (d.open > d.p_close) & big, dn1)
    P["bull_harami"] = ((d.p_bull == 0) & (d.bull == 1) & (d.high < d.p_high) & (d.low > d.p_low), up1)
    P["bear_harami"] = ((d.p_bull == 1) & (d.bull == 0) & (d.high < d.p_high) & (d.low > d.p_low), dn1)
    P["piercing"] = ((d.p_bull == 0) & (d.bull == 1) & (d.close > (d.p_open + d.p_close) / 2) & (d.open < d.p_low), up1)
    P["dark_cloud"] = ((d.p_bull == 1) & (d.bull == 0) & (d.close < (d.p_open + d.p_close) / 2) & (d.open > d.p_high), dn1)
    P["inside_bar"] = ((d.high < d.p_high) & (d.low > d.p_low), up1 * 0)
    P["outside_bar_up"] = ((d.high > d.p_high) & (d.low < d.p_low) & (d.bull == 1), up1)
    P["outside_bar_dn"] = ((d.high > d.p_high) & (d.low < d.p_low) & (d.bull == 0), dn1)
    P["tweezer_bot"] = ((d.low - d.p_low).abs() < 0.1 * d.atr) & (d.p_bull == 0) & (d.bull == 1), up1
    P["tweezer_top"] = ((d.high - d.p_high).abs() < 0.1 * d.atr) & (d.p_bull == 1) & (d.bull == 0), dn1

    # ---- three bar --------------------------------------------------------------------
    P["morning_star"] = ((d.p2_bull == 0) & (d.p_body_frac < 0.3) & (d.bull == 1) &
                         (d.close > (d.p2_open + d.p2_close) / 2), up1)
    P["evening_star"] = ((d.p2_bull == 1) & (d.p_body_frac < 0.3) & (d.bull == 0) &
                         (d.close < (d.p2_open + d.p2_close) / 2), dn1)
    P["three_soldiers"] = ((d.bull == 1) & (d.p_bull == 1) & (d.p2_bull == 1) &
                           (d.close > d.p_close) & (d.p_close > d.p2_close), up1)
    P["three_crows"] = ((d.bull == 0) & (d.p_bull == 0) & (d.p2_bull == 0) &
                        (d.close < d.p_close) & (d.p_close < d.p2_close), dn1)

    # ---- structure --------------------------------------------------------------------
    # failed breakout: took out the running high but closed back below it
    P["failed_bo_up"] = ((d.high >= d.day_hi) & (d.close < d.p_high) & (d.bull == 0) & big, dn1)
    P["failed_bo_dn"] = ((d.low <= d.day_lo) & (d.close > d.p_low) & (d.bull == 1) & big, up1)
    # exhaustion: new session extreme on a weak close
    P["exhaust_hi"] = ((d.high >= d.day_hi) & (d.body_frac < 0.3) & (d.uw > 0.45), dn1)
    P["exhaust_lo"] = ((d.low <= d.day_lo) & (d.body_frac < 0.3) & (d.lw > 0.45), up1)
    # vwap rejection: traded through vwap intrabar but closed back on the original side
    P["vwap_rej_up"] = ((d.high > d.vwap) & (d.close < d.vwap) & (d.p_close < d.vwap), dn1)
    P["vwap_rej_dn"] = ((d.low < d.vwap) & (d.close > d.vwap) & (d.p_close > d.vwap), up1)
    # round-number rejection (whole dollar on the ETF)
    near_round = (d.close.round() - d.close).abs() < 0.15
    P["round_rej_hi"] = (near_round & (d.uw > 0.5) & big, dn1)
    P["round_rej_lo"] = (near_round & (d.lw > 0.5) & big, up1)
    # compression then expansion
    comp = d.rng < 0.6 * d.atr
    P["squeeze_break_up"] = (comp.shift(1).fillna(False) & (d.rng > 1.3 * d.atr) & (d.bull == 1), up1)
    P["squeeze_break_dn"] = (comp.shift(1).fillna(False) & (d.rng > 1.3 * d.atr) & (d.bull == 0), dn1)

    # ---- volume -----------------------------------------------------------------------
    P["climax_rev_hi"] = ((d.rvol > 2.0) & (d.high >= d.day_hi) & (d.bull == 0), dn1)
    P["climax_rev_lo"] = ((d.rvol > 2.0) & (d.low <= d.day_lo) & (d.bull == 1), up1)
    P["dryup_break_up"] = ((d.rvol.shift(1) < 0.7) & (d.rvol > 1.5) & (d.bull == 1), up1)
    P["dryup_break_dn"] = ((d.rvol.shift(1) < 0.7) & (d.rvol > 1.5) & (d.bull == 0), dn1)
    return P


def outcomes(d, thr, horizon_bars):
    """Clean one-sided move within the next `horizon_bars`, per session."""
    up, dn = [], []
    for date, g in d.groupby("date"):
        c, hi, lo = g.close.values, g.high.values, g.low.values
        n = len(c)
        u = np.full(n, np.nan); v = np.full(n, np.nan)
        for i in range(n):
            j = min(i + horizon_bars, n - 1)
            if j <= i:
                continue
            u[i] = hi[i+1:j+1].max() - c[i]
            v[i] = lo[i+1:j+1].min() - c[i]
        up.append(pd.Series(u, index=g.index)); dn.append(pd.Series(v, index=g.index))
    U, D = pd.concat(up), pd.concat(dn)
    hit_u = (U >= thr) & ~(D <= -thr)
    hit_d = (D <= -thr) & ~(U >= thr)
    y = pd.Series(0, index=d.index)
    y[hit_u] = 1
    y[hit_d] = -1
    return y


def main():
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    freq = sys.argv[2] if len(sys.argv) > 2 else "5min"
    hb = int(sys.argv[3]) if len(sys.argv) > 3 else 4          # horizon in bars
    thr = TICKS[sym]
    d = prep(load(sym, freq))
    d["y"] = outcomes(d, thr, hb)
    P = patterns(d)
    dates = np.sort(d.date.unique())
    a, b = dates[int(len(dates)*.40)], dates[int(len(dates)*.70)]
    parts = {"TR": d.date < a, "VA": (d.date >= a) & (d.date < b), "TE": d.date >= b}
    moved = d.y != 0
    print(f"{sym} {freq} bars | horizon {hb} bars | target {thr} pts | sessions {d.date.nunique()}")
    for nm, m in parts.items():
        s = d[m & moved]
        print(f"  {nm}: {len(s):,} moved bars, {(s.y==1).mean()*100:.1f}% up")
    print(f"\n{'pattern':18}{'dir':>4}{'TRn':>6}{'TRedge':>8}{'VAn':>6}{'VAedge':>8}{'TEn':>6}{'TEedge':>8}{'':>4}")
    print("-" * 68)
    hits = []
    for nm, (mask, dirs) in P.items():
        if isinstance(mask, tuple):
            mask, dirs = mask
        mask = mask.fillna(False)
        for side in ((1, -1) if (np.asarray(dirs) == 0).all() else [None]):
            dd = pd.Series(side, index=d.index) if side is not None else dirs
            label = f"{nm}{'+' if side==1 else ('-' if side==-1 else '')}"
            row, ok = [], True
            for _, m in parts.items():
                sel = d[mask & m & moved]
                if len(sel) < 25:
                    ok = False; row += [len(sel), np.nan]; continue
                acc = (sel.y.values == dd[sel.index].values).mean() * 100
                # EDGE OVER BASE RATE: a bearish pattern scoring 60% means nothing if 58% of all
                # clean moves in that window were down. Only the excess is information.
                allm = d[m & moved]
                base = (allm.y.values == dd[allm.index].values).mean() * 100
                row += [len(sel), acc - base]
            if not ok:
                continue
            stable = min(row[1], row[3], row[5]) >= 4.0
            print(f"{label:18}{int(dd.iloc[0]):>4}{row[0]:>6}{row[1]:>+7.1f}{row[2]:>6}{row[3]:>+7.1f}"
                  f"{row[4]:>6}{row[5]:>+7.1f}{'  <<' if stable else ''}")
            if stable:
                hits.append((label, row))
    print(f"\npatterns with >=+4pp edge over base on ALL THREE splits: {[h[0] for h in hits] or 'none'}")


if __name__ == "__main__":
    main()
