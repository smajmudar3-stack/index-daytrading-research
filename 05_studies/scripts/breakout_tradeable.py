"""Enter AT the break, not at 10:00. The difference is the whole result.

mirror_drift_control.py measured the move from the 10:00 close to the session
close, conditioned on which side of the opening range broke first. That gave
+23 bp/trade at t=5.33 on QQQ and it is contaminated:

    the break is DEFINED by price reaching the range boundary, so conditioning
    on "broke up" guarantees the leg from 10:00 up to the high already happened.
    Measuring from 10:00 pays you for a move you could not have traded.

The tradeable quantity enters at the break level itself -- that is the first
moment the signal exists -- and exits at the close. Everything before the break
belongs to the market, not to the strategy.

Reported both ways so the size of the contamination is visible, plus the
standard cost hurdle: SPY/QQQ round trip is roughly 1 bp all-in.
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


def build(sym):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    df = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)].copy()
    df["day"] = pd.DatetimeIndex(df.index).date
    df["t"] = pd.DatetimeIndex(df.index).time
    out = []
    for d, g in df.groupby("day"):
        if g["t"].iloc[-1] < pd.Timestamp("15:55").time():
            continue
        orb, rest = g[g.t <= ORB_END], g[g.t > ORB_END]
        if len(orb) < 25 or len(rest) < 100:
            continue
        hi, lo = orb["high"].max(), orb["low"].min()
        if hi <= lo:
            continue
        close = rest["close"].iloc[-1]
        ref10 = orb["close"].iloc[-1]
        up_i = rest.index[rest["high"] > hi]
        dn_i = rest.index[rest["low"] < lo]
        fu = up_i[0] if len(up_i) else None
        fd = dn_i[0] if len(dn_i) else None
        if fu is None and fd is None:
            continue
        if fd is None or (fu is not None and fu < fd):
            brk, entry, when = +1, hi, fu
        else:
            brk, entry, when = -1, lo, fd
        out.append(dict(day=d, brk=brk, entry=entry, ref10=ref10, close=close,
                        t_break=pd.Timestamp(when).time(),
                        rng_pct=(hi - lo) / ref10))
    return pd.DataFrame(out)


def stat(x):
    return x.mean() * 1e4, x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def main():
    print("=" * 94)
    print("OPENING-RANGE BREAKOUT -- entry at 10:00 (contaminated) vs at the break")
    print("=" * 94)

    for sym in ("SPY", "QQQ"):
        r = build(sym)
        # (a) the contaminated version
        from_10 = r.brk * (r.close / r.ref10 - 1)
        # (b) the tradeable version: entry at the break level
        from_brk = r.brk * (r.close / r.entry - 1)

        a_bp, a_t, n = stat(from_10)
        b_bp, b_t, _ = stat(from_brk)
        print(f"\n  {sym}  n = {n}")
        print(f"    entry at 10:00 close  {a_bp:+8.2f} bp   t = {a_t:+5.2f}   "
              f"<-- includes the pre-break leg")
        print(f"    entry AT the break    {b_bp:+8.2f} bp   t = {b_t:+5.2f}   "
              f"<-- tradeable")
        print(f"    contamination         {a_bp-b_bp:+8.2f} bp "
              f"({(a_bp-b_bp)/abs(a_bp)*100 if a_bp else 0:.0f}% of the headline)")
        print(f"    net of ~1bp round trip{b_bp-1:+8.2f} bp   "
              f"hit rate {(from_brk>0).mean()*100:.1f}%")

        # Does it depend on when the break happens? Late breaks leave less day.
        r2 = r.assign(pnl=from_brk)
        early = r2[r2.t_break <= pd.Timestamp("11:00").time()]
        late = r2[r2.t_break > pd.Timestamp("11:00").time()]
        for lab, s in (("break before 11:00", early), ("break after 11:00", late)):
            if len(s) > 30:
                bp, t, k = stat(s.pnl)
                print(f"      {lab:20s} {bp:+8.2f} bp  t = {t:+5.2f}  n = {k}")

        # Wide ranges mean a volatile day; narrow ranges a quiet one.
        med = r2.rng_pct.median()
        for lab, s in (("narrow opening range", r2[r2.rng_pct <= med]),
                       ("wide opening range", r2[r2.rng_pct > med])):
            bp, t, k = stat(s.pnl)
            print(f"      {lab:20s} {bp:+8.2f} bp  t = {t:+5.2f}  n = {k}")

    print("\n" + "=" * 94)
    print("  The gap between the two entry rules is the cost of measuring a")
    print("  breakout from before the breakout happened.")
    print("=" * 94)


if __name__ == "__main__":
    main()
