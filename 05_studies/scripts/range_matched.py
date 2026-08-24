"""Match the STRUCTURE to the predicted RANGE, since range is what gamma predicts.

Dealer gamma does not predict direction -- 1,001 gated cells, zero survived. But
it predicts RANGE with a large, monotone, every-year-stable effect (realised/
implied 0.843x on high-gamma days vs 1.139x on low, t = -13.2 over 15 years).

So the honest use is: let gamma choose the STRUCTURE, not the side.

    LOW gamma  -> dealers amplify -> big range  -> BUY premium  (straddle/strangle)
    HIGH gamma -> dealers pin     -> small range -> SELL premium (condor/butterfly)

That is the hypothesis. It is testable and it has never been tested here in this
form -- the earlier sweeps gated a FIXED structure on gamma rather than letting
gamma pick between opposite structures.

Two guards, both from mistakes made earlier in this project:
  * NON-OVERLAPPING entries. Daily sampling of an H-day trade counts the same
    days repeatedly and inflates t by ~sqrt(H); it turned a t=+1.04 result into
    t=+6.56 once already.
  * Real quotes, bought at the ask and sold at the bid. Mid-price fills are what
    make every published version of this look tradeable.
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

LONG_PREMIUM = ["long straddle", "long strangle 30d", "long call 0.50d"]
SHORT_PREMIUM = ["iron condor 30/16", "iron condor 16/05", "iron butterfly ATM",
                 "short strangle 16d", "short straddle"]


def gamma_state():
    g = pd.read_csv(GEX)
    dc = [c for c in g.columns if c.lower().startswith("date")][0]
    g[dc] = pd.to_datetime(g[dc])
    g = g.set_index(dc).sort_index()
    col = [c for c in g.columns if c.lower() == "gex"]
    if not col:
        return None
    s = pd.to_numeric(g[col[0]], errors="coerce")
    z = (s - s.rolling(252, min_periods=126).mean()) / s.rolling(252, min_periods=126).std()
    return z.shift(1)          # prior close = knowable before the open


def nonoverlap(df, days):
    """Keep one trade per `days` window so t-stats are not inflated."""
    df = df.sort_values("date")
    keep, last = [], None
    for _, r in df.iterrows():
        if last is None or (r["date"] - last).days >= days:
            keep.append(r)
            last = r["date"]
    return pd.DataFrame(keep)


def stat(r):
    r = pd.Series(r).dropna()
    if len(r) < 12:
        return None
    t = r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0.0
    return {"n": len(r), "win": (r > 0).mean(), "mean": r.mean(),
            "med": r.median(), "t": t}


def main():
    d = pd.read_parquet(TRADES).drop_duplicates(
        subset=["date", "structure", "dte", "hold_frac"])
    z = gamma_state()
    if z is None:
        print("no GEX series"); return
    d["gz"] = d.date.map(z)
    d = d.dropna(subset=["gz"])
    print(f"{len(d):,} structure-trades with a prior-close gamma read\n")

    print("=" * 100)
    print("RANGE-MATCHED STRUCTURE SELECTION — does gamma choose the right side?")
    print("  LOW gamma (z<-0.5) should favour BUYING premium; HIGH gamma (z>+0.5) SELLING it.")
    print("  Non-overlapping entries; real quotes, ask in / bid out.")
    print("=" * 100)
    print(f"  {'structure':22s} {'regime':12s} {'n':>5s} {'win':>7s} "
          f"{'mean':>9s} {'median':>9s} {'t':>7s}")

    rows = []
    for name in LONG_PREMIUM + SHORT_PREMIUM:
        g = d[d.structure == name]
        if len(g) < 100:
            continue
        hold = int(g.dte.median() * g.hold_frac.median()) or 21
        for lab, mask in (("LOW gamma", g.gz < -0.5),
                          ("HIGH gamma", g.gz > 0.5),
                          ("all", pd.Series(True, index=g.index))):
            sub = nonoverlap(g[mask], max(hold, 7))
            s = stat(sub.ret) if len(sub) else None
            if not s:
                continue
            print(f"  {name:22s} {lab:12s} {s['n']:5d} {s['win']*100:6.1f}% "
                  f"{s['mean']*100:+8.2f}% {s['med']*100:+8.1f}% {s['t']:+7.2f}")
            rows.append({"structure": name, "regime": lab, **s,
                         "side": "long" if name in LONG_PREMIUM else "short"})
        print()

    r = pd.DataFrame(rows)
    print("=" * 100)
    print("THE HYPOTHESIS, SCORED")
    print("=" * 100)
    for side, want_regime in (("long", "LOW gamma"), ("short", "HIGH gamma")):
        sub = r[r.side == side]
        if sub.empty:
            continue
        fav = sub[sub.regime == want_regime]["mean"].mean()
        base = sub[sub.regime == "all"]["mean"].mean()
        opp = sub[sub.regime == ("HIGH gamma" if side == "long" else "LOW gamma")]["mean"].mean()
        verdict = "SUPPORTED" if (fav == fav and fav > base and fav > opp) else "not supported"
        print(f"  {side.upper():5s} premium in {want_regime:11s}: "
              f"{fav*100:+6.2f}%  vs all {base*100:+6.2f}%  vs opposite {opp*100:+6.2f}%"
              f"   -> {verdict}")
    best = r[(r.t > 2) & (r["mean"] > 0)]
    print(f"\n  cells with positive mean AND t>2: {len(best)}")
    if not best.empty:
        for _, x in best.sort_values("t", ascending=False).iterrows():
            print(f"    {x['structure']:22s} {x['regime']:11s} "
                  f"mean {x['mean']*100:+.2f}%  t {x['t']:+.2f}  n {int(x['n'])}")


if __name__ == "__main__":
    main()
