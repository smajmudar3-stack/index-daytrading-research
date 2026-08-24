"""Direction comes from flow. GAMMA picks how to EXPRESS it.

The pure range trade failed: long premium in low gamma returned +11.63% against
+17.99% unconditional, and short premium in high gamma stayed negative. Buying
or selling volatility on a range forecast alone does not work.

But one cell survived the non-overlap test:

    long call 0.50d | LOW gamma : 50.8% win, +20.61% mean, +1.3% MEDIAN, t=+2.25

That is a DIRECTIONAL structure, and it points at the right synthesis. Gamma
predicts RANGE, and range determines which expression of a directional view pays
best -- it does not supply the view:

    LOW gamma  -> dealers amplify -> wide range -> a naked call has room to run,
                                                   so pay for the convexity
    HIGH gamma -> dealers pin     -> tight range -> the upside is capped anyway,
                                                   so cut cost with a spread

So this measures directional structures ACROSS gamma regimes, to find which
expression belongs in which regime. Direction still has to come from somewhere
else (flow, dark pool, short interest); this only answers "given a view, what do
I buy?"
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADES = os.path.join(ROOT, "data", "swing", "structure_trades.parquet")
GEX = os.path.join(ROOT, "data", "squeeze_dix_gex.csv")

DIRECTIONAL = ["long call 0.80d", "long call 0.70d", "long call 0.50d",
               "long call 0.30d", "call debit 70/30", "call debit 50/30",
               "ZEBRA call 70/50", "ZEBRA call 80/50"]


def gamma_z():
    g = pd.read_csv(GEX)
    dc = [c for c in g.columns if c.lower().startswith("date")][0]
    g[dc] = pd.to_datetime(g[dc]); g = g.set_index(dc).sort_index()
    col = [c for c in g.columns if c.lower() == "gex"][0]
    s = pd.to_numeric(g[col], errors="coerce")
    return ((s - s.rolling(252, min_periods=126).mean())
            / s.rolling(252, min_periods=126).std()).shift(1)


def nonoverlap(df, days):
    df = df.sort_values("date")
    keep, last = [], None
    for _, r in df.iterrows():
        if last is None or (r["date"] - last).days >= days:
            keep.append(r); last = r["date"]
    return pd.DataFrame(keep)


def stat(r):
    r = pd.Series(r).dropna()
    if len(r) < 12:
        return None
    return {"n": len(r), "win": (r > 0).mean(), "mean": r.mean(), "med": r.median(),
            "t": r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0.0}


def main():
    d = pd.read_parquet(TRADES).drop_duplicates(
        subset=["date", "structure", "dte", "hold_frac"])
    d["gz"] = d.date.map(gamma_z())
    d = d.dropna(subset=["gz"])

    print("=" * 104)
    print("WHICH EXPRESSION OF A DIRECTIONAL VIEW BELONGS IN WHICH GAMMA REGIME?")
    print("  Non-overlapping, real quotes (ask in / bid out). Direction is assumed, not predicted.")
    print("=" * 104)
    print(f"  {'structure':20s} {'LOW gamma (wide range)':>34s} {'HIGH gamma (pinned)':>32s}")
    print(f"  {'':20s} {'win':>7s}{'mean':>10s}{'med':>9s}{'t':>7s}"
          f"{'win':>9s}{'mean':>10s}{'med':>9s}{'t':>7s}")

    best = {"LOW": None, "HIGH": None}
    for name in DIRECTIONAL:
        g = d[d.structure == name]
        if len(g) < 100:
            continue
        hold = max(int(g.dte.median() * g.hold_frac.median()) or 21, 7)
        lo = stat(nonoverlap(g[g.gz < -0.5], hold).ret)
        hi = stat(nonoverlap(g[g.gz > 0.5], hold).ret)
        if not (lo and hi):
            continue
        print(f"  {name:20s} {lo['win']*100:6.1f}%{lo['mean']*100:+9.2f}%"
              f"{lo['med']*100:+8.1f}%{lo['t']:+7.2f}"
              f"{hi['win']*100:+8.1f}%{hi['mean']*100:+9.2f}%"
              f"{hi['med']*100:+8.1f}%{hi['t']:+7.2f}")
        for lab, s in (("LOW", lo), ("HIGH", hi)):
            # Rank on MEDIAN, not mean: a mean carried by one crash payoff is
            # not an outcome anyone can sit through at retail size.
            if s["med"] > 0 and s["t"] > 1.0:
                if best[lab] is None or s["med"] > best[lab][1]["med"]:
                    best[lab] = (name, s)

    print("\n" + "=" * 104)
    print("THE RULE THIS SUPPORTS")
    print("=" * 104)
    for lab, txt in (("LOW", "LOW gamma  (dealers amplify -> wide range)"),
                     ("HIGH", "HIGH gamma (dealers pin -> tight range)")):
        b = best[lab]
        if b:
            n, s = b
            print(f"  {txt:44s} -> {n:20s} "
                  f"win {s['win']*100:.0f}%  mean {s['mean']*100:+.1f}%  "
                  f"med {s['med']*100:+.1f}%  t {s['t']:+.2f}  n {s['n']}")
        else:
            print(f"  {txt:44s} -> nothing clears median>0 and t>1")
    print("\n  Direction is NOT supplied here. It comes from the weighted vote")
    print("  (flow 0.35 / short interest 0.30 / trend 0.35 / dark pool 0.15).")
    print("  This only decides the vehicle once that vote has taken a side.")


if __name__ == "__main__":
    main()
