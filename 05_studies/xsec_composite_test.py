"""xsec_composite_test.py — do the three least-bad weekly predictors add up to a direction?

xsec_predictors_test.py found nothing that clears the multiple-testing bar on its own.
The three with the right sign in every split were post-earnings drift (pead1), days to
cover (short interest / volume) and one-week reversal (ret5). This asks the only question
the weekly book actually needs answered: if you take the top and bottom decile of their
equal-weight rank composite, how often is the SIGN of the next 5/10-day move right, and by
how much? A book that pays ~20% of risk per round trip on a debit spread needs a lot more
than 52%.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS, universe, weekly  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
PARTS = {"pead1": +1, "days_to_cover": -1, "ret5": -1}


def main():
    pd.set_option("display.width", 200)
    df = pd.read_parquet(os.path.join(PANEL, "xsec_panel.parquet"))
    df["act_symbol"] = df.act_symbol.astype(str)
    u = weekly(universe(df), 1).copy()
    for f, s in PARTS.items():
        u[f"z_{f}"] = u.groupby("date")[f].rank(pct=True).sub(0.5).mul(2 * s)
    zc = [f"z_{f}" for f in PARTS]
    u["comp"] = u[zc].mean(axis=1, skipna=True)
    u["n_parts"] = u[zc].notna().sum(axis=1)
    for min_parts in (1, 2, 3):
        d = u[u.n_parts >= min_parts]
        for h in (5, 10):
            y = f"fwd{h}"
            x = d[["date", "comp", y]].dropna()
            ics = x.groupby("date").apply(lambda g: stats.spearmanr(g.comp, g[y])[0] if len(g) >= 30 else np.nan,
                                          include_groups=False).dropna()
            x = x[x.groupby("date").comp.transform("size") >= 50]
            x["dec"] = x.groupby("date").comp.transform(
                lambda v: pd.qcut(v.rank(method="first"), 10, labels=False, duplicates="drop"))
            top, bot = x[x.dec == 9], x[x.dec == 0]
            hit_top, hit_bot = (top[y] > 0).mean(), (bot[y] < 0).mean()
            # direction accuracy vs the cross-sectional median move that week, i.e. relative
            rel = x[y] - x.groupby("date")[y].transform("median")
            rt, rb = (rel[x.dec == 9] > 0).mean(), (rel[x.dec == 0] < 0).mean()
            print(f"parts>={min_parts} h={h}: n={len(x):,} dates={len(ics)} IC={ics.mean():+.4f} "
                  f"t={ics.mean()/ics.std()*np.sqrt(len(ics)):+.2f} | top decile up {hit_top*100:.1f}% "
                  f"(rel {rt*100:.1f}%) mean {top[y].mean()*100:+.2f}% | bottom decile down {hit_bot*100:.1f}% "
                  f"(rel {rb*100:.1f}%) mean {bot[y].mean()*100:+.2f}% | L-S {((top[y].mean()-bot[y].mean())*1e4):+.0f}bp")
            for k, (a, b) in SPLITS.items():
                sub = ics[(ics.index >= a) & (ics.index <= b)]
                if len(sub) >= 15:
                    print(f"      {k}: IC {sub.mean():+.4f} t{sub.mean()/sub.std()*np.sqrt(len(sub)):+.1f}")


if __name__ == "__main__":
    main()
