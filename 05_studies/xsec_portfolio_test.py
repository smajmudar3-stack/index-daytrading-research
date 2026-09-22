"""xsec_portfolio_test.py — what the measured slow factors compound to, as a real portfolio.

Everything in this session that survived is a one-to-three-month STOCK effect: earnings
surprise drift (+2.84% Q5-Q1 at 63d, t 4.3), capital return (buyback / FCF yield / net
issuance), and possibly momentum at the monthly horizon it was published on (the weekly
test could not see it). None of it is an options edge. So the only honest question left
for "$5,000 to $50,000, any horizon, any stock" is: hold the best decile of a composite of
those, rebalanced monthly, and what does it return against SPY, at 1x and at 2x?

Rules, each because its absence faked a result here before:
  * ranks formed at month-end t on data available at t (statements lagged 60 days, the
    surprise from the last announcement before t); held from the next open to the next
    month-end close. No overlap.
  * universe at t: close >= $10, 20-day median dollar volume >= $10m (tradeable at size).
  * equal weight, top decile long. Costs charged: 15 bp per side on the turnover actually
    incurred (names entering or leaving the decile), which is generous for liquid names.
  * three splits reported, and the 2x row is the SAME return series levered with a 6%
    borrow rate, not a fitted one.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_fundamentals_test import fundamentals, prices  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
COST = 0.0015
BORROW = 0.06


def month_panel():
    px = prices()
    m = fundamentals(px)                         # month-ends, statements lagged, ex21 attached
    # last surprise before t
    e = pd.read_parquet(os.path.join(PANEL, "sue_events.parquet"))[["act_symbol", "sig", "sue"]]
    e = e.dropna().sort_values("sig")
    m = m.sort_values("date")
    m = pd.merge_asof(m, e.rename(columns={"sig": "date"}), on="date", by="act_symbol",
                      direction="backward", tolerance=pd.Timedelta(days=95))
    # momentum at the monthly horizon, computed from the same adjusted closes
    g = px.sort_values(["act_symbol", "date"]).groupby("act_symbol", group_keys=False)
    px["mom_12_1"] = g.close.shift(21) / g.close.shift(252) - 1
    px["mom_6_1"] = g.close.shift(21) / g.close.shift(126) - 1
    px["rv63"] = g.close.pct_change(fill_method=None).transform(lambda s: s.rolling(63, min_periods=40).std())
    m = m.merge(px[["date", "act_symbol", "mom_12_1", "mom_6_1", "rv63"]], on=["date", "act_symbol"], how="left")
    return m


FACTORS = {"sue": +1, "buyback_yield": +1, "fcf_yield": +1, "d_shares_yoy": -1, "mom_12_1": +1}


def portfolio(m, factors, label, top=0.10):
    d = m.copy()
    cols = []
    for f, s in factors.items():
        d[f"r_{f}"] = d.groupby("date")[f].rank(pct=True).sub(0.5).mul(2 * s)
        cols.append(f"r_{f}")
    d["comp"] = d[cols].mean(axis=1, skipna=True)
    d["n_f"] = d[cols].notna().sum(axis=1)
    d = d[(d.n_f >= max(1, len(cols) - 2)) & d.fwd21.notna()]
    d["pick"] = d.groupby("date").comp.rank(pct=True) >= 1 - top
    rows, prev = [], set()
    for dt, g in d.groupby("date"):
        held = set(g[g.pick].act_symbol)
        if len(held) < 20:
            continue
        turn = len(held ^ prev) / max(1, len(held))
        r = g[g.pick].fwd21.mean() - COST * turn
        rows.append({"date": dt, "ret": r, "spy": g.fwd21_spy.iloc[0], "n": len(held), "turnover": turn})
        prev = held
    s = pd.DataFrame(rows).set_index("date")
    return s


def summarise(s, label):
    out = {}
    for name, r in (("portfolio 1x", s.ret), ("SPY", s.spy),
                    ("portfolio 2x", 2 * s.ret - (BORROW / 12)), ("SPY 2x", 2 * s.spy - (BORROW / 12))):
        eq = (1 + r).cumprod()
        yrs = len(r) / 12
        cagr = eq.iloc[-1] ** (1 / yrs) - 1
        dd = (eq / eq.cummax() - 1).min()
        out[name] = {"CAGR": cagr, "max DD": dd, "months>0": (r > 0).mean(),
                     "$5k ->": 5000 * eq.iloc[-1], "sharpe": r.mean() / r.std() * np.sqrt(12)}
    t = pd.DataFrame(out).T
    ex = s.ret - s.spy
    print(f"\n=== {label}: {len(s)} months {s.index.min().date()} .. {s.index.max().date()}, "
          f"~{s.n.mean():.0f} names, turnover {s.turnover.mean()*100:.0f}%/month ===")
    print(t.to_string(float_format=lambda v: f"{v:10.3f}"))
    print(f"  excess over SPY: {ex.mean()*12*100:+.1f}%/yr, t={ex.mean()/ex.std()*np.sqrt(len(ex)):+.2f}, "
          f"months beating SPY {(ex>0).mean()*100:.0f}%")
    for k, (a, b) in {"A 2020-21": ("2020-01-01", "2021-12-31"), "B 2022-23": ("2022-01-01", "2023-12-31"),
                      "C 2024-26": ("2024-01-01", "2026-12-31")}.items():
        e = ex[(ex.index >= a) & (ex.index <= b)]
        if len(e) >= 6:
            print(f"    {k}: excess {e.mean()*12*100:+.1f}%/yr (t{e.mean()/e.std()*np.sqrt(len(e)):+.1f}), "
                  f"portfolio CAGR {((1+s.ret[e.index]).prod()**(12/len(e))-1)*100:+.1f}% vs SPY "
                  f"{((1+s.spy[e.index]).prod()**(12/len(e))-1)*100:+.1f}%")


def main():
    pd.set_option("display.width", 200)
    m = month_panel()
    m.to_parquet(os.path.join(PANEL, "month_panel.parquet"), index=False)
    summarise(portfolio(m, FACTORS, "all"), "composite: surprise + buyback + FCF + issuance + 12-1 momentum, top decile")
    summarise(portfolio(m, {"sue": +1}, "sue"), "earnings surprise alone, top decile")
    summarise(portfolio(m, {"mom_12_1": +1}, "mom"), "12-1 momentum alone, top decile")
    summarise(portfolio(m, {"buyback_yield": +1, "fcf_yield": +1, "d_shares_yoy": -1}, "cap"),
              "capital return alone, top decile")
    summarise(portfolio(m, {"sue": +1, "mom_12_1": +1}, "em"), "earnings momentum: surprise + 12-1, top decile")


if __name__ == "__main__":
    main()
