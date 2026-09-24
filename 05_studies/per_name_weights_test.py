"""per_name_weights_test.py — Sholo's design: weight each factor by how much it has moved
THAT stock, not by how much it moves the average stock. Does a per-name model beat one
set of weights for everyone?

For every name with at least 104 weeks of history, at each week t, fit a ridge regression
of the name's own forward 21-session excess return on its own past factor values (weeks
whose forward return was known by t), predict this week, and rank names on that
prediction. Against it: the pooled Fama-MacBeth model on the same factors (one set of
weights for everyone, estimated on the same past), and a plain equal-weight composite of
the factors that survived signal_accuracy.py. Same panel, same horizon, same scoring: IC,
top-decile hit rate, payoff, three splits, net of 15 bp a side.

The prior: per-name weights on ~100-300 noisy observations per name overfit that name's
past accidents; the literature (Lewellen 2015, "The cross-section of expected stock
returns") finds pooled weights beat name-specific ones out of sample. The test says whether
this sample agrees. Whichever wins becomes the swing ranker's weights.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS  # noqa: E402

warnings.filterwarnings("ignore")
PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
FEATS = ["sue", "resid_mom", "mom12_1", "buyback_yield", "fcf_yield", "rev1m", "ivol63", "ma50_200", "iv_hv", "d_shares_yoy"]
SIGN = {"sue": 1, "resid_mom": 1, "mom12_1": 1, "buyback_yield": 1, "fcf_yield": 1, "rev1m": -1, "ivol63": -1,
        "ma50_200": 1, "iv_hv": -1, "d_shares_yoy": -1}
Y = "ex21"
MIN_HIST = 104
RIDGE = 5.0
COST = 0.0015


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def score(p, label):
    p = p.dropna(subset=["pred", Y])
    p = p[p.groupby("date").pred.transform("size") >= 100]
    ics = p.groupby("date").apply(lambda g: stats.spearmanr(g.pred, g[Y])[0], include_groups=False).dropna()
    p["dec"] = p.groupby("date").pred.transform(lambda v: pd.qcut(v.rank(method="first"), 10, labels=False, duplicates="drop"))
    top = p[p.dec == 9]
    s = top.groupby("date")[Y].mean()
    win, loss = top[top[Y] > 0][Y].mean(), top[top[Y] <= 0][Y].mean()
    sets = {d: set(g.act_symbol) for d, g in top.groupby("date")}
    ks = sorted(sets)
    to = np.mean([1 - len(sets[a] & sets[b]) / max(len(sets[b]), 1) for a, b in zip(ks[:-1], ks[1:])])
    net = (s.mean() - 2 * COST * to) * 13 * 100
    sp = {k: f"{ics[(ics.index >= a) & (ics.index <= b)].mean():+.3f}" for k, (a, b) in SPLITS.items()}
    print(f"{label:46s} dates {len(ics):3d} IC {ics.mean():+.4f} (t {_t(ics):+.1f}) | top decile hit {(top[Y]>0).mean():.3f} "
          f"avg {s.mean()*100:+.2f}%/4wk payoff {win/-loss:.2f} turnover {to*100:.0f}% net {net:+.1f}%/yr | IC by split {sp}")


def main():
    w = pd.read_parquet(os.path.join(PANEL, "signal_panel.parquet"))
    dates_all = np.sort(w.date.unique())[::4]                 # non-overlapping 4-week steps
    d = w[w.date.isin(dates_all)][["date", "act_symbol", Y] + FEATS].copy()
    for f in FEATS:
        d[f] = (d.groupby("date")[f].rank(pct=True) - 0.5) * SIGN[f]
    d = d.dropna(subset=[Y])
    d[FEATS] = d[FEATS].fillna(0.0)
    d = d.sort_values(["act_symbol", "date"])
    print(f"{len(d):,} name-months, {d.act_symbol.nunique()} names, {d.date.nunique()} dates")
    # 1. plain composite: equal weight of the signed ranks
    d["pred"] = d[FEATS].mean(axis=1)
    score(d, "equal-weight composite (no fitting)")
    # 2. pooled Fama-MacBeth, expanding, lag 2 steps (the forward return must be known)
    dates = np.sort(d.date.unique())
    betas = {}
    for dt in dates:
        g = d[d.date == dt]
        if len(g) < 200:
            continue
        X = np.column_stack([np.ones(len(g))] + [g[f].values for f in FEATS])
        b, *_ = np.linalg.lstsq(X, g[Y].values, rcond=None)
        betas[dt] = b[1:]
    preds = []
    bk = sorted(betas)
    for i, dt in enumerate(dates):
        past = [betas[k] for k in bk if k <= dates[max(0, i - 2)] and k < dt]
        if len(past) < 12:
            continue
        g = d[d.date == dt].copy()
        g["pred"] = g[FEATS].values @ np.mean(past, axis=0)
        preds.append(g)
    pooled = pd.concat(preds)
    score(pooled, "pooled weights (Fama-MacBeth, expanding)")
    # 3. per-name ridge: each name's own past
    preds = []
    lam = RIDGE * np.eye(len(FEATS) + 1)
    lam[0, 0] = 0.0
    for tk, g in d.groupby("act_symbol"):
        g = g.sort_values("date")
        if len(g) < 30:
            continue
        X = np.column_stack([np.ones(len(g))] + [g[f].values for f in FEATS])
        y = g[Y].values
        out = np.full(len(g), np.nan)
        for i in range(26, len(g)):                            # at least ~2 years of the name's own months
            Xp, yp = X[:i - 1], y[:i - 1]                      # rows whose forward return is realised
            b = np.linalg.solve(Xp.T @ Xp + lam, Xp.T @ yp)
            out[i] = X[i] @ b
        g = g.copy()
        g["pred"] = out
        preds.append(g)
    per = pd.concat(preds)
    score(per, "PER-NAME weights (ridge on the name's own past)")
    # 4. blend: per-name shrunk halfway to pooled
    m = per[["date", "act_symbol", "pred"]].merge(pooled[["date", "act_symbol", "pred"]], on=["date", "act_symbol"], suffixes=("_n", "_p"))
    m["pred"] = (m.groupby("date").pred_n.rank(pct=True) + m.groupby("date").pred_p.rank(pct=True)) / 2
    m = m.merge(d[["date", "act_symbol", Y]], on=["date", "act_symbol"])
    score(m, "blend: per-name and pooled, equal ranks")
    # how stable are per-name weights? sign agreement of a name's beta with the pooled sign
    print("\nPer-name weights vs the pooled sign, last fit per name: share of names where the sign agrees")
    agree = {}
    for tk, g in d.groupby("act_symbol"):
        if len(g) < 40:
            continue
        X = np.column_stack([np.ones(len(g))] + [g[f].values for f in FEATS])
        b = np.linalg.solve(X.T @ X + lam, X.T @ g[Y].values)
        for j, f in enumerate(FEATS):
            agree.setdefault(f, []).append(b[j + 1] > 0)
    print("  " + ", ".join(f"{f} {np.mean(v)*100:.0f}%" for f, v in agree.items()))


if __name__ == "__main__":
    main()
