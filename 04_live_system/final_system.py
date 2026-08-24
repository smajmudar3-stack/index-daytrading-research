"""Final merged index system with CLEAN locked weights (rounded, not overfit to exact
optimizer output): 75% overnight + 15% gap-fade + 10% RSI-2 dip. Full-sample + by-year."""
import numpy as np
import pandas as pd
import multi_edge as me

W = {"E1_overnight": 0.75, "E3_gapfade": 0.15, "E2_rsi2dip": 0.10, "E4_trend": 0.0}

def sh(r):
    r = r.dropna(); return r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else 0

for tk in ["SPY", "QQQ"]:
    E = me.build(tk)
    vols = E.std()
    # scale each edge to unit vol, then apply target weights, then scale whole thing to ~E1's vol
    z = E / vols
    merged = sum(z[c]*W[c] for c in E.columns)
    merged = merged * (E["E1_overnight"].std() / merged.std())  # match overnight's vol for fair compare
    cagr = (1+merged).prod()**(252/len(merged)) - 1
    dd = ((1+merged).cumprod()/(1+merged).cumprod().cummax()-1).min()
    print(f"\n===== {tk}  MERGED SYSTEM (75/15/10) — full sample 2005-2026 =====")
    print(f"  Sharpe {sh(merged):+.2f}  CAGR {cagr*100:+.1f}%  maxDD {dd*100:.1f}%  vs E1-alone Sharpe {sh(E['E1_overnight']):+.2f} DD {((1+E['E1_overnight']).cumprod()/(1+E['E1_overnight']).cumprod().cummax()-1).min()*100:.1f}%")
    yrs = sorted(set(merged.index.year))
    pos = sum(1 for y in yrs if (1+merged[merged.index.year == y]).prod()-1 > 0)
    print(f"  positive years: {pos}/{len(yrs)}")
    byyr = "  ".join(f"{y}:{((1+merged[merged.index.year==y]).prod()-1)*100:+.0f}%" for y in yrs)
    print(f"  {byyr}")
