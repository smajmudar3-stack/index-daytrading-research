"""engine_combo_test.py — the whole paper engine as ONE portfolio, 2019-2026: the index at
1x, 2x while VIX is backwardated inside a golden cross, with a slice of the equity in the
earnings-surprise stock sleeve instead of the index. What does the combination compound
to, and does the sleeve add anything on top of the overlay?

Pieces already measured separately:
  * overlay: 15.3%/yr vs 11.5% buy-and-hold, 2006-2026 (goal_feasibility.md)
  * earnings-surprise top decile, monthly, long-only: 17.8%/yr vs SPY 14.5%, 2020-2026,
    +4.7%/yr excess at t 0.9 (fundamentals.md §3)
This joins them on the common window (2020-01 -> 2026-06, the sleeve's data), monthly:
  * sleeve weight w in {0, 0.25, 0.5}: that share of equity holds the top-decile surprise
    portfolio (from xsec_portfolio_test's month panel, 15 bp/side on turnover), the rest
    holds SPY; the OVERLAY multiplies the whole book's exposure by 2 in months the signal
    was on at the prior month-end (6% borrow on the levered share)
  * reported: CAGR, max drawdown, worst month, Sharpe, $5,000 -> $, years to $50,000 at
    that CAGR, and the same for SPY, for the overlay alone, and for the sleeve alone.
Monthly granularity understates the overlay (its rule is daily), so the overlay row here
is a lower bound on what the daily version did in the same window.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_portfolio_test import COST, month_panel  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
BORROW = 0.06


def sleeve_returns(m):
    """Monthly return of the top-decile earnings-surprise sleeve, net of turnover cost."""
    d = m[m.sue.notna() & m.fwd21.notna()].copy()
    d["r"] = d.groupby("date").sue.rank(pct=True)
    d["pick"] = d.r >= 0.9
    rows, prev = [], set()
    for dt, g in d.groupby("date"):
        held = set(g[g.pick].act_symbol)
        if len(held) < 20:
            continue
        turn = len(held ^ prev) / max(1, len(held))
        rows.append({"date": dt, "sleeve": g[g.pick].fwd21.mean() - COST * turn, "spy": g.fwd21_spy.iloc[0]})
        prev = held
    return pd.DataFrame(rows).set_index("date")


def overlay_signal(dates):
    import yfinance as yf
    px = yf.download(["^VIX", "^VIX3M", "SPY"], start="2018-01-01", progress=False, auto_adjust=True)["Close"].dropna()
    px["golden"] = px["SPY"].rolling(50).mean() > px["SPY"].rolling(200).mean()
    px["on"] = px["golden"] & (px["^VIX"] / px["^VIX3M"] > 1.0)
    # the signal as it stood at each month-end (the decision for the next month)
    return px["on"].reindex(dates, method="ffill").astype(bool)


def stats(r):
    eq = (1 + r).cumprod(); yrs = len(r) / 12
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    return {"CAGR": cagr, "max DD": (eq / eq.cummax() - 1).min(), "worst month": r.min(),
            "Sharpe": r.mean() / r.std() * np.sqrt(12), "$5k ->": 5000 * eq.iloc[-1],
            "years to 10x": np.log(10) / np.log(1 + cagr) if cagr > 0 else np.inf}


def main():
    pd.set_option("display.width", 200)
    m = month_panel()
    s = sleeve_returns(m)
    on = overlay_signal(s.index)
    rows = {}
    for w in (0.0, 0.25, 0.5, 1.0):
        base = w * s.sleeve + (1 - w) * s.spy
        for lev_label, lev in (("1x", pd.Series(1.0, index=s.index)),
                               ("overlay (2x when on)", 1.0 + on.astype(float))):
            r = lev * base - (lev - 1).clip(lower=0) * BORROW / 12
            rows[f"sleeve {int(w*100)}% · {lev_label}"] = stats(r)
    t = pd.DataFrame(rows).T
    print(f"{len(s)} months {s.index.min().date()} .. {s.index.max().date()}; signal on in {int(on.sum())} month-ends")
    print(t.to_string(float_format=lambda v: f"{v:10.3f}"))
    ex = (s.sleeve - s.spy)
    print(f"\nsleeve minus SPY: {ex.mean()*12*100:+.1f}%/yr, t={ex.mean()/ex.std()*np.sqrt(len(ex)):+.2f}; "
          f"correlation of sleeve excess with the signal being on: {np.corrcoef(ex, on.astype(float))[0,1]:+.2f}")
    # what the target needs
    print("\nthe target: $5,000 -> $50,000 in 5 months = 10x = 58.5%/month; in 3 years = 115%/yr; in 5 years = 58.5%/yr")


if __name__ == "__main__":
    main()
