"""Stress-test the gap-and-go-with-volume edge before believing it. Kill it if it's fragile:
  1. OUT-OF-SAMPLE: train 2019-2023 vs test 2024-2026
  2. SURVIVORSHIP: exclude the mega-winners (NVDA/TSLA/MSTR/PLTR/AVGO/SMCI) — does it survive?
  3. COST STRESS: 15 / 25 / 40 bps round trip
  4. PER-YEAR consistency + how concentrated in a few names
"""
import numpy as np
import pandas as pd
import momentum_stocks as ms

WINNERS = {"NVDA","TSLA","MSTR","PLTR","AVGO","SMCI","COIN","ARM"}


def build():
    rows = []
    for tk in ms.UNIV:
        d = ms.load(tk)
        if d is None:
            continue
        m = (d["gap"] > 0.03) & (d["rvol"] > 1.5)
        sub = d[m].copy()
        sub["ticker"] = tk
        sub["r_go"] = sub["intraday"]           # gross (subtract cost later)
        rows.append(sub[["ticker", "r_go"]].assign(date=sub.index))
    return pd.concat(rows).set_index("date").sort_index()


def rep(name, r, cost=0.0015):
    r = (r - cost).dropna()
    if len(r) < 30:
        print(f"  {name:38} n={len(r)} too few"); return
    t = r.mean()/(r.std()/np.sqrt(len(r)))
    print(f"  {name:38} ret {r.mean()*100:+.3f}%  t {t:+.1f}  win {(r>0).mean()*100:.0f}%  n={len(r)}"
          + ("  <== holds" if t >= 2 else "  <== FAILS"))


def main():
    g = build()
    print(f"gap>3% & RVOL>1.5 long-intraday: {len(g)} trades, {g.ticker.nunique()} stocks\n")
    print("=== 1. OUT-OF-SAMPLE ===")
    rep("train 2019-2023", g[g.index < "2024-01-01"]["r_go"])
    rep("test  2024-2026 (OOS)", g[g.index >= "2024-01-01"]["r_go"])
    print("=== 2. SURVIVORSHIP — exclude mega-winners ===")
    rep("all names", g["r_go"])
    rep("EX mega-winners", g[~g.ticker.isin(WINNERS)]["r_go"])
    print("=== 3. COST STRESS (round trip) ===")
    for c in (0.0015, 0.0025, 0.0040):
        rep(f"{c*1e4:.0f} bps cost", g["r_go"], cost=c)
    print("=== 4. PER-YEAR consistency ===")
    for y in sorted(set(g.index.year)):
        rep(f"  {y}", g[g.index.year == y]["r_go"])
    print("=== concentration: top-5 names' share of total P&L ===")
    pnl = (g["r_go"] - 0.0015)
    by = pnl.groupby(g.ticker).sum().sort_values(ascending=False)
    tot = pnl.sum()
    print("  " + ", ".join(f"{t}:{v/tot*100:.0f}%" for t, v in by.head(5).items()) + f"  (total {tot*100:.0f}%)")


if __name__ == "__main__":
    main()
