"""spy_putwrite_test.py — systematic index put-writing and covered calls on REAL monthly
quotes, 2019-2026. The one options-income method with a decades-long public record (the
CBOE PUT and BXM indexes) that this repo had not measured at the monthly horizon.

Every 0DTE credit structure here measured negative after the spread (147,350 SPY trades).
That was 0DTE, where the premium is pennies and the bid-ask is most of it. A MONTHLY
cash-secured put is one leg, sold once a month, held to expiry: the spread is paid once
on a $5-15 premium. Different arithmetic, so it gets its own test.

Rules, on the Dolt SPY chain (thinned, ~11 strikes a side, expiries to ~90 days):
  * on the last chain day of each month, pick the expiry nearest 30 days (21-45 window)
  * PUT-WRITE: sell the put whose delta is nearest TARGET (0.50 = ATM like the CBOE PUT
    index, 0.30 and 0.15 as the OTM variants) AT THE BID; collateral = strike
  * COVERED CALL: hold SPY, sell the call nearest 0.30 delta at the bid
  * settle at expiry on the split-adjusted close; no early management, no rolls
  * returns are on the collateral (put-write) or on the SPY position (covered call), so
    they compare directly to SPY buy-and-hold over the same months
Reported: CAGR, max drawdown, worst month, Sharpe, and the same at 2x collateral use.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_vertical_test import load_chain  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")


def spy_chain():
    months = sorted({os.path.basename(f)[6:13] for f in os.listdir(PANEL) if f.startswith("chain_")})
    out = []
    for m in months:
        ch = pd.read_parquet(os.path.join(PANEL, f"chain_{m}.parquet"))
        ch = ch[ch.act_symbol.astype(str) == "SPY"]
        out.append(ch)
    ch = pd.concat(out, ignore_index=True)
    ch["act_symbol"] = "SPY"
    ch["call_put"] = ch.call_put.astype(str)
    ch["dte"] = (ch.expiration - ch.date).dt.days
    ch["adelta"] = ch.delta.abs()
    return ch[(ch.ask > 0) & (ch.ask >= ch.bid)]


def spy_px():
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"))
    px = px[px.act_symbol.astype(str) == "SPY"][["date", "close"]].sort_values("date")
    return px.set_index("date").close


def month_ends(ch):
    d = pd.Series(sorted(ch.date.unique()))
    return d.groupby(d.dt.to_period("M")).max().tolist()


def run(ch, px, right, target, label):
    rows = []
    for d in month_ends(ch):
        day = ch[(ch.date == d) & (ch.call_put == right) & (ch.dte >= 21) & (ch.dte <= 45)]
        if day.empty:
            continue
        exp = day.expiration.iloc[(day.dte - 30).abs().argmin()]
        leg = day[day.expiration == exp]
        leg = leg.iloc[(leg.adelta - target).abs().argmin()]
        if leg.bid <= 0:
            continue
        spot0 = float(px.asof(d))
        after = px[px.index >= exp]
        if after.empty:
            continue
        spot_T = float(after.iloc[0])
        intrinsic = max(0.0, leg.strike - spot_T) if right == "Put" else max(0.0, spot_T - leg.strike)
        if right == "Put":
            ret = (leg.bid - intrinsic) / leg.strike                     # on cash collateral
        else:
            ret = (spot_T - spot0 + leg.bid - intrinsic) / spot0           # covered call on the shares
        rows.append({"date": d, "expiry": exp, "strike": leg.strike, "delta": leg.adelta, "premium": leg.bid,
                     "spot0": spot0, "spot_T": spot_T, "ret": ret, "spy": spot_T / spot0 - 1})
    s = pd.DataFrame(rows).set_index("date")
    return s


def summarise(s, label):
    def stats(r):
        eq = (1 + r).cumprod()
        yrs = len(r) / 12
        return {"CAGR": eq.iloc[-1] ** (1 / yrs) - 1, "max DD": (eq / eq.cummax() - 1).min(),
                "worst month": r.min(), "months>0": (r > 0).mean(), "sharpe": r.mean() / r.std() * np.sqrt(12)}
    t = pd.DataFrame({label: stats(s.ret), "SPY same months": stats(s.spy),
                      f"{label} 2x": stats(2 * s.ret - 0.005), "SPY 2x": stats(2 * s.spy - 0.005)}).T
    print(f"\n=== {label}: {len(s)} months {s.index.min().date()} .. {s.index.max().date()}, "
          f"avg premium {s.premium.mean():.2f} on ${s.strike.mean():.0f}, avg |delta| {s.delta.mean():.2f} ===")
    print(t.to_string(float_format=lambda v: f"{v:9.3f}"))
    ex = s.ret - s.spy
    print(f"  excess over SPY {ex.mean()*12*100:+.1f}%/yr, t={ex.mean()/ex.std()*np.sqrt(len(ex)):+.2f}; "
          f"2020-03 month: strategy {s.ret[s.index.year==2020].min()*100:+.1f}% vs SPY {s.spy[s.index.year==2020].min()*100:+.1f}%")


def main():
    pd.set_option("display.width", 200)
    ch, px = spy_chain(), spy_px()
    for target, lab in ((0.50, "ATM put-write (CBOE PUT style)"), (0.30, "30-delta put-write"), (0.15, "15-delta put-write")):
        summarise(run(ch, px, "Put", target, lab), lab)
    summarise(run(ch, px, "Call", 0.30, "covered call, 30-delta"), "covered call, 30-delta")


if __name__ == "__main__":
    main()
