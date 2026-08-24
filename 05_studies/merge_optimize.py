"""Merge the edges the RIGHT way (weight by quality, not equally) and test OUT-OF-SAMPLE.
Question: can any blend beat the dominant overnight edge (E1) alone? Fit weights on
2005-2015, test untouched on 2016-2026 — the honest test of whether merging adds value."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import multi_edge as me

def sh(r):
    r = r.dropna()
    return r.mean()/r.std()*np.sqrt(252) if len(r) > 20 and r.std() > 0 else 0

def stats(r, lbl):
    r = r.dropna()
    cagr = (1+r).prod()**(252/len(r)) - 1
    dd = ((1+r).cumprod()/(1+r).cumprod().cummax()-1).min()
    print(f"    {lbl:28} Sharpe {sh(r):+.2f}  CAGR {cagr*100:+6.2f}%  maxDD {dd*100:6.1f}%")


def main():
    for tk in ["SPY", "QQQ"]:
        E = me.build(tk)
        split = E.index[len(E)//2 + 200]
        tr, te = E[E.index < split], E[E.index >= split]
        print(f"\n===== {tk}  (train {tr.index.min().date()}..{tr.index.max().date()}, test {te.index.min().date()}..) =====")

        # baselines on TEST
        print("  --- OUT-OF-SAMPLE (2016-2026) ---")
        stats(te["E1_overnight"], "E1 overnight ALONE")
        vols = tr.std().replace(0, np.nan); ew = (1/vols)/(1/vols).sum()
        stats((te*ew).sum(axis=1), "equal-risk merge")
        shw = tr.apply(sh).clip(lower=0); shw = shw/shw.sum()
        stats((te*shw).sum(axis=1), "Sharpe-weighted merge")

        # optimize weights on TRAIN to max Sharpe, apply to TEST (long-only, sum=1)
        def neg_sh(w):
            return -sh((tr*w).sum(axis=1))
        res = minimize(neg_sh, np.repeat(0.25, 4), bounds=[(0, 1)]*4,
                       constraints=[{"type": "eq", "fun": lambda w: w.sum()-1}])
        w = res.x
        print(f"  optimized weights (fit on train): " +
              ", ".join(f"{c.split('_')[0]}={wi:.2f}" for c, wi in zip(E.columns, w)))
        stats((te*w).sum(axis=1), "OPTIMIZED merge (OOS)")
        # E1 + a small sleeve of the best diversifier (lowest corr to E1)
        corr_e1 = tr.corr()["E1_overnight"].drop("E1_overnight")
        div = corr_e1.idxmin()
        for frac in (0.1, 0.2):
            blend = te["E1_overnight"]*(1-frac) + te[div]*frac*(tr["E1_overnight"].std()/tr[div].std())
            stats(blend, f"85/15-style E1+{frac:.0%} {div.split('_')[0]}")


if __name__ == "__main__":
    main()
