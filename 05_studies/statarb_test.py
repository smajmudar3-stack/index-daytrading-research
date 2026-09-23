"""statarb_test.py — the hedge-fund quant trade, measured: statistical arbitrage on
residual mean reversion (Avellaneda & Lee 2010, "Statistical arbitrage in the US equities
market"), on 1,500 names, 2019-2026, with costs.

WHAT A STAT-ARB DESK ACTUALLY DOES. Not predict a stock. Strip the market and sector out
of each name's daily returns, and bet that what is LEFT -- the idiosyncratic residual --
mean-reverts over a few days. Long the names whose residual has fallen furthest below its
own mean, short the ones furthest above, dollar-neutral, hundreds of positions, held a few
days, rebalanced daily. The edge per name is tiny; the book is the edge. This is the
canonical quant equity strategy of the 2000s, and Avellaneda & Lee themselves report its
Sharpe fell from ~1.4 (1997-2002) to ~0.9 (2003-2007) as it was crowded.

Construction, past-only at every step:
  * factors: the 11 sector ETFs plus SPY, daily returns
  * each day, each name: regress the trailing 60 days of its returns on the factors;
    the residual series is fitted to an OU process (AR(1) on the cumulative residual);
    the s-score is (current cumulative residual - its mean) / its std over the window
  * signal at close t: s-score. Long the bottom decile (most oversold residual), short
    the top decile, equal weight, enter at the NEXT open, hold H in {1, 3, 5} sessions
  * universe: close >= $10, 20-day median dollar volume >= $10m (the option panel's)
  * costs: 5 bp per side per rebalance on the turnover actually incurred (liquid names,
    but daily turnover is what kills this strategy and it is charged honestly)
Reported per split: annualised long-short return, Sharpe, worst month, and the same gross
of costs so the reader can see exactly what the cost line takes.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS, adjust_splits  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
SECTORS = ["SPY", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]
WIN = 60
COST = 0.0005


def load():
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"))
    px["act_symbol"] = px.act_symbol.astype(str)
    fe = pd.read_parquet(os.path.join(PANEL, "features.parquet"), columns=["act_symbol"])
    names = set(fe.act_symbol.astype(str)) | set(SECTORS)
    px = adjust_splits(px[px.act_symbol.isin(names)])
    close = px.pivot(index="date", columns="act_symbol", values="close").sort_index()
    open_ = px.pivot(index="date", columns="act_symbol", values="open").sort_index()
    vol = px.pivot(index="date", columns="act_symbol", values="volume").sort_index()
    return close, open_, vol


def s_scores(ret, fac):
    """Rolling 60-day factor regression residuals -> OU s-score, vectorised per day."""
    out = pd.DataFrame(index=ret.index, columns=ret.columns, dtype=float)
    X_all = fac.values
    dates = ret.index
    for i in range(WIN, len(dates)):
        X = X_all[i - WIN:i]
        X = np.column_stack([np.ones(WIN), X])
        Y = ret.values[i - WIN:i]
        ok = ~np.isnan(Y).any(axis=0) & ~np.isnan(X).any(axis=1).any()
        if not ok.any():
            continue
        Yk = Y[:, ok]
        beta, *_ = np.linalg.lstsq(X, Yk, rcond=None)
        resid = Yk - X @ beta
        cum = np.cumsum(resid, axis=0)
        # AR(1) on the cumulative residual: X_{t+1} = a + b X_t + e
        x0, x1 = cum[:-1], cum[1:]
        mx0, mx1 = x0.mean(0), x1.mean(0)
        b = ((x0 - mx0) * (x1 - mx1)).sum(0) / (((x0 - mx0) ** 2).sum(0) + 1e-12)
        a = mx1 - b * mx0
        e = x1 - (a + b * x0)
        good = (b > 0) & (b < 0.97)                       # mean-reverting inside the window
        mu = a / (1 - b + 1e-12)
        sig_eq = np.sqrt(e.var(0) / (1 - b ** 2 + 1e-12))
        s = (cum[-1] - mu) / (sig_eq + 1e-12)
        s[~good] = np.nan
        out.iloc[i, np.where(ok)[0]] = s
    return out


def backtest(s, open_, close, vol, hold, top=0.10):
    """Long bottom decile, short top decile of s at close t; enter next open; hold `hold` days."""
    ret_oc = close.shift(-hold) / open_.shift(-1) - 1                 # next open -> close t+hold
    dv20 = (close * vol).rolling(20, min_periods=10).median()
    elig = (close >= 10) & (dv20 >= 10e6)
    rows, prev_long, prev_short = [], set(), set()
    for i, d in enumerate(s.index):
        if i % hold:                                                    # non-overlapping cohorts
            continue
        row = s.loc[d].where(elig.loc[d]).dropna()
        if len(row) < 200:
            continue
        lo, hi = row.quantile(top), row.quantile(1 - top)
        longs, shorts = set(row[row <= lo].index), set(row[row >= hi].index)
        r = ret_oc.loc[d]
        rl, rs = r.reindex(list(longs)).mean(), r.reindex(list(shorts)).mean()
        if np.isnan(rl) or np.isnan(rs):
            continue
        turn = (len(longs ^ prev_long) / max(1, len(longs)) + len(shorts ^ prev_short) / max(1, len(shorts))) / 2
        rows.append({"date": d, "long": rl, "short": rs, "gross": (rl - rs) / 2, "net": (rl - rs) / 2 - COST * turn,
                     "n": len(longs) + len(shorts), "turnover": turn})
        prev_long, prev_short = longs, shorts
    return pd.DataFrame(rows).set_index("date")


def report(bt, hold):
    per_year = 252 / hold
    for lab, col in (("gross", "gross"), ("net of 5bp/side", "net")):
        r = bt[col]
        line = f"  H={hold}d {lab:16s}: {r.mean()*per_year*100:+6.1f}%/yr  Sharpe {r.mean()/r.std()*np.sqrt(per_year):+5.2f}  " \
               f"hit {(r>0).mean()*100:.0f}%  worst {r.min()*100:+.1f}%  n={len(r)}"
        for k, (a, b) in SPLITS.items():
            sub = r[(r.index >= a) & (r.index <= b)]
            if len(sub) > 20:
                line += f" | {k[:1]} {sub.mean()*per_year*100:+.1f}% (S{sub.mean()/sub.std()*np.sqrt(per_year):+.1f})"
        print(line)


def main():
    close, open_, vol = load()
    ret = close.pct_change(fill_method=None)
    fac = ret[SECTORS].dropna(how="all")
    names = [c for c in ret.columns if c not in SECTORS]
    ret = ret.loc[fac.index, names]
    fac = fac.fillna(0)
    print(f"{len(names)} names, {len(ret)} sessions {ret.index.min().date()} .. {ret.index.max().date()}; computing s-scores…", flush=True)
    s = s_scores(ret, fac)
    print(f"s-scores: {s.notna().sum().sum():,} name-days; mean |s| {s.abs().stack().mean():.2f}")
    for hold in (1, 3, 5):
        bt = backtest(s, open_[names], close[names], vol[names], hold)
        print(f"\nlong-short deciles on the OU s-score, ~{bt.n.mean():.0f} positions, turnover {bt.turnover.mean()*100:.0f}% per rebalance")
        report(bt, hold)
    s.to_parquet(os.path.join(PANEL, "statarb_sscores.parquet"))


if __name__ == "__main__":
    main()
