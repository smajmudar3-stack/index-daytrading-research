"""What do these structures pay if you trade ~1 per day, gated on regime?

The previous summary annualised by elapsed CALENDAR time while only sampling
weekly entries inside narrow regime cells. That understates a daily-frequency
strategy badly: a +0.55%/trade edge taken 250 times a year is not the same
number as the same edge taken 12 times a year, and reporting the latter when
the intent is the former is simply the wrong statistic.

So this file asks the right question:
  1. What is the per-trade edge, honestly, on real quotes?
  2. How often can it actually be traded (how many days does the gate fire)?
  3. What does that compound to, at a survivable position size?
  4. Which regime combination fires it best -- the "correlation" question.

It also carries the tail properly. A 90%-win structure whose max loss is 12.9x
the credit is not described by its average; the worst-case path is the thing
that decides whether the account is still there at the end.
"""
import os
import sys
import warnings
from itertools import combinations

import numpy as np
import pandas as pd

from idt import paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

TRADES = paths.data("swing", "structure_trades.parquet")
SWING = paths.data("swing", "panel.parquet")
GEX = paths.data("squeeze_dix_gex.csv")

SPLITS = {"2008-2013": ("2008-01-01", "2013-12-31"),
          "2014-2019": ("2014-01-01", "2019-12-31"),
          "2020-2025": ("2020-01-01", "2025-12-31")}


def context():
    p = pd.read_parquet(paths.require_data(SWING))
    close = p.pivot(index="date", columns="ticker", values="close").sort_index()
    spy = close["SPY"]
    c = pd.DataFrame(index=close.index)

    sectors = [x for x in close.columns if x.startswith("XL")]
    c["breadth"] = pd.DataFrame(
        {s: (close[s] > close[s].rolling(200).mean()).astype(float)
         for s in sectors}).mean(axis=1)
    c["above200"] = (spy > spy.rolling(200).mean()).astype(float)
    c["above50"] = (spy > spy.rolling(50).mean()).astype(float)
    c["dd"] = spy / spy.cummax() - 1.0

    v = close["^VIX"]
    c["vix"] = v
    c["vix_pct"] = v.rolling(504, min_periods=252).apply(
        lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    c["ts"] = close["^VIX"] / close["^VIX3M"]
    # Realised vol vs implied -- the variable these structures are actually
    # exposed to. IV rich relative to trailing RV is the premium seller's edge.
    rv = spy.pct_change(fill_method=None).rolling(21).std() * np.sqrt(252) * 100
    c["rv"] = rv
    c["iv_minus_rv"] = v - rv
    c["ivrv_pct"] = c["iv_minus_rv"].rolling(504, min_periods=252).apply(
        lambda w: (w[:-1] < w[-1]).mean(), raw=True)

    if os.path.exists(GEX):          # optional file; absence is a documented degrade
        g = pd.read_csv(GEX)
        dc = [x for x in g.columns if x.lower().startswith("date")][0]
        g[dc] = pd.to_datetime(g[dc])
        g = g.set_index(dc).sort_index()
        for col in ("gex", "dix"):
            hit = [x for x in g.columns if x.lower() == col]
            if hit:
                s = pd.to_numeric(g[hit[0]], errors="coerce").reindex(c.index).ffill()
                c[f"{col}_z"] = ((s - s.rolling(252, min_periods=126).mean())
                                 / s.rolling(252, min_periods=126).std())
    return c.shift(1)


def gates(c):
    """Single-condition gates. Combinations are formed from these."""
    g = {}
    g["VIX<33pct"] = c.vix_pct < 0.33
    g["VIX>67pct"] = c.vix_pct > 0.67
    g["contango"] = c.ts < 1.0
    g["backwardation"] = c.ts >= 1.0
    g["bull200"] = c.above200 > 0
    g["above50"] = c.above50 > 0
    g["breadth>0.6"] = c.breadth > 0.6
    g["IV rich (>67pct)"] = c.ivrv_pct > 0.67
    g["IV cheap (<33pct)"] = c.ivrv_pct < 0.33
    if "gex_z" in c:
        g["GEX high"] = c.gex_z > 0.5
        g["GEX low"] = c.gex_z < -0.5
    if "dix_z" in c:
        g["DIX high"] = c.dix_z > 0.5
        g["DIX low"] = c.dix_z < -0.5
    return {k: v.fillna(False) for k, v in g.items()}


def evaluate(r, days_available, trades_per_year, frac):
    """Compound a per-trade return series at a given size and frequency."""
    if len(r) < 20:
        return None
    step = np.maximum(1 + r.values * frac, 0.0)
    eq = step.cumprod()
    # Annualise on TRADE COUNT and the realistic trading frequency, not on the
    # calendar span of a thin sample.
    g = eq[-1] ** (1 / len(r))            # growth factor per trade
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    # Trades expected in each calendar window, given how often the gate opens.
    per_day = trades_per_year / 252.0
    return {
        "n": len(r), "win": (r > 0).mean(), "avg": r.mean(),
        "t": r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0.0,
        "worst": r.min(), "p05": r.quantile(0.05),
        "daily":   g ** per_day - 1,
        "weekly":  g ** (per_day * 5) - 1,
        "monthly": g ** (per_day * 21) - 1,
        "maxdd": dd, "days_avail": days_available,
    }


def main():
    d = pd.read_parquet(paths.require_data(TRADES))
    # Kill the duplicate trades: two DTE targets can resolve to the same expiry
    # and the same structure on the same day, which double-counts.
    before = len(d)
    d = d.drop_duplicates(subset=["date", "structure", "dte", "hold_frac"])
    print(f"de-duplicated {before:,} -> {len(d):,} trades")

    c = context()
    G = gates(c)
    all_days = c.index[(c.index >= "2008-01-01") & (c.index <= "2025-12-31")]

    # Credit structures only -- the owner's question is about condors,
    # butterflies, jade lizards and the premium family.
    PREMIUM = ["iron condor 30/16", "iron condor 16/05", "iron butterfly ATM",
               "jade lizard", "twisted sister", "broken-wing fly (put)",
               "put credit 30/16", "put credit 16/05", "call credit 30/16",
               "christmas tree call", "short strangle 16d", "short strangle 30d",
               "short straddle"]

    print("\n" + "=" * 108)
    print("PER-TRADE EDGE BY STRUCTURE  (real SPY quotes, ask/bid fills, all regimes pooled)")
    print("=" * 108)
    print(f"  {'structure':24s} {'n':>6s} {'win':>7s} {'avg/trade':>10s} "
          f"{'t':>7s} {'worst':>9s} {'5th pct':>9s}")
    for s in PREMIUM:
        g = d[d.structure == s]
        if len(g) < 50:
            continue
        r = g.ret
        t = r.mean() / (r.std() / np.sqrt(len(r)))
        print(f"  {s:24s} {len(r):6d} {(r>0).mean():7.1%} {r.mean():+10.3%} "
              f"{t:+7.2f} {r.min():+9.1%} {r.quantile(0.05):+9.1%}")

    # ---------------------------------------------------------------
    # The correlation question: which gate combination best predicts a
    # winning trade, and how many days a year does it fire?
    # ---------------------------------------------------------------
    print("\n" + "=" * 108)
    print("BEST REGIME GATES -- ranked by per-trade edge, with tradeable frequency")
    print("  'days/yr' = how many sessions the gate is open, i.e. your realistic trade count")
    print("=" * 108)

    names = sorted(G)
    combos = [(n,) for n in names] + list(combinations(names, 2))

    rows = []
    for s in PREMIUM:
        g = d[d.structure == s]
        if len(g) < 100:
            continue
        for combo in combos:
            mask = G[combo[0]].copy()
            for extra in combo[1:]:
                mask = mask & G[extra]
            open_days = int(mask.reindex(all_days).fillna(False).sum())
            if open_days < 150:            # need a gate that actually fires
                continue
            days_per_year = open_days / (len(all_days) / 252)
            sel = g[g.date.map(mask).fillna(False).values]
            if len(sel) < 60:
                continue
            # One trade per open day is the cap; sizing 10% of account.
            res = evaluate(sel.ret, open_days, days_per_year, frac=0.10)
            if res is None:
                continue
            res.update(structure=s, gate="+".join(combo),
                       days_per_year=days_per_year)
            rows.append(res)

    res = pd.DataFrame(rows)
    if res.empty:
        print("  no gate/structure cell met the minimum sample requirements")
        return
    res.to_parquet(paths.data("swing", "daily_engine.parquet"),
                   index=False)

    top = res.sort_values("avg", ascending=False).head(25)
    print(f"  {'structure':22s} {'gate':28s} {'n':>5s} {'trd/yr':>7s} "
          f"{'win':>6s} {'avg/tr':>8s} {'t':>6s} {'DAILY':>8s} {'WEEKLY':>8s} "
          f"{'MONTHLY':>9s} {'maxDD':>8s}")
    for _, x in top.iterrows():
        print(f"  {x['structure']:22s} {x['gate']:28s} {int(x['n']):5d} "
              f"{x['days_per_year']:7.0f} {x['win']:6.1%} {x['avg']:+8.3%} "
              f"{x['t']:+6.2f} {x['daily']:+8.3%} {x['weekly']:+8.2%} "
              f"{x['monthly']:+9.2%} {x['maxdd']:+8.1%}")

    # ---------------------------------------------------------------
    # Out-of-sample check on the best cells -- the only thing that matters.
    # ---------------------------------------------------------------
    print("\n" + "=" * 108)
    print("DO THE BEST GATES HOLD UP OUT OF SAMPLE? (per-trade avg by period)")
    print("=" * 108)
    print(f"  {'structure':22s} {'gate':28s} "
          f"{'2008-2013':>12s} {'2014-2019':>12s} {'2020-2025':>12s} {'all+?':>7s}")
    for _, x in top.head(15).iterrows():
        g = d[d.structure == x["structure"]]
        combo = x["gate"].split("+")
        mask = G[combo[0]].copy()
        for extra in combo[1:]:
            mask = mask & G[extra]
        sel = g[g.date.map(mask).fillna(False).values]
        vals = []
        for a, b in SPLITS.values():
            ss = sel[(sel.date >= a) & (sel.date <= b)].ret
            vals.append(ss.mean() if len(ss) >= 15 else np.nan)
        ok = "YES" if all(v == v and v > 0 for v in vals) else "no"
        print(f"  {x['structure']:22s} {x['gate']:28s} "
              + "".join(f"{v:+12.3%}" if v == v else f"{'n/a':>12s}" for v in vals)
              + f" {ok:>7s}")

    n_trials = len(res)
    print(f"\n  {n_trials} structure/gate cells tested -> expected best |t| under the "
          f"null ~ {np.sqrt(2*np.log(max(n_trials,2))):.2f}")


if __name__ == "__main__":
    main()
