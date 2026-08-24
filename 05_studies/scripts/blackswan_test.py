"""Black-swan lottery test: does buying very cheap far-OTM options pay?

The strategy under test is deliberately positive-skew: buy many very cheap,
very far OTM contracts; accept that most go to zero; rely on rare large winners.
The owner has explicitly accepted the negative median, so the ONLY question that
matters is whether the MEAN is positive net of real costs.

Two design decisions make this a fair test rather than a flattering one:

  1. WORTHLESS OPTIONS COUNT AS -100%. They are not dropped. Filtering the exit
     chain by `bid > 0` deletes exactly the losers and manufactures a positive
     result -- it is the single most dangerous bug in this domain and it has
     already fooled this repo once.

  2. FILLS ARE AT THE REAL QUOTE. Bought at the ask, sold at the bid. That
     matters more here than anywhere else, because the round-trip spread on a
     sub-2-delta SPY option is 22% of premium -- and SPY is the most liquid
     options market in existence.

Held to expiry, so terminal value is intrinsic and no exit-liquidity assumption
is needed. Every bucket reports mean, median, win rate, the biggest winner, and
how much of the total P&L came from the single best trade.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT = os.path.join(ROOT, "data", "opt_eod", "SPY_options.parquet")

BUCKETS = [(0.001, 0.02, "ultra <2d"), (0.02, 0.05, "2-5 delta"),
           (0.05, 0.10, "5-10 delta"), (0.10, 0.16, "10-16 delta"),
           (0.16, 0.30, "16-30 delta")]
DTE_LO, DTE_HI = 20, 60


def load_year(y):
    t = pq.read_table(OPT, columns=["date", "expiration", "strike", "type",
                                    "bid", "ask", "delta", "open_interest"],
                      filters=[("date", ">=", pd.Timestamp(f"{y}-01-01")),
                               ("date", "<=", pd.Timestamp(f"{y}-12-31"))]).to_pandas()
    if t.empty:
        return t
    t["date"] = pd.to_datetime(t["date"])
    t["expiration"] = pd.to_datetime(t["expiration"])
    t["dte"] = (t["expiration"] - t["date"]).dt.days
    return t


def main():
    print("=" * 96)
    print("BLACK-SWAN TEST — buy cheap far-OTM SPY options, hold to expiry")
    print("  bought at ASK, settled at intrinsic. Worthless = -100%, never dropped.")
    print("=" * 96)

    und = pd.read_parquet(os.path.join(ROOT, "data", "opt_eod",
                                       "SPY_underlying.parquet"))
    ucol = [c for c in und.columns if c.lower() in ("close", "adjclose")][0]
    dcol = [c for c in und.columns if "date" in c.lower()]
    und = und.set_index(pd.to_datetime(und[dcol[0]]) if dcol else und.index)
    px = und[ucol].sort_index()

    rows = []
    for y in range(2010, 2026):
        t = load_year(y)
        if t.empty:
            continue
        # Entry universe: liquid, real two-sided quote, in the DTE window.
        e = t[(t.dte.between(DTE_LO, DTE_HI)) & (t.bid > 0.02) & (t.ask > t.bid)
              & (t.open_interest > 10) & (t.delta.abs() > 0.001)]
        if e.empty:
            continue
        # One entry per (expiration, strike, type) per month to limit overlap.
        e = e.assign(ym=e.date.dt.to_period("M"))
        e = e.sort_values("date").groupby(["ym", "expiration", "strike", "type"]).first().reset_index()

        for _, r in e.iterrows():
            # Terminal underlying price at expiry.
            hit = px[px.index >= r.expiration]
            if hit.empty:
                continue
            S = float(hit.iloc[0])
            intrinsic = max(S - r.strike, 0.0) if r.type == "call" else max(r.strike - S, 0.0)
            cost = float(r.ask)                     # we pay the offer
            if cost <= 0:
                continue
            rows.append({"delta": abs(float(r.delta)), "type": r.type,
                         "ret": (intrinsic - cost) / cost, "cost": cost,
                         "date": r.date})
        print(f"    {y}: {len(rows):,} cumulative trades", flush=True)

    d = pd.DataFrame(rows)
    d.to_parquet(os.path.join(ROOT, "data", "blackswan_trades.parquet"), index=False)

    print(f"\n  {len(d):,} option purchases tested\n")
    print(f"  {'bucket':12s} {'kind':5s} {'n':>7s} {'win%':>6s} {'MEAN':>9s} "
          f"{'median':>8s} {'best':>9s} {'top-1 share':>12s}")
    for kind in ("call", "put"):
        for lo, hi, lab in BUCKETS:
            s = d[(d.delta >= lo) & (d.delta < hi) & (d.type == kind)]
            if len(s) < 200:
                continue
            r = s.ret
            # How much of the total P&L came from the single best trade? If one
            # trade IS the result, the mean is not an expectation you can plan on.
            tot = r.sum()
            top1 = r.max() / tot if tot > 0 else np.nan
            print(f"  {lab:12s} {kind:5s} {len(s):7,d} {(r>0).mean()*100:5.1f}% "
                  f"{r.mean()*100:+8.1f}% {r.median()*100:+7.0f}% {r.max()*100:+8.0f}% "
                  f"{top1*100 if top1==top1 else float('nan'):11.0f}%")

    print("\n" + "=" * 96)
    print("THE SAME THING, AS A PORTFOLIO — $100 spread over N contracts, repeated")
    print("=" * 96)
    for lo, hi, lab in BUCKETS:
        s = d[(d.delta >= lo) & (d.delta < hi) & (d.type == "call")]
        if len(s) < 500:
            continue
        rng = np.random.default_rng(0)
        finals = []
        for _ in range(2000):
            pick = rng.choice(s.ret.values, size=20, replace=True)   # 20 tickets
            finals.append((1 + pick).mean())        # equal-weight basket outcome
        f = np.array(finals)
        print(f"  {lab:12s} basket of 20: median {np.median(f):5.2f}x  "
              f"mean {f.mean():5.2f}x  P(basket > 1.0) = {(f > 1).mean()*100:4.1f}%  "
              f"P(> 2x) = {(f > 2).mean()*100:4.1f}%")


if __name__ == "__main__":
    main()
