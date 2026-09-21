"""xsec_straddle_test.py — which names' options are MISPRICED, on seven years of real chains.

Goyal & Saretto (2009 JFE): sort names on realised minus implied volatility; straddles on
the names whose IV is low against realised earn a lot, straddles on the names whose IV is
high against realised lose. That is a statement about the price of the OPTION, not the
direction of the stock, so it is the one edge in the literature the weekly book can use
without a direction call it has measured itself unable to make (xsec_predictors_test.py:
best weekly IC 0.02, nothing clears the multiple-testing bar).

The trade: at the last session of each week, buy the ATM straddle (call + put at the strike
nearest spot, expiry nearest 30d in [10, 60]) AT THE ASK. Two exits:
    expiry   : intrinsic value off the split-adjusted close on the expiry date. Exact.
    1 week   : sell both legs AT THE BID on the first chain day >= t+7 where both are quoted.
Return is P&L over the straddle's own cost. Deciles are formed on the SAME date across names,
so the result is a ranking of which names to sell premium on and which to buy it on.

Sorts tested: ivrv21 = atm_iv - 21d trimmed realised (the live engine's read),
              ivrv252 = atm_iv - 252d realised (Goyal-Saretto's own construction),
              term_slope, straddle_pct, and atm_iv itself.
Everything is signed so that a POSITIVE decile-10-minus-decile-1 means "buying the straddle
where the sort says vol is cheap, selling where it says vol is rich, made money".
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS, adjust_splits, universe, weekly  # noqa: E402
from xsec_vertical_test import load_chain  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")


def straddles(ch, ent):
    key = ["date", "act_symbol"]
    c = ch.merge(ent[key + ["near_dte", "close"]], on=key)
    c = c[c.dte == c.near_dte]
    c["mny_d"] = (c.strike / c.close - 1).abs()
    k = c.groupby(key).mny_d.idxmin()
    atm_strike = c.loc[k.values, key + ["strike", "expiration"]]
    c = c.merge(atm_strike, on=key + ["strike", "expiration"])
    cl = c[c.call_put == "Call"][key + ["strike", "expiration", "near_dte", "bid", "ask"]]
    pu = c[c.call_put == "Put"][key + ["strike", "expiration", "bid", "ask"]]
    s = cl.merge(pu, on=key + ["strike", "expiration"], suffixes=("_c", "_p"))
    s = s[(s.bid_c > 0) & (s.bid_p > 0)]
    s["cost"] = s.ask_c + s.ask_p
    s["cost_bid"] = s.bid_c + s.bid_p
    s["rt_spread"] = (s.cost - s.cost_bid) / s.cost          # one-way spread as % of cost
    return s


def settle(s, ch, px):
    cl = px[["date", "act_symbol", "close"]].sort_values("date")
    s = s.sort_values("expiration")
    s = pd.merge_asof(s, cl.rename(columns={"date": "expiration", "close": "spot_T"}),
                      on="expiration", by="act_symbol", direction="backward",
                      tolerance=pd.Timedelta(days=4))
    s["ret_expiry"] = ((s.spot_T - s.strike).abs() - s.cost) / s.cost
    m = ch[["date", "act_symbol", "expiration", "strike", "call_put", "bid"]]
    s["exit_after"] = s.date + pd.Timedelta(days=7)
    for right, lab in (("Call", "c"), ("Put", "p")):
        mm = m[m.call_put == right].drop(columns="call_put").rename(columns={"date": "mdate", "bid": f"xbid_{lab}"})
        s = s.sort_values("exit_after"); mm = mm.sort_values("mdate")
        s = pd.merge_asof(s, mm, left_on="exit_after", right_on="mdate",
                          by=["act_symbol", "expiration", "strike"], direction="forward",
                          tolerance=pd.Timedelta(days=4)).drop(columns="mdate")
    s["ret_1w"] = (s.xbid_c + s.xbid_p - s.cost) / s.cost
    return s


def decile_table(s, sort, sign, ycol):
    x = s[[sort, ycol, "date"]].dropna().copy()
    x["v"] = x[sort] * sign
    x["dec"] = x.groupby("date").v.transform(lambda v: pd.qcut(v, 10, labels=False, duplicates="drop"))
    by = x.groupby("dec")[ycol].agg(["mean", "median", "count"])
    by["win"] = x.groupby("dec")[ycol].apply(lambda v: (v > 0).mean())
    per_date = x.groupby(["date", "dec"])[ycol].mean().unstack()
    spread = (per_date[per_date.columns.max()] - per_date[0]).dropna()
    t = spread.mean() / spread.std() * np.sqrt(len(spread))
    row = {"sort": sort, "exit": ycol[4:], "n": len(x), "dates": len(spread),
           "D1 mean %": by["mean"].iloc[0] * 100, "D10 mean %": by["mean"].iloc[-1] * 100,
           "D10-D1 %": spread.mean() * 100, "t": t, "hit": (spread > 0).mean()}
    for k, (a, b) in SPLITS.items():
        sub = spread[(spread.index >= a) & (spread.index <= b)]
        row[k] = f"{sub.mean()*100:+.1f}% (t{sub.mean()/sub.std()*np.sqrt(len(sub)):+.1f})" if len(sub) >= 15 else "—"
    return row, by


def main():
    pd.set_option("display.width", 250)
    panel = pd.read_parquet(os.path.join(PANEL, "xsec_panel.parquet"))
    panel["act_symbol"] = panel.act_symbol.astype(str)
    u = weekly(universe(panel), 1)
    u["rv252"] = u.groupby("act_symbol").rv21.transform(lambda s: s.rolling(52, min_periods=26).mean())
    u["ivrv21"] = u.atm_iv - u.rv21
    u["ivrv252"] = u.atm_iv - u.rv252
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"))
    px["act_symbol"] = px.act_symbol.astype(str)
    px = adjust_splits(px[px.act_symbol.isin(set(u.act_symbol))])
    parts = []
    for yr in sorted({d.year for d in u.date.unique()}):
        uu = u[u.date.dt.year == yr]
        months = [f"{yr}-{m:02d}" for m in range(1, 13)] + [f"{yr+1}-01", f"{yr+1}-02", f"{yr+1}-03"]
        ch = load_chain(months)
        if ch.empty:
            continue
        st = straddles(ch, uu[["date", "act_symbol", "near_dte", "close"]])
        parts.append(settle(st, ch, px))
        print(f"{yr}: {len(parts[-1]):,} straddles", flush=True)
        del ch
    s = pd.concat(parts, ignore_index=True)
    s = s.merge(u[["date", "act_symbol", "ivrv21", "ivrv252", "term_slope", "straddle_pct", "atm_iv",
                   "days_to_earn", "near_dte"]], on=["date", "act_symbol", "near_dte"])
    s = s[s.rt_spread <= 0.15]                    # entry-side liquidity screen only
    print(f"{len(s):,} straddles, {s.date.nunique()} weeks, {s.act_symbol.nunique()} names; "
          f"cost {s.cost.median():.2f} median, one-way spread {s.rt_spread.median()*100:.1f}% of cost")
    for ycol in ("ret_expiry", "ret_1w"):
        v = s[ycol].dropna()
        print(f"\nUNCONDITIONAL long ATM straddle, exit {ycol[4:]}: n={len(v):,} mean {v.mean()*100:+.1f}% "
              f"median {v.median()*100:+.1f}% win {(v>0).mean()*100:.0f}%  t={v.mean()/v.std()*np.sqrt(len(v)):+.1f}")
    rows = []
    # sign: +1 means D10 = names where the sort says vol is CHEAP (buy), D1 = rich (sell)
    for sort, sign in (("ivrv21", -1), ("ivrv252", -1), ("term_slope", -1), ("straddle_pct", -1), ("atm_iv", -1)):
        for ycol in ("ret_expiry", "ret_1w"):
            row, by = decile_table(s, sort, sign, ycol)
            rows.append(row)
            if sort in ("ivrv21", "ivrv252") and ycol == "ret_expiry":
                print(f"\n{sort} deciles (D1 = richest IV vs realised .. D10 = cheapest), exit at expiry:")
                print((by.assign(**{"mean": by["mean"] * 100, "median": by["median"] * 100})).round(2).to_string())
    print("\nD10 (cheap vol, BUY) minus D1 (rich vol, SELL), long-straddle return over cost:")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
    # names with a print inside the expiry: the earnings VRP finding says rich sells
    e = s[s.days_to_earn.notna() & (s.days_to_earn <= s.near_dte)]
    if len(e) > 500:
        print(f"\n--- names reporting BEFORE expiry ({len(e):,}) ---")
        for sort in ("ivrv21", "ivrv252"):
            row, by = decile_table(e, sort, -1, "ret_expiry")
            print(pd.DataFrame([row]).to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
    s.to_parquet(os.path.join(PANEL, "straddles.parquet"), index=False)


if __name__ == "__main__":
    main()
