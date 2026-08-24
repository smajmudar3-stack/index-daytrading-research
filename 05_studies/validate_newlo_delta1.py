"""validate_newlo_delta1.py — express the new-low edge WITHOUT paying premium.

Established: new session low on an expanding 30-min bar predicts continuation down over the next
60-90 minutes at 54-62% accuracy, stable across three time splits and four move thresholds on 1,919
sessions. Also established: buying puts on it LOSES (-6.6%/trade on real quotes) because put skew
prices the asymmetry and theta takes the rest.

A directional edge of 54-62% is worth real money — but only through an instrument that does not charge
premium for it. Tested here:

  1. SHORT DELTA-1        (ES futures / SPY shares) — pure direction, no theta, no skew
  2. PUT DEBIT SPREAD     — buy the ATM put, sell one further out; the short leg refunds much of the skew
  3. CALL CREDIT SPREAD   — get PAID to be right, theta works for you instead of against

Delta-1 is measured on the underlying path directly. The spreads are priced on real SPXW bid/ask.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

import validate_newlo_real as V

COST_BP = 1.0        # round-trip friction on delta-1, in basis points of notional


def delta1(hold_bars=3, stop_pct=None, tp_pct=None):
    """Short the index at the signal; exit on target, stop, or time."""
    df = V.load()
    sig = V.signals(df)
    px = sig.set_index(["quote_date", "t"]).close
    out = []
    for date, day in sig.groupby("quote_date"):
        rows = day[day.sig]
        if rows.empty:
            continue
        r0 = rows.iloc[0]
        if r0.tmin > 810:
            continue
        after = day[day.tmin > r0.tmin].head(hold_bars)
        if after.empty:
            continue
        entry = r0.close
        ret = None
        for _, r in after.iterrows():
            move = (entry - r.close) / entry          # SHORT: profit when price falls
            if stop_pct is not None and move <= -stop_pct:
                ret = -stop_pct; break
            if tp_pct is not None and move >= tp_pct:
                ret = tp_pct; break
        if ret is None:
            ret = (entry - after.iloc[-1].close) / entry
        out.append(dict(date=date, ret=ret - COST_BP / 10000.0, tmin=r0.tmin))
    return pd.DataFrame(out)


def spread(kind="put_debit", long_otm=0.001, short_otm=0.006, hold_bars=3, tp=0.60, stop=-0.50):
    """Real-quote vertical. put_debit = buy near-ATM put / sell further OTM put.
       call_credit = sell near-ATM call / buy further OTM call."""
    df = V.load()
    sig = V.signals(df)
    out = []
    for date, day in df.groupby("quote_date"):
        rows = sig[(sig.quote_date == date) & sig.sig]
        if rows.empty:
            continue
        r0 = rows.iloc[0]
        if r0.tmin > 810:
            continue
        ch = day[day.t == r0.t]
        if ch.empty:
            continue
        spot0 = ch.active_underlying_price.iloc[0]
        typ = "P" if kind == "put_debit" else "C"
        side = ch[ch.option_type == typ]
        if side.empty:
            continue

        def pick(target):
            i = np.argmin(np.abs(side.mnes_rel.values - target))
            r = side.iloc[i]
            return r if abs(r.mnes_rel - target) <= 0.0025 and r.mid > 0 else None

        if kind == "put_debit":
            a = pick(1 - long_otm); b = pick(1 - short_otm)
        else:
            a = pick(1 + long_otm); b = pick(1 + short_otm)
        if a is None or b is None:
            continue
        ka, kb = a.mnes_rel * spot0, b.mnes_rel * spot0
        if kind == "put_debit":
            entry = (a.mid + a.bas / 2) - (b.mid - b.bas / 2)     # net debit paid
            risk = entry
        else:
            entry = (a.mid - a.bas / 2) - (b.mid + b.bas / 2)     # net credit received
            width = abs(kb - ka)
            risk = width - entry
        if entry <= 0 or risk <= 0:
            continue

        def val(t):
            c = day[day.t == t]
            if c.empty:
                return None
            sp = c.active_underlying_price.iloc[0]
            s2 = c[c.option_type == typ]
            if s2.empty or sp <= 0:
                return None
            def leg(k):
                w = k / sp
                i = np.argmin(np.abs(s2.mnes_rel.values - w))
                r = s2.iloc[i]
                return r if abs(r.mnes_rel - w) <= 0.0015 else None
            la, lb = leg(ka), leg(kb)
            if la is None or lb is None:
                return None
            if kind == "put_debit":
                return (la.mid - la.bas / 2) - (lb.mid + lb.bas / 2)
            return (la.mid + la.bas / 2) - (lb.mid - lb.bas / 2)   # cost to close the credit

        times = sorted(day[day.tmin > r0.tmin].t.unique())[:hold_bars]
        ret, last = None, None
        for t in times:
            v = val(t)
            if v is None:
                continue
            last = v
            r = ((v - entry) / risk) if kind == "put_debit" else ((entry - v) / risk)
            if r <= stop:
                ret = stop; break
            if r >= tp:
                ret = tp; break
        if ret is None and last is not None:
            ret = ((last - entry) / risk) if kind == "put_debit" else ((entry - last) / risk)
        if ret is None:
            continue
        out.append(dict(date=date, ret=ret))
    return pd.DataFrame(out)


def rep(t, label, rf=0.10):
    if t.empty or len(t) < 40:
        print(f"  {label:40} n={len(t)} too few")
        return
    r = t.ret.values
    tt, pp = st.ttest_1samp(r, 0)
    d = np.sort(t.date.unique())
    a, b = d[int(len(d)*.40)], d[int(len(d)*.70)]
    seg = []
    for nm, m in (("TR", t.date < a), ("VA", (t.date>=a)&(t.date<b)), ("TE", t.date>=b)):
        x = t[m]
        seg.append(f"{nm} {x.ret.mean()*100:+.2f}%" if len(x) >= 15 else f"{nm} --")
    t2 = t.copy(); t2["mo"] = pd.to_datetime(t2.date).dt.to_period("M")
    mo = t2.groupby("mo")["ret"].apply(lambda x: np.prod(1+x*rf)-1).values
    eq = np.cumprod(1+mo); pk = np.maximum.accumulate(eq)
    print(f"  {label:40} n={len(r):4d} win {(r>0).mean()*100:4.1f}% avg {r.mean()*100:+6.2f}% "
          f"t={tt:+5.2f} | {' '.join(seg)} | mo {mo.mean()*100:+.2f}% DD -{((pk-eq)/pk).max()*100:.0f}%")


def main():
    print("THE SAME SIGNAL, EXPRESSED WITHOUT BUYING PREMIUM\n")
    print("1) SHORT DELTA-1 (no theta, no skew) — return is on NOTIONAL, so leverage applies")
    for hb, lab in ((2, "60m"), (3, "90m"), (4, "120m")):
        rep(delta1(hold_bars=hb), f"short index, hold {lab}, no stop")
    for stop in (0.002, 0.003):
        rep(delta1(hold_bars=3, stop_pct=stop, tp_pct=0.004),
            f"short index 90m, stop {stop*100:.1f}% / tp 0.4%")
    print("\n2) PUT DEBIT SPREAD (real quotes) — returns on capital at risk")
    for so in (0.004, 0.006):
        rep(spread("put_debit", 0.001, so), f"put debit 0.1%/{so*100:.1f}% OTM")
    print("\n3) CALL CREDIT SPREAD (real quotes) — paid to be right")
    for lo in (0.001, 0.003):
        rep(spread("call_credit", lo, lo + 0.005), f"call credit {lo*100:.1f}%/{(lo+0.005)*100:.1f}% OTM")


if __name__ == "__main__":
    main()
