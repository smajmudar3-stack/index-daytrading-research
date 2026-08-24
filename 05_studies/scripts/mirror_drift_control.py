"""Is QQQ's breakout asymmetry a signal, or is it just drift?

The mirror test gave QQQ up-breaks a 60.2% follow-through against 49.8% for
down-breaks -- a +10.4pp gap, outside two standard errors. Taken alone that
looks like a directional edge.

Two things argue it is drift instead:

  1. Up-breaks follow through MORE (+10.4pp) but extend LESS (-9.1pp). A
     momentum mechanism moves both together. Drift on a rising asset does
     exactly this: price closes above without needing to travel.

  2. QQQ rose steeply over 2024-2026. On any asset with positive drift, "close
     above a level" is more likely than "close below" regardless of what
     happened at 10:00.

The control is the unconditional base rate: how often would the close finish
beyond the same level with NO breakout condition at all. The tradeable quantity
is the excess over that, not the raw rate.

Also reported: the same test on returns measured RELATIVE TO THE DAY'S DRIFT,
which removes the beta component entirely.
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
    rows = []
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
            brk = 0
        elif fd is None or (fu is not None and fu < fd):
            brk = +1
        else:
            brk = -1
        rows.append(dict(day=d, hi=hi, lo=lo, close=close, ref10=ref10, brk=brk,
                         ret=close / ref10 - 1))
    return pd.DataFrame(rows)


def main():
    print("=" * 96)
    print("DRIFT CONTROL -- is the breakout asymmetry an edge or just beta?")
    print("=" * 96)

    for sym in ("SPY", "QQQ"):
        r = build(sym)
        n = len(r)
        # Unconditional base rates for the SAME events, ignoring the breakout.
        base_above = (r.close > r.hi).mean()
        base_below = (r.close < r.lo).mean()
        drift = r.ret.mean()

        up = r[r.brk > 0]
        dn = r[r.brk < 0]
        cond_up = (up.close > up.hi).mean()
        cond_dn = (dn.close < dn.lo).mean()

        print(f"\n  {sym}  {n} sessions   mean 10:00->close return {drift*1e4:+.2f} bp")
        print(f"    {'':30s} {'conditional':>13s} {'base rate':>12s} {'EXCESS':>10s}")
        print(f"    {'up-break closes above hi':30s} {cond_up*100:12.1f}% "
              f"{base_above*100:11.1f}% {(cond_up-base_above)*100:+9.1f}pp")
        print(f"    {'down-break closes below lo':30s} {cond_dn*100:12.1f}% "
              f"{base_below*100:11.1f}% {(cond_dn-base_below)*100:+9.1f}pp")

        # Demeaned: strip the day-type drift out of the return itself.
        r2 = r.copy()
        r2["excess"] = r2.ret - drift
        eu = r2[r2.brk > 0]["excess"]
        ed = r2[r2.brk < 0]["excess"]
        pooled = pd.concat([eu, -ed])
        t = pooled.mean() / (pooled.std(ddof=1) / np.sqrt(len(pooled)))
        print(f"    drift-removed follow-through: {pooled.mean()*1e4:+.2f} bp/trade"
              f"   t = {t:+.2f}   n = {len(pooled)}")

        # Raw sign-following P&L, which is what you would actually trade.
        pnl = np.sign(r.brk) * r.ret
        pnl = pnl[r.brk != 0]
        tt = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(len(pnl)))
        print(f"    raw sign-following        : {pnl.mean()*1e4:+.2f} bp/trade"
              f"   t = {tt:+.2f}")

    print("\n" + "=" * 96)
    print("  If the EXCESS columns are near zero while the conditional rates look")
    print("  strong, the breakout is inheriting the asset's drift and there is no")
    print("  pattern edge to trade.")
    print("=" * 96)


if __name__ == "__main__":
    main()
