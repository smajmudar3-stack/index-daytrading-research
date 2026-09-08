"""WEEKLY vs MONTHLY iron condors and iron butterflies on SPY, priced on REAL EOD bid/ask.

Data: data/opt_eod/SPY_options.parquet (24.7M rows, 2008-2025) -- real quoted bid, ask, delta, IV.
No pricing model is used. Entry is at the EOD quote; the credit is taken at the MID and then the
half-spread of all four legs is charged. Settlement is against the underlying close on the
expiration date (SPY options are AM/PM American and physically settled; charging no exit cost is
therefore OPTIMISTIC and is flagged in the output by a second, exit-cost-charged column).
"""
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats as st

import os

from idt import paths

OPT = "opt_eod/SPY_options.parquet"  # path under DATA_ROOT, resolved at the read site
UND = "opt_eod/SPY_underlying.parquet"
COLS = ["expiration", "strike", "type", "bid", "ask", "delta", "date",
        "implied_volatility", "open_interest", "volume"]



def pick(g, typ, target_delta):
    d = g[g.type == typ]
    if len(d) == 0:
        return None
    i = (d.adelta - target_delta).abs().idxmin()
    return d.loc[i]


def nearest_strike(g, typ, k):
    d = g[g.type == typ]
    if len(d) == 0:
        return None
    i = (d.strike - k).abs().idxmin()
    if abs(d.loc[i, "strike"] - k) > 0.35 * abs(k - g.S.iloc[0]) + 1.5:
        return None
    return d.loc[i]


def build_trades(dte_lo, dte_hi, sdelta, wing_pct, kind="condor"):
    """One trade per (entry date, chosen expiry). wing_pct = wing width as % of spot."""
    sel = opt[(opt.dte >= dte_lo) & (opt.dte <= dte_hi)]
    rows = []
    for (dt, exp), g in sel.groupby(["date", "expiration"], sort=False):
        S = g.S.iloc[0]; ST = g.ST.iloc[0]
        w = wing_pct * S
        if kind == "fly":
            sc = nearest_strike(g, "call", S); sp = nearest_strike(g, "put", S)
        else:
            sc = pick(g, "call", sdelta); sp = pick(g, "put", sdelta)
        if sc is None or sp is None or sc.strike < sp.strike:
            continue
        lc = nearest_strike(g, "call", sc.strike + w)
        lp = nearest_strike(g, "put", sp.strike - w)
        if lc is None or lp is None:
            continue
        if lc.strike <= sc.strike or lp.strike >= sp.strike:
            continue
        credit = (sc.mid + sp.mid) - (lc.mid + lp.mid)
        cost = sc.half + sp.half + lc.half + lp.half
        width = max(lc.strike - sc.strike, sp.strike - lp.strike)
        risk = width - credit
        if credit <= 0 or risk <= 0.15 * width:
            continue
        pay = (max(0, ST - sc.strike) + max(0, sp.strike - ST)
               - max(0, ST - lc.strike) - max(0, lp.strike - ST))
        rows.append(dict(date=dt, exp=exp, dte=g.dte.iloc[0], S=S, ST=ST,
                         kc=sc.strike, kp=sp.strike, kcl=lc.strike, kpl=lp.strike,
                         credit=credit, cost=cost, width=width, risk=risk, pay=pay,
                         iv=0.5 * (sc.implied_volatility + sp.implied_volatility),
                         oi=min(sc.open_interest, sp.open_interest, lc.open_interest, lp.open_interest),
                         adc=sc.adelta, adp=sp.adelta))
    t = pd.DataFrame(rows)
    if len(t) == 0:
        return t
    t["pnl_mid"] = t.credit - t.pay
    t["pnl_net"] = t.credit - t.cost - t.pay            # 4 half-spreads at entry only
    t["pnl_rt"] = t.credit - 2 * t.cost - t.pay          # closed before/at expiry
    for c in ["pnl_mid", "pnl_net", "pnl_rt"]:
        t[c + "_r"] = 100 * t[c] / t.risk
    t["cost_pct_credit"] = 100 * t.cost / t.credit
    t["rt_pct_credit"] = 200 * t.cost / t.credit
    t["cr_pct_w"] = 100 * t.credit / t.width
    t["dow"] = t.date.dt.dayofweek
    return t


def summ(t, label):
    if len(t) < 40:
        return None
    d = dict(label=label, n=len(t), dte=round(t.dte.mean(), 1),
             cr_pct_w=round(t.cr_pct_w.mean(), 1),
             ENTRY_pct_cr=round(t.cost_pct_credit.median(), 1),
             RT_pct_cr=round(t.rt_pct_credit.median(), 1),
             win=round(100 * (t.pnl_net > 0).mean(), 1))
    for lbl, c in [("mid", "pnl_mid_r"), ("net", "pnl_net_r"), ("rt", "pnl_rt_r")]:
        d[lbl] = round(t[c].mean(), 2)
        d["t_" + lbl] = round(st.ttest_1samp(t[c], 0).statistic, 2)
    d["worst"] = round(t.pnl_net_r.min(), 0)
    d["p01"] = round(t.pnl_net_r.quantile(0.01), 0)
    return d


pd.set_option("display.width", 260)
rows = []


def main():
    # these were module-level before the guard; the functions above
    # still read them, so they stay global — only the work moved.
    global opt

    und = pd.read_parquet(paths.require_data(UND))
    und["date"] = pd.to_datetime(und["date"])
    und = und.set_index("date").sort_index()
    close = und["close"]

    print("loading chains (DTE<=45 only)...")
    f = pq.ParquetFile(paths.require_data(OPT))
    parts = []
    for i in range(f.metadata.num_row_groups):
        t = f.read_row_group(i, columns=COLS).to_pandas()
        t["dte"] = (t.expiration - t.date).dt.days
        parts.append(t[(t.dte >= 3) & (t.dte <= 45) & (t.bid > 0) & (t.ask > t.bid)])
    opt = pd.concat(parts, ignore_index=True)
    del parts
    opt["mid"] = 0.5 * (opt.bid + opt.ask)
    opt["half"] = 0.5 * (opt.ask - opt.bid)
    opt["adelta"] = opt.delta.abs()
    opt = opt[(opt.adelta > 0.005) & (opt.adelta < 0.995)]
    print("usable rows", len(opt), "dates", opt.date.nunique(),
          opt.date.min().date(), "->", opt.date.max().date())

    opt["S"] = close.reindex(opt.date).values
    opt["ST"] = close.reindex(opt.expiration).values
    opt = opt.dropna(subset=["S", "ST"])
    opt = opt.sort_values(["date", "expiration", "type", "strike"])

    print("\n" + "=" * 110)
    print("WEEKLY (5-10 DTE) vs MONTHLY (25-40 DTE) SPY IRON CONDORS, REAL EOD BID/ASK")
    print("returns are % of capital at risk per trade; overlapping trades, so t-stats are OPTIMISTIC")
    print("=" * 110)
    store = {}

    for tag, lo, hi in [("weekly 5-10d", 5, 10), ("monthly 25-40d", 25, 40)]:
        for sd in [0.10, 0.16, 0.30]:
            for wp in [0.02, 0.04]:
                t = build_trades(lo, hi, sd, wp)
                s = summ(t, f"{tag} d={sd} wing={wp*100:.0f}%")
                if s:
                    rows.append(s)
                    store[(tag, sd, wp)] = t
        t = build_trades(lo, hi, None, 0.04, kind="fly")
        s = summ(t, f"{tag} IRON BUTTERFLY wing=4%")
        if s:
            rows.append(s)
            store[(tag, "fly", 0.04)] = t
    print(pd.DataFrame(rows).to_string(index=False))

    key = ("weekly 5-10d", 0.16, 0.04)
    if key in store:
        t = store[key]
        print("\n--- weekly 16-delta 4%-wing condor: entry DAY OF WEEK ---")
        print(t.groupby("dow").apply(lambda x: pd.Series(dict(
            n=len(x), win=round(100 * (x.pnl_net > 0).mean(), 1),
            net=round(x.pnl_net_r.mean(), 2),
            tstat=round(st.ttest_1samp(x.pnl_net_r, 0).statistic, 2))), include_groups=False).to_string())
        print("\n--- by entry IV quintile (IV-rank proxy) ---")
        t2 = t.assign(q=pd.qcut(t.iv, 5, labels=[1, 2, 3, 4, 5]))
        print(t2.groupby("q", observed=True).apply(lambda x: pd.Series(dict(
            n=len(x), iv=round(x.iv.mean(), 3), cr_pct_w=round(x.cr_pct_w.mean(), 1),
            win=round(100 * (x.pnl_net > 0).mean(), 1), net=round(x.pnl_net_r.mean(), 2),
            tstat=round(st.ttest_1samp(x.pnl_net_r, 0).statistic, 2))), include_groups=False).to_string())
        print("\n--- by calendar year ---")
        t3 = t.assign(yr=t.date.dt.year)
        print(t3.groupby("yr").apply(lambda x: pd.Series(dict(
            n=len(x), win=round(100 * (x.pnl_net > 0).mean(), 1),
            net=round(x.pnl_net_r.mean(), 2))), include_groups=False).to_string())
        print("\n--- worst 12 entries ---")
        print(t.nsmallest(12, "pnl_net_r")[["date", "exp", "S", "ST", "kp", "kc", "credit",
                                            "risk", "pnl_net_r"]].round(2).to_string(index=False))
        # was a /private/tmp scratchpad from the authoring session; it no longer exists
        os.makedirs(paths.data("scratch"), exist_ok=True)
        t.to_parquet(paths.data("scratch", "spy_weekly_cnd.parquet"))

    print("\n--- STRESS WINDOWS: weekly 16-delta condor, trades OPEN into the event ---")
    for lbl, a, b in [("Feb2018", "2018-01-25", "2018-02-12"), ("Mar2020", "2020-02-19", "2020-03-23"),
                      ("Aug2024", "2024-07-26", "2024-08-07"), ("Apr2025", "2025-03-25", "2025-04-10")]:
        if key not in store:
            break
        t = store[key]
        seg = t[(t.date >= a) & (t.date <= b)]
        if len(seg):
            print(f"{lbl:9s} n={len(seg):3d} win={100*(seg.pnl_net>0).mean():5.1f}% "
                  f"mean={seg.pnl_net_r.mean():7.1f}% worst={seg.pnl_net_r.min():7.1f}% "
                  f"sum_of_risk_lost={seg.pnl_net_r.sum()/100:6.2f}R")


if __name__ == "__main__":
    main()
