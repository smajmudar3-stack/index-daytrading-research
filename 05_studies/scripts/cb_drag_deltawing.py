"""Like-for-like cross-check of the coordinator's SPY result: DELTA-DEFINED wings.

Their structures are "iron condor 30/16" (short 30-delta, long 16-delta) and "16/05", plus an
ATM iron butterfly. A delta-defined wing is NARROW, which is why the 8-crossing drag lands near
10% of capital at risk. This script measures that on the same SPY EOD bid/ask file, and on SPX
0DTE for comparison, using their fill convention (enter at ask / exit at bid = FULL spread per
leg, both ways) and also the half-spread convention.
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats as st

from idt import paths

OPT = "opt_eod/SPY_options.parquet"  # path under DATA_ROOT, resolved at the read site
UND = "opt_eod/SPY_underlying.parquet"


def run(lo, hi, short_d, long_d, atm=False):
    sub = o[(o.dte >= lo) & (o.dte <= hi)]
    acc = []
    for (dt, exp), g in sub.groupby(["date", "expiration"], sort=False):
        S = g.S.iloc[0]; ST = g.ST.iloc[0]
        c = g[g.type == "call"]; p = g[g.type == "put"]
        if len(c) < 4 or len(p) < 4:
            continue
        if atm:
            sc = c.loc[(c.strike - S).abs().idxmin()]; sp_ = p.loc[(p.strike - S).abs().idxmin()]
        else:
            sc = c.loc[(c.ad - short_d).abs().idxmin()]; sp_ = p.loc[(p.ad - short_d).abs().idxmin()]
        lc = c.loc[(c.ad - long_d).abs().idxmin()]; lp = p.loc[(p.ad - long_d).abs().idxmin()]
        if sc.strike < sp_.strike or lc.strike <= sc.strike or lp.strike >= sp_.strike:
            continue
        cr = (sc.mid + sp_.mid) - (lc.mid + lp.mid)
        spr = sc.sp + sp_.sp + lc.sp + lp.sp
        wd = max(lc.strike - sc.strike, sp_.strike - lp.strike)
        rk = wd - cr
        if cr <= 0 or rk <= 0.05 * wd:
            continue
        pay = (max(0, ST - sc.strike) + max(0, sp_.strike - ST)
               - max(0, ST - lc.strike) - max(0, lp.strike - ST))
        acc.append((cr, spr, wd, rk, pay))
    A = np.array(acc)
    if len(A) < 100:
        return None
    cr, spr, wd, rk, pay = A.T
    pnl_full = cr - 2 * spr - pay        # enter at ask, exit at bid (their convention)
    pnl_half = cr - spr - pay            # 8 half-spreads
    pnl_mid = cr - pay
    return dict(n=len(A), cr_pct_w=round(100 * np.median(cr / wd), 1),
                half_rt_pct_credit=round(100 * np.median(spr / cr), 1),
                FULL_rt_pct_credit=round(100 * np.median(2 * spr / cr), 1),
                half_rt_pct_RISK=round(100 * np.median(spr / rk), 2),
                FULL_rt_pct_RISK=round(100 * np.median(2 * spr / rk), 2),
                win=round(100 * (pnl_full > 0).mean(), 1),
                mid_r=round(100 * (pnl_mid / rk).mean(), 2),
                half_r=round(100 * (pnl_half / rk).mean(), 2),
                FULL_r=round(100 * (pnl_full / rk).mean(), 2),
                t_FULL=round(st.ttest_1samp(100 * pnl_full / rk, 0).statistic, 1))


pd.set_option("display.width", 230)


def main():
    # these were module-level before the guard; the functions above
    # still read them, so they stay global — only the work moved.
    global o

    und = pd.read_parquet(paths.require_data(UND))
    und["date"] = pd.to_datetime(und["date"])
    close = und.set_index("date").sort_index()["close"]

    f = pq.ParquetFile(paths.require_data(OPT))
    parts = []
    for i in range(f.metadata.num_row_groups):
        t = f.read_row_group(i, columns=["expiration", "strike", "type", "bid", "ask", "delta", "date"]).to_pandas()
        t["dte"] = (t.expiration - t.date).dt.days
        parts.append(t[(t.dte >= 5) & (t.dte <= 45) & (t.bid > 0) & (t.ask > t.bid)])
    o = pd.concat(parts, ignore_index=True)
    del parts
    o["mid"] = .5 * (o.bid + o.ask); o["sp"] = o.ask - o.bid; o["ad"] = o.delta.abs()
    o["S"] = close.reindex(o.date).values
    o["ST"] = close.reindex(o.expiration).values
    o = o.dropna(subset=["S", "ST"])
    print("rows", len(o))

    rows = []
    for tag, lo, hi in [("weekly 5-10d", 5, 10), ("monthly 25-45d", 25, 45)]:
        for lbl, sd, ld, atm in [("condor 30/16", 0.30, 0.16, False),
                                 ("condor 16/05", 0.16, 0.05, False),
                                 ("condor 10/05", 0.10, 0.05, False),
                                 ("IRON BUTTERFLY ATM/16", None, 0.16, True),
                                 ("IRON BUTTERFLY ATM/05", None, 0.05, True)]:
            r = run(lo, hi, sd, ld, atm)
            if r:
                rows.append(dict(tenor=tag, structure=lbl, **r))
    print("\nSPY, real EOD bid/ask, DELTA-DEFINED WINGS (the coordinator's structures)")
    print("mid_r / half_r / FULL_r = mean % of capital at risk per trade under each fill convention")
    print("FULL_r = enter at ask, exit at bid -- overlapping trades, t-stats OPTIMISTIC\n")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
