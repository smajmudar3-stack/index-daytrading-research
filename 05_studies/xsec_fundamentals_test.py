"""xsec_fundamentals_test.py — the company-specific factors, measured: earnings surprise,
margins, cash flow, buybacks, dilution, dividends, sales growth.

Two families, two horizons, because they are different kinds of information:

  EARNINGS SURPRISE (event time). Bernard & Thomas 1989: post-earnings-announcement drift is
  the size of the SURPRISE, not just the sign of the reaction. Here SUE = (reported EPS -
  consensus) / price on the announcement day, from Dolt `eps_history` joined to the
  announcement date in `earnings_calendar`. Forward excess returns (over SPY) from the open
  of the session after the announcement, 5 / 10 / 21 / 63 sessions. Quintiles formed within
  each calendar week's cohort of announcers, so the spread is a same-week comparison and
  the t-stat is over weeks.

  FUNDAMENTALS (monthly cross-section). Quarterly statements with a 60-day publication lag
  (the `date` column is the period END, not the filing date -- using it unlagged is
  look-ahead): gross margin, net margin, year-on-year margin change, sales growth, FCF yield,
  buyback yield (negative capital-stock issuance / market cap), net issuance, dividend
  yield. Fama-MacBeth rank IC at 21 and 63 sessions, three splits, signed as published.

Universe: names in the Dolt option panel with close >= $10 and 20-day median dollar volume
>= $10m at the signal date. Prices split-adjusted from the Dolt split table.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS, adjust_splits  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
LAG_DAYS = 60


def prices():
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"))
    px["act_symbol"] = px.act_symbol.astype(str)
    fe = pd.read_parquet(os.path.join(PANEL, "features.parquet"), columns=["act_symbol"])
    px = px[px.act_symbol.isin(set(fe.act_symbol.astype(str)) | {"SPY"})]
    px = adjust_splits(px).sort_values(["act_symbol", "date"])
    g = px.groupby("act_symbol", group_keys=False)
    px["adv20"] = g.apply(lambda d: (d.close * d.volume).rolling(20, min_periods=10).median())
    nxt_open = g.open.shift(-1)
    for h in (5, 10, 21, 63):
        px[f"fwd{h}"] = (g.close.shift(-h) / nxt_open - 1).mask(lambda s: s.abs() > 1.5)
    spy = px[px.act_symbol == "SPY"].set_index("date")[[f"fwd{h}" for h in (5, 10, 21, 63)]]
    px = px[px.act_symbol != "SPY"].merge(spy.add_suffix("_spy"), left_on="date", right_index=True, how="left")
    for h in (5, 10, 21, 63):
        px[f"ex{h}"] = px[f"fwd{h}"] - px[f"fwd{h}_spy"]
    return px


def sue_events(px):
    e = pd.read_parquet(os.path.join(PANEL, "eps_history.parquet"))
    e["period_end_date"] = pd.to_datetime(e.period_end_date)
    for c in ("reported", "estimate"):
        e[c] = pd.to_numeric(e[c], errors="coerce")
    e = e.dropna(subset=["reported", "estimate"])
    cal = pd.read_parquet(os.path.join(PANEL, "earnings.parquet"))
    cal["date"] = pd.to_datetime(cal.date)
    cal = cal.drop_duplicates(["act_symbol", "date"]).sort_values("date")
    e = e.sort_values("period_end_date")
    e = pd.merge_asof(e, cal.rename(columns={"date": "ann"}), left_on="period_end_date", right_on="ann",
                      by="act_symbol", direction="forward", tolerance=pd.Timedelta(days=75))
    e = e.dropna(subset=["ann"])
    # the signal date: the announcement day itself for pre-market reports, the next session for
    # after-close ones; `when` is text ("After market close" / "Before market open")
    e["after"] = e["when"].astype(str).str.lower().str.contains("after")
    px = px.sort_values("date")
    e = e.sort_values("ann")
    e = pd.merge_asof(e, px[["date", "act_symbol", "close", "adv20", "open"]].rename(columns={"date": "ann"}),
                      on="ann", by="act_symbol", direction="forward", tolerance=pd.Timedelta(days=4))
    e = e.dropna(subset=["close"])
    e["sue"] = (e.reported - e.estimate) / e.close
    e["sue_rel"] = (e.reported - e.estimate) / e.estimate.abs().replace(0, np.nan)
    # signal date = first session strictly after the report is public
    e["sig"] = e.ann + pd.to_timedelta(np.where(e.after, 1, 0), unit="D")
    e = e.sort_values("sig")
    lab = px[["date", "act_symbol"] + [f"ex{h}" for h in (5, 10, 21, 63)] + ["fwd5", "fwd21", "fwd63"]]
    e = pd.merge_asof(e, lab.rename(columns={"date": "sig"}), on="sig", by="act_symbol",
                      direction="forward", tolerance=pd.Timedelta(days=4))
    e = e[(e.close >= 10) & (e.adv20 >= 10e6)]
    return e


def sue_report(e):
    e = e.copy()
    e["wk"] = e.sig.dt.to_period("W")
    e = e[e.groupby("wk").sue.transform("size") >= 20]
    e["q"] = e.groupby("wk").sue.transform(lambda v: pd.qcut(v.rank(method="first"), 5, labels=False))
    print(f"\nEARNINGS SURPRISE: {len(e):,} announcements, {e.wk.nunique()} weeks, "
          f"{e.act_symbol.nunique()} names, {e.sig.min().date()} .. {e.sig.max().date()}")
    tab = e.groupby("q")[["ex5", "ex10", "ex21", "ex63"]].mean() * 100
    tab.index = ["Q1 worst miss", "Q2", "Q3", "Q4", "Q5 best beat"]
    print("mean EXCESS return over SPY by SUE quintile, % (from the next open):")
    print(tab.round(2).to_string())
    for h in (5, 10, 21, 63):
        w = e.groupby(["wk", "q"])[f"ex{h}"].mean().unstack()
        sp = (w[4] - w[0]).dropna()
        t = sp.mean() / sp.std() * np.sqrt(len(sp))
        line = f"  Q5-Q1 @{h:2d}d: {sp.mean()*100:+.2f}%  t={t:+.2f}  weeks>0 {(sp>0).mean()*100:.0f}%"
        for k, (a, b) in SPLITS.items():
            s = sp[(sp.index.start_time >= a) & (sp.index.start_time <= b)]
            if len(s) >= 15:
                line += f" | {k} {s.mean()*100:+.2f}% (t{s.mean()/s.std()*np.sqrt(len(s)):+.1f})"
        print(line)
    # is the drift in the surprise or in the reaction? both, and their interaction
    e["react"] = np.sign(e.fwd5.fillna(0))  # placeholder replaced below
    return e


def fundamentals(px):
    inc = pd.read_parquet(os.path.join(PANEL, "income_statement.parquet"))
    cf = pd.read_parquet(os.path.join(PANEL, "cash_flow_statement.parquet"))
    inc = inc[inc.period == "Quarter"].copy(); cf = cf[cf.period == "Quarter"].copy()
    for d in (inc, cf):
        d["date"] = pd.to_datetime(d.date)
        for c in d.columns:
            if c not in ("act_symbol", "date", "period"):
                d[c] = pd.to_numeric(d[c], errors="coerce")
    f = inc.merge(cf, on=["act_symbol", "date", "period"], how="outer").sort_values(["act_symbol", "date"])
    g = f.groupby("act_symbol")
    f["gm"] = f.gross_profit / f.sales.replace(0, np.nan)
    f["nm"] = f.net_income / f.sales.replace(0, np.nan)
    f["d_gm_yoy"] = f.gm - g.gm.shift(4)
    f["d_nm_yoy"] = f.nm - g.nm.shift(4)
    f["sales_g"] = f.sales / g.sales.shift(4).replace(0, np.nan) - 1
    f["fcf"] = f.net_cash_from_operating_activities + f.property_and_equipment.fillna(0)   # capex is negative
    f["buyback"] = -f.issuance_of_capital_stock.fillna(0)                                   # net repurchase > 0
    f["divs"] = -f.payment_of_dividends_and_other_distributions.fillna(0)
    f["d_shares_yoy"] = f.average_shares / g.average_shares.shift(4).replace(0, np.nan) - 1
    f["avail"] = f.date + pd.Timedelta(days=LAG_DAYS)
    # monthly cross-sections: last session of each month, latest statement available
    m = px[px.date == px.groupby(px.date.dt.to_period("M")).date.transform("max")].copy()
    m = m[(m.close >= 10) & (m.adv20 >= 10e6)].sort_values("date")
    f = f.sort_values("avail")
    m = pd.merge_asof(m, f[["avail", "act_symbol", "gm", "nm", "d_gm_yoy", "d_nm_yoy", "sales_g", "fcf",
                            "buyback", "divs", "d_shares_yoy", "average_shares"]].rename(columns={"avail": "date"}),
                      on="date", by="act_symbol", direction="backward", tolerance=pd.Timedelta(days=200))
    m["mcap"] = m.average_shares * m.close
    m["fcf_yield"] = 4 * m.fcf / m.mcap.replace(0, np.nan)
    m["buyback_yield"] = 4 * m.buyback / m.mcap.replace(0, np.nan)
    m["div_yield"] = 4 * m.divs / m.mcap.replace(0, np.nan)
    return m


FUND = {  # feature: (published sign, source)
    "gm": (+1, "gross profitability, Novy-Marx 2013"),
    "nm": (+1, "net margin"),
    "d_gm_yoy": (+1, "margin improvement"),
    "d_nm_yoy": (+1, "margin improvement"),
    "sales_g": (+1, "sales growth"),
    "fcf_yield": (+1, "free-cash-flow yield (value)"),
    "buyback_yield": (+1, "net repurchases, Ikenberry et al"),
    "d_shares_yoy": (-1, "net issuance / dilution, Pontiff & Woodgate 2008"),
    "div_yield": (+1, "dividend yield"),
}


def fund_report(m):
    rows = []
    for f, (sgn, src) in FUND.items():
        for h in (21, 63):
            x = m[[f, f"ex{h}", "date"]].dropna()
            x = x[(x[f].abs() < 5)]
            ics = x.groupby("date").apply(lambda g: stats.spearmanr(g[f] * sgn, g[f"ex{h}"])[0] if len(g) >= 50 else np.nan,
                                          include_groups=False).dropna()
            if len(ics) < 12:
                continue
            row = {"feature": f, "sign": "+" if sgn > 0 else "-", "h": h, "months": len(ics), "n": len(x),
                   "IC": ics.mean(), "t": ics.mean() / ics.std() * np.sqrt(len(ics)), "hit": (ics > 0).mean()}
            for k, (a, b) in SPLITS.items():
                s = ics[(ics.index >= a) & (ics.index <= b)]
                row[k] = f"{s.mean():+.3f} (t{s.mean()/s.std()*np.sqrt(len(s)):+.1f})" if len(s) >= 8 else "—"
            rows.append(row)
    t = pd.DataFrame(rows).sort_values(["h", "t"], ascending=[True, False])
    print(f"\nFUNDAMENTALS: monthly cross-sections, {m.date.nunique()} months, {m.act_symbol.nunique()} names, "
          f"statements lagged {LAG_DAYS} days")
    print(t.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    print(f"  {len(t)} tests; expected max |t| under the null ~ {np.sqrt(2*np.log(max(2,len(t)))):.1f}")


def main():
    pd.set_option("display.width", 250)
    px = prices()
    e = sue_events(px)
    sue_report(e)
    e.to_parquet(os.path.join(PANEL, "sue_events.parquet"), index=False)
    m = fundamentals(px)
    fund_report(m)


if __name__ == "__main__":
    main()
