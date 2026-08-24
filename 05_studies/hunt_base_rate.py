"""hunt_base_rate.py — STEP 1 of the direction hunt: how often does the target move even occur?

Target: SPX >= 25 pts (~0.32%) or NDX >= 80 pts (~0.27%) inside 10-15 minutes.
Before hunting for a 60%-accurate predictor we must know the BASE RATE, because that is what any
signal has to beat. If a +0.3% 15-minute move happens 8% of the time, a signal that fires and is right
60% of the time is an enormous edge. If it happens 45% of the time, 60% is a modest one.

This also establishes the correct benchmark for "accuracy": a coin flip on DIRECTION given a move
happened is 50%, but the joint event (move happens AND we called the side) has a much lower base rate.
Being precise about which one we are targeting prevents fooling ourselves later.
"""
import glob
import numpy as np
import pandas as pd

SPY_MULT = 10.0        # SPY ~ SPX/10
QQQ_MULT = 41.0        # QQQ ~ NDX/41
SPX_TICKS, NDX_TICKS = 25.0, 80.0


def load(sym):
    fs = sorted(glob.glob(f"data/minute/{sym}/*.parquet"))
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f) for f in fs])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df["date"] = df.index.normalize().tz_localize(None)
    df["mins"] = df.index.hour * 60 + df.index.minute
    return df[(df.mins >= 570) & (df.mins < 960)].copy()


def forward_extremes(df, horizon):
    """For each bar: the max up and max down move over the NEXT `horizon` minutes, within the session."""
    out_up, out_dn = [], []
    for date, g in df.groupby("date"):
        c = g.close.values
        hi = g.high.values
        lo = g.low.values
        n = len(c)
        up = np.full(n, np.nan)
        dn = np.full(n, np.nan)
        for i in range(n):
            j = min(i + horizon, n - 1)
            if j <= i:
                continue
            up[i] = hi[i + 1:j + 1].max() - c[i]
            dn[i] = lo[i + 1:j + 1].min() - c[i]
        out_up.append(pd.Series(up, index=g.index))
        out_dn.append(pd.Series(dn, index=g.index))
    return pd.concat(out_up), pd.concat(out_dn)


def report(sym, mult, ticks):
    df = load(sym)
    if df is None:
        print(f"{sym}: no data")
        return
    thr = ticks / mult                      # threshold in ETF points
    print(f"\n{'='*74}")
    print(f"{sym}  target = {ticks:.0f} index pts = {thr:.2f} {sym} pts "
          f"(~{thr/df.close.mean()*100:.2f}% move)")
    print(f"{'='*74}")
    print(f"sessions {df.date.nunique()} | bars {len(df):,}")
    print(f"\n{'horizon':>9}{'P(up hit)':>11}{'P(dn hit)':>11}{'P(either)':>11}{'P(both)':>10}"
          f"{'clean up':>10}{'clean dn':>10}")
    for h in (10, 15, 30, 60, 120):
        up, dn = forward_extremes(df, h)
        m = up.notna()
        u = (up[m] >= thr)
        d = (dn[m] <= -thr)
        either = (u | d).mean() * 100
        both = (u & d).mean() * 100
        # "clean" = hit one side without the other being hit (a tradeable directional move)
        cu = (u & ~d).mean() * 100
        cd = (d & ~u).mean() * 100
        print(f"{h:>8}m{u.mean()*100:>10.1f}%{d.mean()*100:>10.1f}%{either:>10.1f}%"
              f"{both:>9.1f}%{cu:>9.1f}%{cd:>9.1f}%")
    # what a perfect direction-caller would earn vs the base rate
    up, dn = forward_extremes(df, 15)
    m = up.notna()
    u = (up[m] >= thr); d = (dn[m] <= -thr)
    clean = (u & ~d) | (d & ~u)
    print(f"\n  at 15m: a CLEAN one-sided {ticks:.0f}-pt move occurs on {clean.mean()*100:.1f}% of bars.")
    print(f"  Given a clean move happened, it was UP {((u & ~d).sum()/max(clean.sum(),1))*100:.1f}% of the time")
    print(f"  -> guessing 'up' every time on those bars scores that %. THAT is the number to beat,")
    print(f"     not 50%. And a signal must ALSO pick the {clean.mean()*100:.1f}% of bars that move at all.")


if __name__ == "__main__":
    report("SPY", SPY_MULT, SPX_TICKS)
    report("QQQ", QQQ_MULT, NDX_TICKS)
