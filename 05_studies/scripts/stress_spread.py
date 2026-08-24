"""Does the bid-ask blow out exactly when you need to exit? Measured, not inferred.

Every backtest in this repo charges the spread observed on the ENTRY day. That
is fine for a winner you close calmly. It is badly wrong for the trade that
matters -- the loser you must close in a panic, when the spread you actually
pay is the stressed one.

This measures the real SPY spread by VIX regime over 2008-2025, including
2008-11, 2018-02, 2020-03 and 2024-08. It also measures WRONG-WAY RISK: the
short put you sold at 20 delta is bought back as a 70-90 delta option, which is
a different and more expensive instrument.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

warnings.filterwarnings("ignore")

OPT = paths.data("opt_eod", "SPY_options.parquet")
SWING = paths.data("swing", "panel.parquet")


def main():
    p = pd.read_parquet(paths.require_data(SWING))
    close = p.pivot(index="date", columns="ticker", values="close").sort_index()
    vix = close["^VIX"].dropna()

    cols = ["date", "expiration", "strike", "type", "bid", "ask", "delta",
            "open_interest", "volume"]

    frames = []
    for year in range(2008, 2026):
        t = pq.read_table(paths.require_data(OPT), columns=cols, filters=[
            ("date", ">=", pd.Timestamp(f"{year}-01-01")),
            ("date", "<=", pd.Timestamp(f"{year}-12-31"))]).to_pandas()
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t["date"])
        t["expiration"] = pd.to_datetime(t["expiration"])
        t["dte"] = (t["expiration"] - t["date"]).dt.days
        t = t[(t.dte.between(20, 60)) & (t.bid > 0.05) & (t.ask > t.bid) &
              (t.open_interest > 10) & (t.delta.abs().between(0.05, 0.95))]
        if t.empty:
            continue
        t["mid"] = (t.bid + t.ask) / 2
        t["spread_pct"] = (t.ask - t.bid) / t.mid
        t["vix"] = t.date.map(vix)
        frames.append(t[["date", "type", "delta", "mid", "spread_pct", "vix", "dte"]])
        print(f"  {year} loaded", flush=True)

    d = pd.concat(frames, ignore_index=True).dropna(subset=["vix"])

    print("\n" + "=" * 88)
    print("SPY OPTION SPREAD BY VIX REGIME  (20-60 DTE, real quotes 2008-2025)")
    print("=" * 88)
    bins = [0, 15, 20, 25, 30, 40, 100]
    labels = ["<15", "15-20", "20-25", "25-30", "30-40", ">40"]
    d["vbin"] = pd.cut(d.vix, bins=bins, labels=labels)

    print(f"  {'VIX':8s} {'n':>10s} {'median':>9s} {'75th':>9s} {'90th':>9s} {'mean':>9s}")
    base = None
    for lab in labels:
        s = d[d.vbin == lab]["spread_pct"]
        if len(s) < 100:
            continue
        if base is None:
            base = s.median()
        print(f"  {lab:8s} {len(s):10,d} {s.median():9.2%} "
              f"{s.quantile(0.75):9.2%} {s.quantile(0.90):9.2%} {s.mean():9.2%}")
    print(f"\n  ratio of >40 VIX median to <15 VIX median: "
          f"{d[d.vbin=='>40']['spread_pct'].median() / d[d.vbin=='<15']['spread_pct'].median():.2f}x")

    print("\n" + "=" * 88)
    print("THE SPECIFIC STRESS EPISODES -- what you would actually have paid")
    print("=" * 88)
    episodes = {
        "2008 GFC (Oct-Nov)": ("2008-10-01", "2008-11-30"),
        "2010 flash crash":   ("2010-05-05", "2010-05-25"),
        "2011 downgrade":     ("2011-08-01", "2011-08-31"),
        "2015 Aug shock":     ("2015-08-20", "2015-09-04"),
        "2018 Volmageddon":   ("2018-02-02", "2018-02-16"),
        "2018 Q4 selloff":    ("2018-12-01", "2018-12-31"),
        "2020 COVID":         ("2020-02-24", "2020-04-03"),
        "2022 bear":          ("2022-06-01", "2022-06-30"),
        "2024 Aug 5 unwind":  ("2024-08-01", "2024-08-09"),
        "CALM baseline 2017": ("2017-01-01", "2017-12-31"),
    }
    print(f"  {'episode':22s} {'VIX avg':>8s} {'median sp':>10s} {'90th sp':>9s} {'vs calm':>8s}")
    calm = d[(d.date >= "2017-01-01") & (d.date <= "2017-12-31")]["spread_pct"].median()
    for name, (a, b) in episodes.items():
        s = d[(d.date >= a) & (d.date <= b)]
        if len(s) < 50:
            continue
        print(f"  {name:22s} {s.vix.mean():8.1f} {s.spread_pct.median():10.2%} "
              f"{s.spread_pct.quantile(0.90):9.2%} {s.spread_pct.median()/calm:7.1f}x")

    print("\n" + "=" * 88)
    print("WRONG-WAY RISK -- the short put you sold at 0.20d is bought back deeper")
    print("=" * 88)
    print(f"  {'delta band':14s} {'n':>10s} {'median spread':>14s} {'median mid $':>13s}")
    for lo, hi in [(0.05, 0.15), (0.15, 0.25), (0.25, 0.40), (0.40, 0.60),
                   (0.60, 0.75), (0.75, 0.90)]:
        s = d[(d.type == "put") & (d.delta.abs().between(lo, hi))]
        if len(s) < 100:
            continue
        print(f"  {lo:.2f}-{hi:.2f} put  {len(s):10,d} {s.spread_pct.median():14.2%} "
              f"{s.mid.median():13.2f}")
    print("\n  A 0.20d short put bought back at 0.80d costs the deeper spread AND a")
    print("  far larger premium -- the cost of exiting scales with how wrong you are.")


if __name__ == "__main__":
    main()
