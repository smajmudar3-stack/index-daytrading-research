"""gxz_straddle_test.py — the pre-earnings straddle the way Gao, Xing & Zhang (JFQA 2018)
actually trade it: buy a few sessions BEFORE the print, sell BEFORE the release. Never
tested here; the repo's -35% straddle number held THROUGH the print, the opposite trade.

The claim: implied volatility ramps into an announcement, so a straddle bought at T-3 and
sold at the close before the release captures the ramp without the crush. GXZ report
+3.34% on average, at mid prices, 1996-2013.

Here, on the Dolt chains (thinned, EOD, real bid/ask), 2020-2026, every announcement with
a chain on both days:
  entry   the close ENTRY_BEFORE sessions before the report session, ATM straddle at the
          expiry nearest 30 days, both legs at the ASK
  exit    the last close BEFORE the release: for a pre-market report, the close two
          sessions... no -- the close of the session before the report date; for an
          after-close report, the close of the report date itself (the print is after it)
          both legs at the BID
  return  (exit proceeds - entry cost) / entry cost, one trade per announcement
Also the mid-to-mid version, so the paper's number and the spread are shown side by side,
and the split by the name's own IV percentile (does the ramp already sit in the price?).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS  # noqa: E402
from xsec_vertical_test import load_chain  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
ENTRY_BEFORE = 3


def atm_straddle(day, spot):
    """(cost_ask, cost_bid, strike, expiration) for the ATM straddle nearest 30 DTE, or None."""
    d = day[(day.dte >= 10) & (day.dte <= 60)]
    if d.empty:
        return None
    exp = d.expiration.iloc[(d.dte - 30).abs().argmin()]
    d = d[d.expiration == exp]
    k = d.strike.iloc[(d.strike - spot).abs().argmin()]
    c, p = d[(d.strike == k) & (d.call_put == "Call")], d[(d.strike == k) & (d.call_put == "Put")]
    if c.empty or p.empty or c.bid.iloc[0] <= 0 or p.bid.iloc[0] <= 0:
        return None
    return {"ask": float(c.ask.iloc[0] + p.ask.iloc[0]), "bid": float(c.bid.iloc[0] + p.bid.iloc[0]),
            "strike": float(k), "expiration": exp}


def main():
    pd.set_option("display.width", 220)
    e = pd.read_parquet(os.path.join(PANEL, "earnings.parquet"))
    e["date"] = pd.to_datetime(e.date)
    e["after"] = e["when"].astype(str).str.lower().str.contains("after")
    e = e.drop_duplicates(["act_symbol", "date"])
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"), columns=["date", "act_symbol", "close", "volume"])
    px["act_symbol"] = px.act_symbol.astype(str)
    fe = pd.read_parquet(os.path.join(PANEL, "features.parquet"), columns=["date", "act_symbol", "atm_iv"])
    fe["act_symbol"] = fe.act_symbol.astype(str)
    fe = fe.sort_values(["act_symbol", "date"])
    fe["iv_pct"] = fe.groupby("act_symbol").atm_iv.transform(
        lambda s: s.rolling(252, min_periods=120).apply(lambda w: (w <= w[-1]).mean(), raw=True))
    rows = []
    for yr in range(2020, 2027):
        months = [f"{yr}-{m:02d}" for m in range(1, 13)]
        ch = load_chain(months)
        if ch.empty:
            continue
        days = sorted(ch.date.unique())
        day_idx = {d: i for i, d in enumerate(days)}
        ey = e[(e.date.dt.year == yr)]
        pxy = px[px.date.dt.year == yr]
        cl = pxy.pivot(index="date", columns="act_symbol", values="close")
        for r in ey.itertuples():
            sym = r.act_symbol
            if sym not in cl.columns:
                continue
            # exit session: the last chain day strictly before the report date (pre-market), or
            # the report date itself (after-close)
            exit_days = [d for d in days if (d <= r.date if r.after else d < r.date)]
            if len(exit_days) < ENTRY_BEFORE + 1:
                continue
            dx = exit_days[-1]
            de = exit_days[-1 - ENTRY_BEFORE]
            if (r.date - de).days > 12:
                continue                                         # chain gap; not a real T-3
            s0 = cl[sym].get(de); s1 = cl[sym].get(dx)
            if pd.isna(s0) or pd.isna(s1) or s0 < 10:
                continue
            day0 = ch[(ch.date == de) & (ch.act_symbol == sym)]
            if day0.empty:
                continue
            st = atm_straddle(day0, s0)
            if not st:
                continue
            day1 = ch[(ch.date == dx) & (ch.act_symbol == sym) & (ch.expiration == st["expiration"]) & (ch.strike == st["strike"])]
            c1, p1 = day1[day1.call_put == "Call"], day1[day1.call_put == "Put"]
            if c1.empty or p1.empty:
                continue
            exit_bid = float(c1.bid.iloc[0] + p1.bid.iloc[0]); exit_mid = float((c1.bid.iloc[0] + c1.ask.iloc[0] + p1.bid.iloc[0] + p1.ask.iloc[0]) / 2)
            entry_mid = (st["ask"] + st["bid"]) / 2
            rows.append({"sym": sym, "report": r.date, "entry": de, "exit": dx, "cost": st["ask"],
                         "ret_real": exit_bid / st["ask"] - 1, "ret_mid": exit_mid / entry_mid - 1,
                         "spot_move": s1 / s0 - 1, "spread_pct": (st["ask"] - st["bid"]) / st["ask"]})
        print(f"{yr}: {sum(1 for x in rows if x['report'].year == yr)} trades", flush=True)
    t = pd.DataFrame(rows)
    t = t.merge(fe[["date", "act_symbol", "iv_pct"]].rename(columns={"date": "entry", "act_symbol": "sym"}), on=["entry", "sym"], how="left")
    print(f"\n{len(t):,} pre-earnings straddles, {t.sym.nunique()} names, entry T-{ENTRY_BEFORE}, exit before the release; "
          f"one-way spread {t.spread_pct.median()*100:.1f}% of cost")
    for lab, col in (("REAL: buy at ask, sell at bid", "ret_real"), ("MID to MID (the paper's convention)", "ret_mid")):
        v = t[col]
        line = f"  {lab:38s} mean {v.mean()*100:+.2f}%  median {v.median()*100:+.2f}%  win {(v>0).mean()*100:.0f}%  t={v.mean()/v.std()*np.sqrt(len(v)):+.1f}"
        for k, (a, b) in SPLITS.items():
            s = v[(t.report >= a) & (t.report <= b)]
            if len(s) > 100:
                line += f" | {k[:1]} {s.mean()*100:+.2f}% (t{s.mean()/s.std()*np.sqrt(len(s)):+.1f})"
        print(line)
    q = pd.qcut(t.iv_pct, 4, labels=["IV low", "IV 2", "IV 3", "IV high"])
    print("\nby the name's own IV percentile at entry (real fills):")
    print(t.groupby(q, observed=True).ret_real.agg(["count", "mean", "median", lambda v: (v > 0).mean()]).round(4).to_string())
    t.to_parquet(os.path.join(PANEL, "gxz_straddles.parquet"), index=False)


if __name__ == "__main__":
    main()
