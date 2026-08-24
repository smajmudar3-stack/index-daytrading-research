"""Swing-horizon edge lab: cross-sectional sector rotation + regime timing.

The point of this file is NOT to find a big number. It is to make a big number
that is fake HARD TO PRODUCE. Four disciplines are enforced structurally, each
because it manufactured a fake edge in this repo before (see FINDINGS.md):

  1. Every normalisation is past-only: expanding().mean().shift(1). A
     whole-sample transform once produced t=+15.6 out of pure leakage.
  2. Signals are known at close t, positions taken at the OPEN of t+1. No
     signal can peek at the bar it trades on.
  3. Three-way split (train / validate / test). Two-way was not enough after
     heavy searching -- a 61.5% rule collapsed when a third split was added.
  4. Every result is scored against the number of trials that produced it
     (deflated Sharpe). Search 5,000 combinations and the best one looks
     wonderful by construction; the correction says how wonderful it should
     have looked by luck alone.

Costs are charged on turnover, not waved away.
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

from idt import paths

PANEL = paths.data("swing", "panel.parquet")

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]

# Round-trip cost on a liquid ETF, in basis points of notional. 5bps is already
# generous for SPY/XLK at retail size; it is charged on every unit of turnover.
COST_BPS = 5.0

# Three-way split. Deliberately chosen so each window contains at least one
# regime change -- train has 2000 and 2008, validate has 2015/2018, test has
# 2020 and 2022. A split where one window is all bull market proves nothing.
SPLITS = {
    "train": ("1998-01-01", "2011-12-31"),
    "validate": ("2012-01-01", "2019-12-31"),
    "test": ("2020-01-01", "2026-12-31"),
}

TRADING_DAYS = 252


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load():
    p = pd.read_parquet(paths.require_data(PANEL))
    close = p.pivot(index="date", columns="ticker", values="close").sort_index()
    open_ = p.pivot(index="date", columns="ticker", values="open").sort_index()
    return close, open_


def pch(x, n=1):
    """pct_change without pad-filling. The default fill_method carries a price
    across a ticker's pre-inception NaNs and fabricates a return; XLRE (2015)
    and XLC (2018) would otherwise show 17 years of phantom history."""
    return x.pct_change(n, fill_method=None)


def zscore_past(s, win=252, minp=126):
    """Past-only z-score. The .shift(1) is the whole point -- without it the
    current observation contributes to its own mean and the result leaks."""
    m = s.rolling(win, min_periods=minp).mean().shift(1)
    v = s.rolling(win, min_periods=minp).std().shift(1)
    return (s - m) / v


def pct_rank_past(s, win=252, minp=126):
    """Where does today sit in its own trailing distribution, excluding today."""
    return s.rolling(win, min_periods=minp).apply(
        lambda w: (w[:-1] < w[-1]).mean(), raw=True
    )


# --------------------------------------------------------------------------
# performance stats
# --------------------------------------------------------------------------
def stats_of(rets, freq=TRADING_DAYS):
    """Daily return series -> the numbers that matter, plus a t-stat."""
    r = pd.Series(rets).dropna()
    if len(r) < 30 or r.std() == 0:
        return None
    ann_ret = (1 + r).prod() ** (freq / len(r)) - 1
    ann_vol = r.std() * np.sqrt(freq)
    sharpe = (r.mean() / r.std()) * np.sqrt(freq)
    t = r.mean() / (r.std() / np.sqrt(len(r)))
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return {
        "n": len(r),
        "cagr": ann_ret,
        "vol": ann_vol,
        "sharpe": sharpe,
        "t": t,
        "maxdd": dd,
        "skew": r.skew(),
        "hit": (r > 0).mean(),
    }


def trade_stats(trade_rets):
    """Per-TRADE stats. Win rate here is the number the owner actually cares
    about -- daily hit rate is not the same thing and must not be quoted as it."""
    r = pd.Series(trade_rets).dropna()
    if len(r) < 10:
        return None
    wins = r > 0
    return {
        "trades": len(r),
        "win": wins.mean(),
        "avg": r.mean(),
        "avg_win": r[wins].mean() if wins.any() else 0.0,
        "avg_loss": r[~wins].mean() if (~wins).any() else 0.0,
        "t": r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0.0,
        "best": r.max(),
        "worst": r.min(),
    }


def deflated_sharpe(sharpe, n_obs, n_trials, skew=0.0, kurt=3.0):
    """Bailey & Lopez de Prado. Probability the observed Sharpe would NOT have
    arisen from searching `n_trials` strategies with no real edge.

    This is the antidote to 'test every single combination'. The expected
    maximum Sharpe under the null grows like sqrt(2*ln(N)) -- with 5,000 trials
    a Sharpe near 0.8 is the EXPECTED best result from pure noise.
    """
    if n_trials < 2 or n_obs < 30:
        return np.nan, np.nan
    euler = 0.5772156649
    # Expected max of N standard normals.
    e_max = (1 - euler) * stats.norm.ppf(1 - 1.0 / n_trials) + euler * stats.norm.ppf(
        1 - 1.0 / (n_trials * np.e)
    )
    # Variance of the Sharpe estimator across trials -> the benchmark to beat.
    sr_std = 1.0 / np.sqrt(n_obs - 1)
    sr0 = sr_std * e_max
    denom = np.sqrt(1 - skew * sharpe + (kurt - 1) / 4.0 * sharpe**2)
    if denom <= 0:
        return np.nan, sr0
    z = (sharpe - sr0) * np.sqrt(n_obs - 1) / denom
    return stats.norm.cdf(z), sr0


def slice_dates(idx, split):
    a, b = SPLITS[split]
    return (idx >= a) & (idx <= b)


# --------------------------------------------------------------------------
# feature library -- everything past-only by construction
# --------------------------------------------------------------------------
def build_features(close, open_):
    """Return a dict of DataFrames (date x ticker) of candidate ranking signals."""
    f = {}
    ret1 = pch(close)

    for lb in (21, 63, 126, 252):
        f[f"mom{lb}"] = pch(close, lb)

    # 12-1 momentum: skip the most recent month to dodge short-term reversal.
    # This is the classic academic specification and differs materially from
    # raw 12-month momentum.
    f["mom12_1"] = pch(close.shift(21), 231)
    f["mom6_1"] = pch(close.shift(21), 105)

    # Acceleration -- is medium-term momentum improving on long-term?
    f["accel"] = f["mom63"] - f["mom126"]

    for lb in (21, 63):
        f[f"vol{lb}"] = ret1.rolling(lb).std()
        # Risk-adjusted momentum: return per unit of its own volatility.
        f[f"sharpe{lb}"] = pch(close, lb) / (ret1.rolling(lb).std() * np.sqrt(lb))

    for w in (50, 200):
        f[f"sma{w}_dist"] = close / close.rolling(w).mean() - 1.0

    # Proximity to the 52-week high -- the George-Hwang anchor.
    f["hi52"] = close / close.rolling(252).max()
    f["lo52"] = close / close.rolling(252).min()

    # RSI(14), Wilder.
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    f["rsi14"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))

    # Short-term reversal -- the counterweight to momentum at this horizon.
    f["rev5"] = -pch(close, 5)
    f["rev21"] = -pch(close, 21)

    # Relative strength vs the market. Sector rotation is fundamentally a
    # relative game, so express it explicitly rather than hoping raw momentum
    # captures it.
    if "SPY" in close.columns:
        spy = close["SPY"]
        for lb in (21, 63, 126):
            f[f"rs{lb}"] = pch(close, lb).sub(pch(spy, lb), axis=0)

    # Everything is shifted one day: a signal computed from the close of t is
    # only available to trade at t+1.
    return {k: v.shift(1) for k, v in f.items()}


def build_regime(close):
    """Market-wide regime signals -> a DataFrame of boolean/continuous columns.

    These are the bull/bear and rotation-context filters. All past-only.
    """
    r = pd.DataFrame(index=close.index)
    spy = close["SPY"]

    r["spy_above_200"] = (spy > spy.rolling(200).mean()).astype(float)
    r["spy_above_50"] = (spy > spy.rolling(50).mean()).astype(float)
    r["spy_50_above_200"] = (spy.rolling(50).mean() > spy.rolling(200).mean()).astype(float)

    # Breadth: how many sectors are in their own uptrend. A far better bear
    # detector than the index alone, because the index is cap-weighted.
    have = [s for s in SECTORS if s in close.columns]
    above = pd.DataFrame(
        {s: (close[s] > close[s].rolling(200).mean()).astype(float) for s in have}
    )
    r["breadth"] = above.mean(axis=1)

    if "^VIX" in close.columns:
        vix = close["^VIX"]
        r["vix"] = vix
        r["vix_z"] = zscore_past(vix)
        r["vix_low"] = (vix < 20).astype(float)
    if "^VIX3M" in close.columns and "^VIX" in close.columns:
        # Contango (VIX < VIX3M) is the calm/risk-on state; backwardation is
        # the stress state. The single most-cited swing regime signal.
        ts = close["^VIX"] / close["^VIX3M"]
        r["vix_ts"] = ts
        r["contango"] = (ts < 1.0).astype(float)
    if "^SKEW" in close.columns:
        r["skew_z"] = zscore_past(close["^SKEW"])

    # Credit: HYG vs a duration-matched Treasury. Credit leads equity at the
    # weeks-to-months horizon far more reliably than anything intraday.
    if "HYG" in close.columns and "IEF" in close.columns:
        cr = close["HYG"] / close["IEF"]
        r["credit_mom"] = pch(cr, 63)
        r["credit_up"] = (cr > cr.rolling(63).mean()).astype(float)

    # Defensive vs cyclical leadership -- the rotation state itself.
    if "XLP" in close.columns and "XLY" in close.columns:
        dc = close["XLY"] / close["XLP"]
        r["cyc_lead"] = pch(dc, 63)
        r["cyc_up"] = (dc > dc.rolling(63).mean()).astype(float)

    # Duration bid = risk-off.
    if "TLT" in close.columns:
        r["tlt_mom"] = pch(close["TLT"], 63)

    if "^GSPC" in close.columns:
        g = close["^GSPC"]
        r["dd_from_high"] = g / g.cummax() - 1.0  # cummax is past-only by definition

    return r.shift(1)


# --------------------------------------------------------------------------
# track A -- cross-sectional sector rotation
# --------------------------------------------------------------------------
def rotation_backtest(close, open_, sig, k, hold, regime_mask=None, cost_bps=COST_BPS,
                      long_only=True, short_k=0):
    """Rank sectors by `sig`, hold the top k, rebalance every `hold` days.

    Returns (daily_returns, per_trade_returns). Positions are formed on the
    signal available at t and entered at the OPEN of t+1; returns accrue
    open-to-open so the entry price is never the one the signal was computed on.
    """
    have = [s for s in SECTORS if s in close.columns and s in sig.columns]
    px = open_[have]
    sg = sig[have]

    # Rebalance dates: every `hold` trading days.
    reb = px.index[::hold]

    # Ranks at each rebalance. min_count guards the ragged XLRE/XLC starts.
    weights = pd.DataFrame(0.0, index=px.index, columns=have)
    trades = []

    for i, dt in enumerate(reb):
        row = sg.loc[dt].dropna()
        if len(row) < 5:
            continue
        if regime_mask is not None:
            m = regime_mask.get(dt, np.nan)
            if not (m == m) or m <= 0:  # NaN or False -> flat
                continue

        top = row.nlargest(k).index.tolist()
        bot = row.nsmallest(short_k).index.tolist() if short_k else []

        end = reb[i + 1] if i + 1 < len(reb) else px.index[-1]
        seg = px.loc[dt:end]
        if len(seg) < 2:
            continue

        w = 1.0 / max(len(top), 1)
        weights.loc[dt:end, top] = w
        if bot:
            wb = -1.0 / len(bot)
            weights.loc[dt:end, bot] = wb

        # Per-trade return = the actual held leg, open-to-open, net of a
        # round-trip cost. This is the number the owner reads as "win rate".
        for tk in top:
            seg_tk = seg[tk].dropna()
            if len(seg_tk) < 2:
                continue
            gross = seg_tk.iloc[-1] / seg_tk.iloc[0] - 1
            trades.append(gross - 2 * cost_bps / 1e4)
        for tk in bot:
            seg_tk = seg[tk].dropna()
            if len(seg_tk) < 2:
                continue
            gross = -(seg_tk.iloc[-1] / seg_tk.iloc[0] - 1)
            trades.append(gross - 2 * cost_bps / 1e4)

    # Daily portfolio return from open-to-open moves.
    oret = pch(px).shift(-0)  # open_t -> open_{t+1} accrues on t+1
    port = (weights.shift(1) * oret).sum(axis=1)

    # Charge cost on turnover.
    turn = (weights - weights.shift(1)).abs().sum(axis=1)
    port = port - turn * cost_bps / 1e4

    return port, trades


# --------------------------------------------------------------------------
# track B -- regime timing on a single instrument
# --------------------------------------------------------------------------
def timing_backtest(close, cond, symbol, horizon, cost_bps=COST_BPS):
    """When `cond` is true at close t, hold `symbol` for `horizon` days from t+1.

    Non-overlapping trades only -- overlapping windows inflate the t-stat by
    reusing the same days, which is the most common way a timing study lies.
    """
    px = close[symbol]
    fwd = px.shift(-horizon) / px - 1.0

    c = cond.reindex(px.index).fillna(0).astype(bool)
    idx = np.flatnonzero(c.values)

    # Enforce non-overlap: once a trade opens, skip signals until it closes.
    picked, last = [], -10**9
    for i in idx:
        if i - last >= horizon:
            picked.append(i)
            last = i

    r = fwd.iloc[picked].dropna() - 2 * cost_bps / 1e4
    # Base rate: the same holding period taken unconditionally. An edge must
    # beat THIS, not zero -- equities drift up, so any long signal wins often.
    base = fwd.iloc[::horizon].dropna() - 2 * cost_bps / 1e4
    return r, base


def main():
    close, open_ = load()
    feats = build_features(close, open_)
    regime = build_regime(close)

    print("=" * 78)
    print("SWING LAB -- data loaded")
    print("=" * 78)
    print(f"  {close.index[0].date()} -> {close.index[-1].date()}, {len(close)} sessions")
    print(f"  features: {len(feats)}  regime cols: {len(regime.columns)}")
    for name, (a, b) in SPLITS.items():
        n = slice_dates(close.index, name).sum()
        print(f"  {name:9s} {a[:7]} -> {b[:7]}  {n:5d} sessions")
    print()

    # Benchmark to beat, per split.
    print("BENCHMARK  buy & hold SPY")
    spy_ret = pch(close["SPY"])
    for name in SPLITS:
        m = slice_dates(close.index, name)
        s = stats_of(spy_ret[m])
        print(
            f"  {name:9s} CAGR {s['cagr']:+7.2%}  Sharpe {s['sharpe']:+5.2f}  maxDD {s['maxdd']:+7.1%}"
        )
    print()


if __name__ == "__main__":
    main()
