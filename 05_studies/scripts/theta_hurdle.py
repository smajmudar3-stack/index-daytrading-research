"""The spread is not the binding cost on 0DTE direction -- theta is.

accuracy_hurdle.py found a break-even of 51.6% from bid-ask alone, which sits
BELOW the ~52.9% ceiling the literature supports. That would make directional
0DTE marginally viable, and it is wrong, because it ignores time decay. On a
same-day option held for hours, extrinsic value bleeds continuously whether or
not the direction call is right.

This measures the decay empirically instead of assuming a model. The SPXW panel
carries `tv` (time value) for ATM options at half-hourly snapshots, so the
average loss of extrinsic per half hour is directly observable.

The corrected hurdle is then

    p* = 0.5 + (spread + theta_cost) / (2 * delta * move)

where theta_cost is what the position bleeds over the intended hold, and it
enters the same way the spread does: paid whether right or wrong.
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPXW = os.path.join(ROOT, "data", "spxw", "data_opt.parquet")


def main():
    df = pd.read_parquet(SPXW, columns=["quote_date", "quote_time", "option_type",
                                        "mnes_rel", "mid", "bas", "tv",
                                        "active_underlying_price"])
    atm = df[(df.mnes_rel.between(0.995, 1.005)) & (df.mid > 0)].copy()
    atm["spot"] = atm.active_underlying_price
    atm["tv_pts"] = atm.tv * atm.spot
    atm["prem_pts"] = atm.mid * atm.spot
    atm["sp_pts"] = atm.bas * atm.spot

    print("=" * 94)
    print("MEASURED TIME-VALUE DECAY -- ATM SPXW, by time of day")
    print("=" * 94)
    prof = atm.groupby("quote_time").agg(
        n=("tv_pts", "size"), tv=("tv_pts", "median"), prem=("prem_pts", "median"),
        sp=("sp_pts", "median"))
    prof = prof[prof.n > 500]
    print(f"  {'time':>9s} {'n':>8s} {'time value':>12s} {'premium':>10s} "
          f"{'spread':>8s} {'decay vs prev':>14s}")
    prev = None
    decays = []
    for t, r in prof.iterrows():
        d = "" if prev is None else f"{r.tv - prev:+.2f} pts"
        if prev is not None and str(t) > "10:00:00":
            decays.append(prev - r.tv)
        print(f"  {str(t):>9s} {r.n:8,.0f} {r.tv:11.2f}p {r.prem:9.2f}p "
              f"{r.sp:7.2f}p {d:>14s}")
        prev = r.tv

    med_decay = float(np.median(decays)) if decays else float("nan")
    med_sp = atm.sp_pts.median()
    spot = atm.spot.median()
    print(f"\n  median extrinsic lost per half hour: {med_decay:.2f} index points")
    print(f"  median round-trip spread            : {med_sp:.2f} index points")
    print(f"  -> theta over a 2-hour hold is {4*med_decay/med_sp:.0f}x the spread")

    print("\n" + "=" * 94)
    print("CORRECTED BREAK-EVEN:  p* = 0.5 + (spread + theta) / (2 * delta * move)")
    print("=" * 94)
    delta = 0.50
    print(f"  {'move':>9s} {'%spot':>7s}  " +
          "".join(f"{h:>13s}" for h in ("30min hold", "1h hold", "2h hold", "4h hold")))
    for mv_pct in (0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00):
        mv = spot * mv_pct / 100
        cap = delta * mv
        cells = []
        for halves in (1, 2, 4, 8):
            cost = med_sp + halves * med_decay
            p = 0.5 + cost / (2 * cap)
            cells.append(f"{p*100:.1f}%" if p < 1 else "impossible")
        print(f"  {mv:8.1f}p {mv_pct:6.2f}%  " + "".join(f"{c:>13s}" for c in cells))

    ceiling = 0.529
    print(f"\n  Literature ceiling on real production data: {ceiling*100:.1f}%")
    print("  Cells above that number are unreachable, whatever the signal.")

    print("\n" + "=" * 94)
    print("WHAT MOVE SIZE IS NEEDED TO MAKE 52.9% ACCURACY PAY?")
    print("=" * 94)
    for halves, lab in ((1, "30 min"), (2, "1 hour"), (4, "2 hours"), (8, "4 hours")):
        cost = med_sp + halves * med_decay
        # p* = 0.5 + cost/(2*delta*move)  ->  move = cost / (2*delta*(p-0.5))
        need_mv = cost / (2 * delta * (ceiling - 0.5))
        print(f"  {lab:>8s} hold: need a move of {need_mv:6.1f} pts "
              f"({need_mv/spot*100:5.2f}% of spot) before a {ceiling*100:.1f}% "
              f"call breaks even")

    # How often does SPX actually move that much intraday?
    px = (df.groupby(["quote_date", "quote_time"])["active_underlying_price"]
            .median().unstack())
    rng = (px.max(axis=1) / px.min(axis=1) - 1).dropna() * 100
    print(f"\n  observed SPX intraday range (10:00-16:00), {len(rng):,} days:")
    for q in (0.25, 0.50, 0.75, 0.90, 0.95):
        print(f"    p{int(q*100):02d}  {rng.quantile(q):5.2f}%")
    print(f"    share of days with range >= 1.00%: {(rng >= 1.0).mean()*100:.1f}%")
    print(f"    share of days with range >= 1.50%: {(rng >= 1.5).mean()*100:.1f}%")


if __name__ == "__main__":
    main()
