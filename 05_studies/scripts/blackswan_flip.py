"""Two questions the last test raised but did not answer.

Q1. THE OPPOSITE SIDE. If buying 2-5 delta puts returns -46.6%, then SELLING
    them should return roughly +46.6% minus the spread — you become the house.
    That is the direct implication of the previous result and it deserves a
    real test, including the part that makes it dangerous: the worst single
    outcome, and what one of those does to an account.

Q2. THE 5000x. "$200 -> $1M" needs a 5,000x. The previous run found single
    winners of +16,350% (164x) and +33,358% (334x), so enormous payoffs are
    REAL and in the data. The honest question is not whether they exist but
    what the probability is of catching one, given N tickets — and whether the
    capital survives long enough to be holding a ticket when it happens.

Both computed from the same 10.5M real-quote purchases, bought at the ask,
settled at intrinsic, worthless = -100%.
"""
import warnings

import numpy as np
import pandas as pd

from idt import paths

warnings.filterwarnings("ignore")
TR = paths.data("blackswan_trades.parquet")

BUCKETS = [(0.001, 0.02, "ultra <2d"), (0.02, 0.05, "2-5d"),
           (0.05, 0.10, "5-10d"), (0.10, 0.16, "10-16d"), (0.16, 0.30, "16-30d")]

# Measured round-trip spread as a fraction of premium, by delta bucket (SPY).
SPREAD = {"ultra <2d": 0.222, "2-5d": 0.087, "5-10d": 0.043,
          "10-16d": 0.028, "16-30d": 0.018}


def main():
    d = pd.read_parquet(paths.require_data(TR))
    print("=" * 100)
    print("Q1. THE OPPOSITE SIDE — SELLING the far-OTM options instead of buying")
    print("=" * 100)
    print("  Seller's return per unit of PREMIUM collected. Entry at the bid (you")
    print("  receive less than mid), so the buyer's spread cost becomes yours too.")
    print()
    print(f"  {'bucket':11s} {'kind':5s} {'n':>7s} {'win%':>6s} {'MEAN':>9s} "
          f"{'WORST':>10s} {'p1':>9s} {'ruin?':>22s}")
    for kind in ("call", "put"):
        for lo, hi, lab in BUCKETS:
            s = d[(d.delta >= lo) & (d.delta < hi) & (d.type == kind)]
            if len(s) < 200:
                continue
            # Seller's P&L is the buyer's, negated, minus the round-trip spread.
            sell = -s.ret - SPREAD[lab]
            worst = sell.min()
            # A naked short's loss is unbounded in premium terms. Express the
            # worst case as: how many winning trades does one loss erase?
            erase = abs(worst) / sell[sell > 0].mean() if (sell > 0).any() else np.nan
            print(f"  {lab:11s} {kind:5s} {len(s):7,d} {(sell>0).mean()*100:5.1f}% "
                  f"{sell.mean()*100:+8.1f}% {worst*100:+9.0f}% "
                  f"{sell.quantile(0.01)*100:+8.0f}% "
                  f"{erase:>10.0f} wins erased")

    print("\n  NOTE: these are per-unit-of-PREMIUM. Selling a $0.16 option collects")
    print("  $16 and can lose thousands — the % looks fine and the dollars do not.")
    print("  Margin, not premium, is the real denominator. See the dollar view below.")

    # ---- what it looks like in dollars, which is what actually matters ----
    print("\n" + "-" * 100)
    print("  THE DOLLAR VIEW — selling 2-5 delta puts, $200 account, 1 contract at a time")
    print("-" * 100)
    s = d[(d.delta >= 0.02) & (d.delta < 0.05) & (d.type == "put")]
    prem = 16.0                      # $0.16 x 100, the median 2-5 delta premium
    sell = (-s.ret - SPREAD["2-5d"]) * prem
    print(f"  median trade  {sell.median():+8.2f}$   mean {sell.mean():+7.2f}$")
    print(f"  worst trade   {sell.min():+8.2f}$   (on a ${prem:.0f} credit)")
    print(f"  trades worse than -$200 (account gone): "
          f"{(sell < -200).sum()} of {len(sell)} = {(sell < -200).mean()*100:.2f}%")
    print(f"  expected trades until one of those: ~{1/max((sell<-200).mean(),1e-9):.0f}")

    # ------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("Q2. THE 5,000x — what are the actual odds of $200 -> $1M?")
    print("=" * 100)
    for lo, hi, lab in BUCKETS[:3]:
        s = d[(d.delta >= lo) & (d.delta < hi)]
        if len(s) < 500:
            continue
        r = s.ret.values
        for mult in (10, 50, 100, 500, 5000):
            p = (r > mult - 1).mean()
            if p > 0:
                print(f"  {lab:11s} P(single contract >= {mult:5d}x) = {p*100:7.4f}%"
                      f"   ~1 in {1/p:,.0f}")
        print()

    print("-" * 100)
    print("  $200 spread across N tickets — probability at least one hits 5,000x")
    print("-" * 100)
    for lo, hi, lab in BUCKETS[:3]:
        s = d[(d.delta >= lo) & (d.delta < hi)]
        if len(s) < 500:
            continue
        p = (s.ret.values > 4999).mean()
        for n in (20, 200, 2000):
            hit = 1 - (1 - p) ** n
            print(f"  {lab:11s} {n:5d} tickets: P(any 5000x) = {hit*100:8.5f}%   "
                  f"cost to place them ~${n * (0.06 if lab=='ultra <2d' else 0.16 if lab=='2-5d' else 0.43) * 100:,.0f}")
        print()

    print("=" * 100)
    print("  The single best outcome in 10.5M real purchases was +33,358% = 334x.")
    print(f"  Contracts returning >= 5000x in the entire dataset: "
          f"{(d.ret > 4999).sum()}")
    print("  A 5,000x did not occur once in 10.5 million real option purchases.")


if __name__ == "__main__":
    main()
