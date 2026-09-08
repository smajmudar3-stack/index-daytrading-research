"""validate_newlo_real.py — the new-low continuation setup, traded as a REAL 0DTE put.

The signal: SPX makes a new session low on an expanding 30-minute bar. Directional accuracy over the
next 60-90 minutes is 54-62% across all three time splits and all four move thresholds — a plateau in
two dimensions on 1,919 sessions spanning 2016-2024.

Directional accuracy is not money, though. Puts carry skew precisely because downside moves are more
common, so the market may already charge for this. That is the question this answers, and it answers
it with ACTUAL SPXW bid/ask — no Black-Scholes anywhere, which matters because the model is exactly
what inflated the condor result.

Trade modelled the way the owner trades: enter at the signal bar, buy a put, exit on a premium target,
a premium stop, or a time stop, whichever comes first, paying the real spread both ways.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

from idt import paths

PATH = "spxw/data_opt.parquet"  # path under DATA_ROOT, resolved at the read site
COLS = ["quote_date", "quote_time", "option_type", "mnes_rel", "mid", "bas",
        "active_underlying_price", "open_interest"]


def load():
    df = pd.read_parquet(paths.require_data(PATH), columns=COLS)
    df["t"] = df.quote_time.astype(str)
    df["tmin"] = pd.to_datetime(df.t).dt.hour * 60 + pd.to_datetime(df.t).dt.minute
    return df


def signals(df):
    """New session low on an expanding bar, from the underlying path."""
    s = df.groupby(["quote_date", "t"]).agg(
        close=("active_underlying_price", "first")).reset_index()
    s["tmin"] = pd.to_datetime(s.t).dt.hour * 60 + pd.to_datetime(s.t).dt.minute
    s = s.sort_values(["quote_date", "tmin"])
    g = s.groupby("quote_date", group_keys=False)
    s["ret"] = g.close.apply(lambda x: x.pct_change())
    s["run_lo"] = g.close.cummin()
    s["at_lo"] = (s.close <= s.run_lo).astype(int)
    s["vol"] = g.ret.apply(lambda x: x.rolling(6, min_periods=3).std())
    s["vol_ratio"] = s.ret.abs() / s.vol.replace(0, np.nan)
    s["sig"] = (s.at_lo == 1) & (s.vol_ratio > 1.2) & (s.ret < 0)
    return s


def pick_put(chain, target_mnes):
    puts = chain[chain.option_type == "P"]
    if puts.empty:
        return None
    i = np.argmin(np.abs(puts.mnes_rel.values - target_mnes))
    r = puts.iloc[i]
    if abs(r.mnes_rel - target_mnes) > 0.004 or r.mid <= 0:
        return None
    return r


def run(otm=0.003, tp=0.60, stop=-0.50, hold_bars=3):
    df = load()
    sig = signals(df)
    sig_set = {(r.quote_date, r.t) for r in sig[sig.sig].itertuples()}
    trades = []
    for date, day in df.groupby("quote_date"):
        rows = sig[(sig.quote_date == date) & sig.sig]
        if rows.empty:
            continue
        r0 = rows.iloc[0]                      # first signal of the session only
        if r0.tmin > 810:                      # need time left to work
            continue
        entry_chain = day[day.t == r0.t]
        if entry_chain.empty:
            continue
        spot0 = entry_chain.active_underlying_price.iloc[0]
        leg = pick_put(entry_chain, 1 - otm)
        if leg is None:
            continue
        entry = leg.mid + leg.bas / 2.0        # pay the offer
        if entry <= 0:
            continue
        # CRITICAL: hold a FIXED STRIKE. mnes_rel is strike/spot, and spot moves every bar, so
        # matching on mnes_rel would silently track a different contract each time — which is what
        # produced an impossible 3.9% win rate on the first attempt.
        strike = leg.mnes_rel * spot0
        times = sorted(day[day.tmin > r0.tmin].t.unique())[:hold_bars]

        def price_at(t):
            ch = day[day.t == t]
            if ch.empty:
                return None
            sp = ch.active_underlying_price.iloc[0]
            puts = ch[ch.option_type == "P"]
            if puts.empty or sp <= 0:
                return None
            want = strike / sp                       # the SAME strike, re-expressed in today's spot
            i = np.argmin(np.abs(puts.mnes_rel.values - want))
            row = puts.iloc[i]
            if abs(row.mnes_rel - want) > 0.0015:    # that strike is off this grid now
                return None
            return row.mid - row.bas / 2.0           # sell the bid

        ret = None
        last_px = None
        for t in times:
            px = price_at(t)
            if px is None:
                continue
            last_px = px
            r = (px - entry) / entry
            if r <= stop:
                ret = stop; break
            if r >= tp:
                ret = tp; break
        if ret is None and last_px is not None:
            ret = (last_px - entry) / entry
        if ret is None:
            continue
        trades.append(dict(date=date, ret=ret, entry=entry, tmin=r0.tmin, spot=spot0))
    return pd.DataFrame(trades)


def report(t, label):
    if t.empty or len(t) < 40:
        print(f"  {label:38} n={len(t)} too few")
        return None
    r = t.ret.values
    tt, pp = st.ttest_1samp(r, 0)
    dates = np.sort(t.date.unique())
    a, b = dates[int(len(dates)*.40)], dates[int(len(dates)*.70)]
    sp = []
    for nm, m in (("TR", t.date < a), ("VA", (t.date>=a)&(t.date<b)), ("TE", t.date>=b)):
        x = t[m]
        sp.append(f"{nm} n{len(x)} {x.ret.mean()*100:+.1f}%" if len(x) >= 15 else f"{nm} --")
    print(f"  {label:38} n={len(r):4d} win {(r>0).mean()*100:4.1f}% avg {r.mean()*100:+6.2f}% "
          f"t={tt:+5.2f} | " + " ".join(sp))
    return t


def main():
    print("NEW-LOW CONTINUATION, TRADED AS A REAL 0DTE PUT (actual SPXW bid/ask)\n")
    print(f"{'config':40}{'result'}")
    best = None
    for otm in (0.001, 0.003, 0.005):
        for tp, stop in ((0.60, -0.50), (1.00, -0.50), (0.40, -0.40)):
            t = run(otm=otm, tp=tp, stop=stop, hold_bars=3)
            got = report(t, f"{otm*100:.1f}% OTM put, TP{tp*100:.0f}/stop{stop*100:.0f}")
            if got is not None and (best is None or got.ret.mean() > best[1].ret.mean()):
                best = ((otm, tp, stop), got)
    if best is None:
        print("\nnothing tradeable")
        return
    (otm, tp, stop), t = best
    print(f"\nBEST: {otm*100:.1f}% OTM, TP {tp*100:.0f}%, stop {stop*100:.0f}%")
    t = t.copy(); t["yr"] = pd.to_datetime(t.date).dt.year
    for y, g in t.groupby("yr"):
        print(f"    {y}  n={len(g):3d}  win {(g.ret>0).mean()*100:4.1f}%  avg {g.ret.mean()*100:+6.2f}%")
    t["mo"] = pd.to_datetime(t.date).dt.to_period("M")
    for rf in (0.10, 0.25):
        mo = t.groupby("mo")["ret"].apply(lambda x: np.prod(1+x*rf)-1).values
        eq = np.cumprod(1+mo); pk = np.maximum.accumulate(eq)
        yrs = len(mo)/12
        print(f"  {rf*100:3.0f}% risk: monthly {mo.mean()*100:+.2f}% | {(mo>0).mean()*100:.0f}% green "
              f"| CAGR {((max(eq[-1],1e-9))**(1/max(yrs,.1))-1)*100:+.1f}% "
              f"| maxDD -{((pk-eq)/pk).max()*100:.0f}% | $2k->${2000*eq[-1]:,.0f}")


if __name__ == "__main__":
    main()
