"""Is volatility actually predictable on our data, and can anything beat HAR?

Direction topped out at ~51% on this data. Volatility is the other question, and
it matters here for a specific reason: the 0DTE break-even hurdle is a direct
function of MOVE SIZE, so a credible move forecast decides which days are
tradeable at all.

The benchmark is deliberately strong. "HARd to Beat" (Branco et al., 1,455
stocks) found machine learning fails to beat a properly specified HAR once its
rolling window and re-estimation frequency are set correctly -- the fitting
scheme mattered more than the model. So HAR is the bar, not a strawman, and
every addition must beat it on the same walk-forward.

    HAR (Corsi):  log RV_{t+1} = a + b_d logRV_t + b_w logRV_{t-4..t}
                                   + b_m logRV_{t-21..t}

Measured against two honest baselines that are easy to forget:
  RANDOM WALK   forecast tomorrow = today. Beating this is the minimum bar.
  CONSTANT      forecast the training-window mean. R2 is measured against THIS,
                not against a rolling mean, which inflates R2 (Gu-Kelly-Xiu
                footnote 34: ~3pp/month of pure inflation).

Losses: MSE on log RV, and QLIKE, which is the standard loss for variance
because it penalises under-prediction asymmetrically and is robust to noise in
the RV proxy.

Evaluation is expanding-window walk-forward: refit on everything up to day t,
predict t+1, never the reverse.
"""
import glob
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T = pd.Timestamp("09:30").time()
CLOSE_T = pd.Timestamp("16:00").time()


def realized_vol(sym, bar_min=5):
    """Daily realized variance from intraday returns, regular hours only."""
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    df = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)]
    # Resample to bar_min to damp microstructure noise -- 5 minutes is the
    # convention precisely because 1-minute RV is contaminated by bid-ask bounce.
    px = df["close"].resample(f"{bar_min}min").last().dropna()
    r = np.log(px).diff()
    r = r[pd.DatetimeIndex(r.index).time >= OPEN_T]
    day = pd.DatetimeIndex(r.index).date
    rv = r.groupby(day).apply(lambda s: np.sum(s.values ** 2))
    cnt = r.groupby(day).size()
    rv = rv[cnt >= 50]                     # drop half days and gappy sessions
    return rv[rv > 0]


def har_design(lrv):
    """Lagged daily / weekly / monthly averages of log RV."""
    d = pd.DataFrame({"y": lrv})
    d["x_d"] = lrv.shift(1)
    d["x_w"] = lrv.shift(1).rolling(5).mean()
    d["x_m"] = lrv.shift(1).rolling(22).mean()
    return d.dropna()


def qlike(actual_var, pred_var):
    a = np.asarray(actual_var, float)
    p = np.clip(np.asarray(pred_var, float), 1e-12, None)
    return np.mean(a / p - np.log(a / p) - 1)


def walk_forward(d, cols, min_train=150):
    """Expanding-window OLS. Returns (pred_logRV, actual_logRV) aligned."""
    X = np.column_stack([np.ones(len(d))] + [d[c].values for c in cols])
    y = d["y"].values
    preds, acts = [], []
    for i in range(min_train, len(d)):
        b, *_ = np.linalg.lstsq(X[:i], y[:i], rcond=None)
        preds.append(X[i] @ b)
        acts.append(y[i])
    return np.array(preds), np.array(acts)


def score(name, pred_l, act_l, bench_l):
    """R2 against the CONSTANT benchmark, plus QLIKE in variance space."""
    sse = np.sum((act_l - pred_l) ** 2)
    sst = np.sum((act_l - bench_l) ** 2)
    r2 = 1 - sse / sst
    # log->variance needs the Jensen correction, else systematic under-prediction
    resid_var = np.var(act_l - pred_l)
    q = qlike(np.exp(act_l), np.exp(pred_l + 0.5 * resid_var))
    corr = np.corrcoef(pred_l, act_l)[0, 1]
    print(f"    {name:34s} R2 {r2*100:6.1f}%   QLIKE {q:7.4f}   corr {corr:+.3f}")
    return r2, q


def main():
    print("=" * 92)
    print("REALIZED VOLATILITY -- is it predictable, and can anything beat HAR?")
    print("=" * 92)

    for sym in ("SPY", "QQQ"):
        rv = realized_vol(sym)
        lrv = np.log(rv)
        d = har_design(lrv)
        n_oos = len(d) - 150
        ann = np.sqrt(rv * 252) * 100
        print(f"\n  {sym}   {len(rv)} sessions, {n_oos} out-of-sample")
        print(f"    realized vol (annualised): median {ann.median():.1f}%  "
              f"p10 {ann.quantile(.1):.1f}%  p90 {ann.quantile(.9):.1f}%")

        # Constant benchmark: expanding mean of log RV, which is what an
        # uninformed forecaster would say.
        y = d["y"].values
        const = np.array([y[:i].mean() for i in range(150, len(d))])
        act = y[150:]

        print(f"    {'model':34s} {'R2':>9s}   {'QLIKE':>12s}   {'corr':>6s}")
        # Random walk: tomorrow = today.
        rw = d["x_d"].values[150:]
        score("random walk (yesterday's RV)", rw, act, const)

        p, a = walk_forward(d, ["x_d"])
        score("AR(1) on log RV", p, a, const)

        p, a = walk_forward(d, ["x_d", "x_w"])
        score("HAR without monthly", p, a, const)

        p, a = walk_forward(d, ["x_d", "x_w", "x_m"])
        har_r2, har_q = score("HAR (daily+weekly+monthly)", p, a, const)

        # Does the realized RANGE add anything over squared returns?
        d2 = d.copy()
        d2["x_min"] = d2["x_d"].rolling(5).min()
        d2["x_max"] = d2["x_d"].rolling(5).max()
        d2 = d2.dropna()
        p, a = walk_forward(d2, ["x_d", "x_w", "x_m", "x_min", "x_max"])
        const2 = np.array([d2["y"].values[:i].mean() for i in range(150, len(d2))])
        score("HAR + 5d min/max of RV", p, a, const2)

        print(f"    -> HAR reference: R2 {har_r2*100:.1f}%, QLIKE {har_q:.4f}")

    print("\n" + "=" * 92)
    print("  R2 here is against a CONSTANT benchmark, not a rolling mean.")
    print("  Compare with direction on the same data: R2 0.11%, hit rate 51.0%.")
    print("=" * 92)


if __name__ == "__main__":
    main()
