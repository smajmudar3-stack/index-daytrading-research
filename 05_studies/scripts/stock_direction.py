"""Market-conditioned stock direction for 5-10 day swing trades.

THE CENTRAL IDEA, which is the owner's own observation made quantitative:
a stock's move is two different things added together, and they need two
different forecasts.

    r_stock  =  alpha  +  beta * r_market  +  residual

  * The beta*r_market part is the stock "copying the market". Forecasting it
    is a MARKET-TIMING problem -- and it is the same problem for every stock,
    so it is solved once, from the regime work, and then levered by beta.
  * The residual is the stock moving on its own. Forecasting it is a
    STOCK-SELECTION problem. Residual momentum (Blitz-Huij-Martens 2011) is
    the documented anomaly here and it is materially stronger than plain
    momentum precisely because it strips out the market component.

So the expected move over the holding period is:

    E[move] = beta * E[market move] + E[residual move]

which says something immediately useful: a high-beta stock is the LEVERED
expression of a market view, not an independent bet. Buying calls on NVDA
because "the market looks good" is a market trade at ~2x size, and should be
sized as one. A low-beta / low-R^2 name is where stock-specific work pays.

Every statistic here is cross-sectional (rank-based) rather than absolute.
That matters: the universe has survivorship bias and equities drift up, so an
absolute long-side win rate is flattered by both. A top-decile-minus-
bottom-decile spread is immune to a common drift that lifts everything.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from swing_lab import SPLITS, deflated_sharpe, pch, slice_dates, zscore_past  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCKS = os.path.join(ROOT, "data", "stocks", "panel.parquet")
SWING = os.path.join(ROOT, "data", "swing", "panel.parquet")
OUT = os.path.join(ROOT, "data", "swing")

BETA_WIN = 126   # ~6 months, the standard estimation window
HORIZONS = [5, 10]  # "days to 2 weeks"
COST_BPS = 5.0


def load():
    st = pd.read_parquet(STOCKS)
    sw = pd.read_parquet(SWING)

    close = st.pivot(index="date", columns="ticker", values="close").sort_index()
    open_ = st.pivot(index="date", columns="ticker", values="open").sort_index()
    vol = st.pivot(index="date", columns="ticker", values="volume").sort_index()

    mkt = sw[sw.ticker == "SPY"].set_index("date")["close"].sort_index()
    mkt = mkt.reindex(close.index).ffill()
    return close, open_, vol, mkt, sw


def beta_decompose(close, mkt, win=BETA_WIN):
    """Rolling past-only beta, R^2 and residual returns for every stock.

    Uses covariance/variance over a trailing window ending YESTERDAY. The
    .shift(1) at the end is what keeps today's move out of today's beta.
    """
    r = pch(close)
    rm = pch(mkt)

    rm_var = rm.rolling(win, min_periods=60).var()
    beta = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
    r2 = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)

    for tk in close.columns:
        cov = r[tk].rolling(win, min_periods=60).cov(rm)
        b = cov / rm_var
        beta[tk] = b
        corr = r[tk].rolling(win, min_periods=60).corr(rm)
        r2[tk] = corr**2

    beta = beta.shift(1)
    r2 = r2.shift(1)

    # Residual = what the stock did that the market does NOT explain.
    resid = r.sub(beta.mul(rm, axis=0))
    return beta, r2, resid, r, rm


def build_stock_features(close, vol, beta, r2, resid, r, rm):
    """Signal library. Everything shifted so it is knowable at the prior close."""
    f = {}

    # --- residual momentum: the documented cross-sectional anomaly ---------
    for lb in (21, 63, 126, 252):
        cum = resid.rolling(lb).sum()
        sd = resid.rolling(lb).std()
        # Standardising by residual vol is the Blitz-Huij-Martens step; without
        # it the measure is dominated by whichever names are simply volatile.
        f[f"residmom{lb}"] = cum / sd

    # Residual 12-1, skipping the last month to avoid short-term reversal.
    f["residmom12_1"] = (resid.shift(21).rolling(231).sum() /
                         resid.shift(21).rolling(231).std())

    # --- plain (total) momentum, to prove residual is doing something extra -
    for lb in (21, 63, 126, 252):
        f[f"mom{lb}"] = pch(close, lb)
    f["mom12_1"] = pch(close.shift(21), 231)

    # --- reversal ---------------------------------------------------------
    f["rev5"] = -pch(close, 5)
    f["rev21"] = -pch(close, 21)
    f["residrev5"] = -resid.rolling(5).sum()

    # --- trend / location -------------------------------------------------
    for w in (50, 200):
        f[f"sma{w}_dist"] = close / close.rolling(w).mean() - 1.0
    f["hi52"] = close / close.rolling(252).max()

    # --- oscillators ------------------------------------------------------
    d = close.diff()
    for n, key in ((14, "rsi14"), (2, "rsi2")):
        up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
        f[key] = 100 - 100 / (1 + up / dn.replace(0, np.nan))

    # --- volatility state -------------------------------------------------
    rv21 = r.rolling(21).std()
    rv63 = r.rolling(63).std()
    f["vol_ratio"] = rv21 / rv63          # is vol expanding or contracting?
    f["idiovol"] = resid.rolling(63).std()
    f["rv21"] = rv21

    # --- volume -----------------------------------------------------------
    vz = (vol - vol.rolling(63).mean()) / vol.rolling(63).std()
    f["volsurge"] = vz

    # --- market-relationship descriptors (conditioners, not predictors) ----
    f["beta"] = beta
    f["r2mkt"] = r2

    return {k: v.shift(1) for k, v in f.items()}, beta.shift(0), r2.shift(0)


def fwd_returns(open_, h):
    """Forward h-day return entered at the NEXT open after the signal.

    Signal is known at close t -> we buy at open t+1 -> we exit at open t+1+h.
    Entering at the same close the signal was computed from is the single most
    common way a stock backtest overstates itself.
    """
    entry = open_.shift(-1)
    exit_ = open_.shift(-1 - h)
    return exit_ / entry - 1.0


def decile_spread(sig, fwd, mask=None, n_bins=5):
    """Cross-sectional test: sort into quintiles each day, measure top vs bottom.

    Returns (per-day top return, per-day bottom return, per-day spread).
    Immune to common market drift -- which is the point, given the universe's
    survivorship bias.
    """
    s = sig.copy()
    fw = fwd.copy()
    if mask is not None:
        m = mask.reindex(s.index).fillna(False)
        s = s[m]
        fw = fw[m]

    ranks = s.rank(axis=1, pct=True)
    valid = s.notna() & fw.notna()
    ranks = ranks.where(valid)

    top = fw.where(ranks >= 1 - 1.0 / n_bins).mean(axis=1)
    bot = fw.where(ranks <= 1.0 / n_bins).mean(axis=1)
    return top, bot, top - bot


def summarize(x, label, cost=COST_BPS):
    x = pd.Series(x).dropna()
    if len(x) < 30:
        return None
    net = x - 2 * cost / 1e4
    t = net.mean() / (net.std() / np.sqrt(len(net))) if net.std() > 0 else 0.0
    return {
        "label": label,
        "n": len(net),
        "win": (net > 0).mean(),
        "avg": net.mean(),
        "t": t,
        "std": net.std(),
    }


def main():
    close, open_, vol, mkt, sw = load()
    print("=" * 84)
    print("STOCK DIRECTION -- market-conditioned, 5-10 day swing")
    print("=" * 84)
    print(f"  {close.shape[1]} tickers, {close.index[0].date()} -> {close.index[-1].date()}")

    beta, r2, resid, r, rm = beta_decompose(close, mkt)
    feats, beta_raw, r2_raw = build_stock_features(close, vol, beta, r2, resid, r, rm)
    print(f"  {len(feats)} stock-level signals built")

    # How market-driven is the universe? This is the owner's question, answered.
    med_r2 = r2.median(axis=1).dropna()
    med_beta = beta.median(axis=1).dropna()
    print(f"\n  HOW MUCH DO THESE STOCKS 'COPY THE MARKET'?")
    print(f"    median R^2 to SPY: {med_r2.mean():.2f}  "
          f"(i.e. ~{med_r2.mean()*100:.0f}% of the typical stock's daily variance IS the market)")
    print(f"    median beta:       {med_beta.mean():.2f}")

    last_r2 = r2.iloc[-1].dropna().sort_values()
    last_b = beta.iloc[-1].dropna()
    print(f"\n    MOST market-driven right now (highest R^2 -> a market call in disguise):")
    for tk in last_r2.tail(8).index[::-1]:
        print(f"      {tk:6s} R2={last_r2[tk]:.2f}  beta={last_b.get(tk, np.nan):.2f}")
    print(f"    LEAST market-driven (lowest R^2 -> genuinely stock-specific):")
    for tk in last_r2.head(8).index:
        print(f"      {tk:6s} R2={last_r2[tk]:.2f}  beta={last_b.get(tk, np.nan):.2f}")

    # ------------------------------------------------------------------
    # Cross-sectional signal test, per horizon, per split.
    # ------------------------------------------------------------------
    rows = []
    for h in HORIZONS:
        fwd = fwd_returns(open_, h)
        for name, sig in feats.items():
            rec = {"signal": name, "horizon": h}
            ok = True
            for split in SPLITS:
                sl = slice_dates(close.index, split)
                # Sample every h days so trades do not overlap.
                idx = close.index[sl][::h]
                s_ = sig.loc[idx]
                f_ = fwd.loc[idx]
                top, bot, spr = decile_spread(s_, f_)
                st = summarize(spr, name)
                tp = summarize(top, name)
                if st is None or tp is None:
                    ok = False
                    break
                rec[f"{split}_spread"] = st["avg"]
                rec[f"{split}_spread_t"] = st["t"]
                rec[f"{split}_top_win"] = tp["win"]
                rec[f"{split}_top_avg"] = tp["avg"]
                rec[f"{split}_n"] = st["n"]
            if ok:
                rows.append(rec)

    res = pd.DataFrame(rows)
    res.to_parquet(os.path.join(OUT, "stock_signals.parquet"), index=False)

    n_trials = len(res)
    print(f"\n{'='*84}")
    print(f"CROSS-SECTIONAL SIGNAL TEST  ({n_trials} signal x horizon combinations)")
    print("=" * 84)
    print("  'spread' = top-quintile minus bottom-quintile forward return, net of cost.")
    print("  This is the clean measure -- market drift and survivorship cancel out.\n")

    res = res.sort_values("train_spread_t", ascending=False)
    print(f"  {'signal':14s} {'h':>3s} {'TRAIN sp':>9s} {'t':>6s} "
          f"{'VALID sp':>9s} {'t':>6s} {'TEST sp':>9s} {'t':>6s}")
    for _, x in res.head(20).iterrows():
        print(f"  {x['signal']:14s} {int(x['horizon']):3d} "
              f"{x['train_spread']:+9.2%} {x['train_spread_t']:+6.2f} "
              f"{x['validate_spread']:+9.2%} {x['validate_spread_t']:+6.2f} "
              f"{x['test_spread']:+9.2%} {x['test_spread_t']:+6.2f}")

    surv = res[(res.train_spread_t > 1.5) & (res.validate_spread_t > 1.5) &
               (res.test_spread_t > 0)]
    print(f"\n  SURVIVORS (t>1.5 on train AND validate, still positive on test): "
          f"{len(surv)} of {n_trials}")
    for _, x in surv.iterrows():
        print(f"    {x['signal']:14s} h={int(x['horizon']):2d}  "
              f"spread {x['train_spread']:+.2%}/{x['validate_spread']:+.2%}/{x['test_spread']:+.2%}  "
              f"top-quintile win {x['test_top_win']:.1%}")

    print(f"\n  Multiple-testing bar: {n_trials} trials -> "
          f"expected best |t| under the null ~ {np.sqrt(2*np.log(max(n_trials,2))):.2f}")


if __name__ == "__main__":
    main()
