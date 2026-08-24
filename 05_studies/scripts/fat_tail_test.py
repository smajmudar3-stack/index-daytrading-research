"""Are black swans more common than the model says? Yes. Does that make options cheap? No.

The thesis: real distributions have fatter tails than the Gaussian, so big moves
happen far more often than a normal model implies, so cheap far-OTM options are
underpriced.

The first half of that is TRUE and this measures exactly how true. The second
half does not follow, and this measures why: the market does not price options
off a Gaussian. The volatility SMILE is precisely the market's own fat-tail
adjustment, and the question that decides the trade is not

    "are tails fatter than a bell curve?"        (yes, enormously)

but

    "are tails fatter than the SMILE already charges for?"

Two comparisons, on the same 1.16M stock-days:
  1. Realised tail frequency vs a Gaussian random walk.
  2. Realised tail frequency vs what the OPTION MARKET implies, backed out of
     real far-OTM contract prices — the delta of an option IS approximately the
     market's risk-neutral probability of finishing beyond that strike.
"""
import os
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm

from idt import paths

warnings.filterwarnings("ignore")
BM = paths.data("bigmove", "panel.parquet")
OPT = paths.data("opt_eod", "SPY_options.parquet")


def main():
    d = pd.read_parquet(paths.require_data(BM))
    print("=" * 92)
    print("1. ARE TAILS FATTER THAN GAUSSIAN?  (1.16M stock-days, 158 names)")
    print("=" * 92)
    print("  Gaussian benchmark uses the reflection principle: for a driftless")
    print("  random walk, P(MAX |move| over the window > k sigma) ~= 2 x P(|Z| > k).\n")
    print(f"  {'horizon':9s} {'k':>3s} {'ACTUAL':>9s} {'GAUSSIAN':>10s} "
          f"{'ratio':>8s}   verdict")
    for H in sorted(d.H.unique()):
        s = d[d.H == H]
        for k in (2, 3, 4, 5):
            act = (s.move_sig >= k).mean()
            gauss = 2 * (1 - norm.cdf(k))          # reflection approximation
            if act == 0:
                continue
            ratio = act / gauss
            verdict = ("FAR fatter" if ratio > 10 else
                       "much fatter" if ratio > 3 else
                       "fatter" if ratio > 1.2 else "in line")
            print(f"  {H:>3d} days  {k:>3d} {act*100:8.3f}% {gauss*100:9.4f}% "
                  f"{ratio:8.1f}x   {verdict}")
        print()

    print("=" * 92)
    print("2. BUT WHAT DOES THE OPTION MARKET ALREADY CHARGE FOR THOSE TAILS?")
    print("=" * 92)
    print("  An option's DELTA is approximately the risk-neutral probability of")
    print("  finishing beyond its strike. So comparing delta to the realised")
    print("  frequency of finishing beyond that strike tests whether the market's")
    print("  tail pricing is too thin -- which is the actual trade.\n")

    rows = []
    und = pd.read_parquet(paths.data("opt_eod", "SPY_underlying.parquet"))
    dcol = [c for c in und.columns if "date" in c.lower()]
    ucol = [c for c in und.columns if c.lower() in ("close", "adjclose")][0]
    und.index = pd.to_datetime(und[dcol[0]]) if dcol else und.index
    px = und[ucol].sort_index()

    for y in range(2012, 2026):
        t = pq.read_table(paths.require_data(OPT), columns=["date", "expiration", "strike", "type",
                                                            "bid", "ask", "delta", "open_interest"],
                                              filters=[("date", ">=", pd.Timestamp(f"{y}-01-01")),
                                                       ("date", "<=", pd.Timestamp(f"{y}-12-31"))]).to_pandas()
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t["date"]); t["expiration"] = pd.to_datetime(t["expiration"])
        t["dte"] = (t["expiration"] - t["date"]).dt.days
        e = t[(t.dte.between(25, 45)) & (t.bid > 0.01) & (t.open_interest > 10)
              & (t.delta.abs().between(0.005, 0.20))]
        if e.empty:
            continue
        e = e.assign(ym=e.date.dt.to_period("M"))
        e = e.groupby(["ym", "expiration", "strike", "type"]).first().reset_index()
        for _, r in e.iterrows():
            hit = px[px.index >= r.expiration]
            if hit.empty:
                continue
            S = float(hit.iloc[0])
            itm = (S > r.strike) if r.type == "call" else (S < r.strike)
            rows.append({"delta": abs(float(r.delta)), "itm": bool(itm),
                         "type": r.type})
    o = pd.DataFrame(rows)

    print(f"  {'delta band':16s} {'kind':5s} {'n':>7s} {'IMPLIED':>9s} "
          f"{'REALISED':>10s} {'ratio':>8s}   who wins")
    for lo, hi in [(0.005, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 0.20)]:
        for kind in ("call", "put"):
            s = o[(o.delta >= lo) & (o.delta < hi) & (o.type == kind)]
            if len(s) < 300:
                continue
            implied = s.delta.mean()          # market's own probability
            realised = s.itm.mean()           # how often it actually happened
            ratio = realised / implied if implied > 0 else np.nan
            who = ("BUYER edge" if ratio > 1.15 else
                   "SELLER edge" if ratio < 0.85 else "fairly priced")
            print(f"  {lo:.3f}-{hi:.2f}      {kind:5s} {len(s):7,d} "
                  f"{implied*100:8.2f}% {realised*100:9.2f}% {ratio:8.2f}x   {who}")

    print("\n" + "=" * 92)
    print("  The tails ARE far fatter than a bell curve — that part of the thesis is")
    print("  correct and the numbers above are dramatic. But the option market is not")
    print("  quoting a bell curve: the volatility smile IS its fat-tail adjustment,")
    print("  and section 2 shows whether that adjustment is too small or too large.")


if __name__ == "__main__":
    main()
