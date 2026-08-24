"""4-leg bid/ask drag and expectancy for 0DTE SPX iron BUTTERFLIES and CONDORS, on REAL quotes.

Data: data/spxw/data_opt.parquet -- 1,919 sessions 2016-09..2024-05, 30-min grid, moneyness grid
0.98..1.02 in 0.001 steps, all prices expressed as a FRACTION OF SPOT at that quote time.
`payoff` = settlement value / spot_at_quote_time; `sret` = close / spot_at_quote_time.
NO PRICING MODEL IS USED ANYWHERE. `bas` is the real quoted bid-ask spread.

Outputs:
  1. Quoted half-spread per leg, and the 4-leg entry cost as a % of the mid credit.
  2. Round-trip (8 half-spreads) cost as a % of credit -- the number that matters if you MANAGE.
  3. Expectancy per trade at mid / net of entry / net of round trip, normalised by capital at risk.
  4. The 0DTE ATM straddle VRP: mid straddle price vs realised |move|.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

import os

from idt import paths

PATH = "spxw/data_opt.parquet"  # path under DATA_ROOT, resolved at the read site
TIMES = ["10:00:00", "10:30:00", "11:00:00", "11:30:00", "12:00:00", "13:00:00", "14:00:00"]


# ---- wide tables: index (date,time) x moneyness, one per (field, type) -------------------
def wide(field, typ):
    d = df[df.option_type == typ]
    return d.pivot_table(index=["quote_date", "t"], columns="mnes_rel", values=field)



def col(tbl, m):
    """Nearest-grid-point column (grid is 0.001 spaced; targets are snapped to it)."""
    j = int(np.argmin(np.abs(GRID - m)))
    return tbl.iloc[:, j].values, GRID[j]


def strike_for_delta(dtbl, target_abs, sign):
    """Per-row moneyness whose |delta| is closest to target. sign=+1 calls, -1 puts."""
    d = dtbl.values * sign          # positive for calls, positive after flip for puts
    d = np.where(np.isfinite(d) & (d > 0) & (d < 1), d, np.nan)
    j = np.nanargmin(np.abs(d - target_abs), axis=1)
    return GRID[j], j


def gather(tbl, j):
    v = tbl.values
    return v[np.arange(len(v)), j]




# =============================================================================
# 2/3. STRUCTURES
# =============================================================================
def run_structure(kind, entry_t, wing, short_delta=None, short_off=None):
    """Returns a DataFrame of per-trade results for one (structure, time, params) cell."""
    mask = idx.get_level_values("t") == entry_t
    sub = np.where(mask)[0]
    if len(sub) == 0:
        return None

    def rows(tbl):
        return tbl.values[sub]

    if kind == "fly":
        mc, mp = 1.0, 1.0
        jc = int(np.argmin(np.abs(GRID - 1.0)))
        jp = jc
        kc = np.full(len(sub), 1.0)
        kp = np.full(len(sub), 1.0)
        scm = rows(MID_C)[:, jc]; spm = rows(MID_P)[:, jp]
        scb = rows(BAS_C)[:, jc]; spb = rows(BAS_P)[:, jp]
    else:
        dC = DLT_C.iloc[sub]; dP = DLT_P.iloc[sub]
        if short_delta is not None:
            kc, jc = strike_for_delta(dC, short_delta, +1)
            kp, jp = strike_for_delta(dP, short_delta, -1)
        else:
            jc = np.full(len(sub), int(np.argmin(np.abs(GRID - (1 + short_off)))))
            jp = np.full(len(sub), int(np.argmin(np.abs(GRID - (1 - short_off)))))
            kc, kp = GRID[jc], GRID[jp]
        scm = gather(MID_C.iloc[sub], jc); spm = gather(MID_P.iloc[sub], jp)
        scb = gather(BAS_C.iloc[sub], jc); spb = gather(BAS_P.iloc[sub], jp)

    # long wings at short strike +/- wing
    lcm = np.full(len(sub), np.nan); lpm = np.full(len(sub), np.nan)
    lcb = np.full(len(sub), np.nan); lpb = np.full(len(sub), np.nan)
    kcl = kc + wing; kpl = kp - wing
    okgrid = (kcl <= GRID.max() + 1e-9) & (kpl >= GRID.min() - 1e-9)
    jcl = np.argmin(np.abs(GRID[None, :] - kcl[:, None]), axis=1)
    jpl = np.argmin(np.abs(GRID[None, :] - kpl[:, None]), axis=1)
    lcm = gather(MID_C.iloc[sub], jcl); lpm = gather(MID_P.iloc[sub], jpl)
    lcb = gather(BAS_C.iloc[sub], jcl); lpb = gather(BAS_P.iloc[sub], jpl)
    kcl_a, kpl_a = GRID[jcl], GRID[jpl]

    sret = SRET.iloc[sub].values
    iv = IVATM.reindex(idx[sub]).values

    credit = (scm + spm) - (lcm + lpm)
    entry_cost = 0.5 * (scb + spb + lcb + lpb)
    width = np.maximum(kcl_a - kc, kp - kpl_a)
    # settlement payoff of the whole structure, as fraction of spot at entry
    pay = (np.maximum(0, sret - kc) + np.maximum(0, kp - sret)
           - np.maximum(0, sret - kcl_a) - np.maximum(0, kpl_a - sret))
    risk = width - credit
    ok = okgrid & np.isfinite(credit) & np.isfinite(entry_cost) & (credit > 0) & (risk > 0) & np.isfinite(sret)
    out = pd.DataFrame(dict(
        date=idx[sub].get_level_values("quote_date"), t=entry_t, kind=kind, wing=wing,
        sdelta=short_delta if short_delta is not None else np.nan,
        kc=kc, kp=kp, kcl=kcl_a, kpl=kpl_a, credit=credit, entry_cost=entry_cost,
        width=width, risk=risk, pay=pay, sret=sret, iv=iv))[ok]
    out["pnl_mid"] = out.credit - out.pay
    out["pnl_net"] = out.credit - out.entry_cost - out.pay          # cash-settled, no exit cost
    out["pnl_rt"] = out.credit - 2 * out.entry_cost - out.pay        # if you close the position
    for c in ["pnl_mid", "pnl_net", "pnl_rt"]:
        out[c + "_r"] = 100 * out[c] / out.risk
    out["credit_pct_width"] = 100 * out.credit / out.width
    out["cost_pct_credit"] = 100 * out.entry_cost / out.credit
    out["rt_pct_credit"] = 200 * out.entry_cost / out.credit
    return out


def summarise(o):
    if o is None or len(o) < 30:
        return None
    d = dict(n=len(o),
             credit_bp=round(1e4 * o.credit.mean(), 1),
             width_bp=round(1e4 * o.width.mean(), 1),
             cr_pct_w=round(o.credit_pct_width.mean(), 1),
             entry_cost_bp=round(1e4 * o.entry_cost.mean(), 2),
             ENTRY_pct_credit=round(o.cost_pct_credit.median(), 1),
             RT_pct_credit=round(o.rt_pct_credit.median(), 1),
             win=round(100 * (o.pnl_net > 0).mean(), 1))
    for lbl, c in [("mid", "pnl_mid_r"), ("net", "pnl_net_r"), ("rt", "pnl_rt_r")]:
        d[lbl] = round(o[c].mean(), 2)
        d["t_" + lbl] = round(st.ttest_1samp(o[c], 0).statistic, 2)
    d["worst"] = round(o.pnl_net_r.min(), 0)
    d["p05"] = round(o.pnl_net_r.quantile(0.05), 0)
    return d


rows = []
pd.set_option("display.width", 250)
rows = []
rows = []


def main():
    # these were module-level before the guard; the functions above
    # still read them, so they stay global — only the work moved.
    global BAS_C
    global BAS_P
    global DLT_C
    global DLT_P
    global GRID
    global IVATM
    global MID_C
    global MID_P
    global SRET
    global df
    global idx

    print("loading...")
    df = pd.read_parquet(paths.require_data(PATH), columns=[
        "quote_date", "quote_time", "option_type", "mnes_rel", "mid", "bas", "delta",
        "implied_volatility", "sret", "active_underlying_price", "open_interest"])
    df["t"] = df.quote_time.astype(str)
    df = df[df.t.isin(TIMES)]
    df = df[(df.mid > 0) & (df.bas > 0)]
    print("rows", len(df), "sessions", df.quote_date.nunique())

    MID_C, MID_P = wide("mid", "C"), wide("mid", "P")
    BAS_C, BAS_P = wide("bas", "C"), wide("bas", "P")
    DLT_C, DLT_P = wide("delta", "C"), wide("delta", "P")
    SRET = df.groupby(["quote_date", "t"]).sret.first()
    IVATM = df[np.isclose(df.mnes_rel, 1.0) & (df.option_type == "C")].set_index(["quote_date", "t"]).implied_volatility

    GRID = np.array(MID_C.columns, dtype=float)
    idx = MID_C.index
    print("panel", MID_C.shape)

    # =============================================================================
    # 1. RAW LIQUIDITY: half-spread per leg as % of that leg's mid, by moneyness
    # =============================================================================
    print("\n" + "=" * 78)
    print("1. QUOTED SPREAD BY MONEYNESS (real SPXW 0DTE, all sessions, all listed times)")
    print("=" * 78)
    liq = df.copy()
    liq["half_pct_of_mid"] = 100 * 0.5 * liq.bas / liq.mid
    liq["half_bp_of_spot"] = 1e4 * 0.5 * liq.bas
    liq["otm"] = np.where(liq.option_type == "C", liq.mnes_rel - 1, 1 - liq.mnes_rel)
    liq["bucket"] = pd.cut(liq.otm, [-0.021, -0.005, -0.001, 0.001, 0.005, 0.010, 0.021],
                           labels=["ITM>0.5%", "ITM 0.1-0.5%", "ATM +-0.1%", "OTM 0.1-0.5%",
                                   "OTM 0.5-1.0%", "OTM 1.0-2.0%"])
    g = liq.groupby("bucket", observed=True).agg(
        n=("mid", "size"), mid_bp_spot=("mid", lambda x: 1e4 * x.mean()),
        half_bp_spot=("half_bp_of_spot", "mean"),
        half_pct_of_mid_mean=("half_pct_of_mid", "mean"),
        half_pct_of_mid_med=("half_pct_of_mid", "median"))
    print(g.round(2).to_string())

    print("\nhalf-spread in bp of SPOT by entry time (ATM +-0.1% only):")
    atmliq = liq[liq.bucket == "ATM +-0.1%"]
    print(atmliq.groupby("t").agg(n=("mid", "size"), half_bp_spot=("half_bp_of_spot", "mean"),
                                  half_pct_mid=("half_pct_of_mid", "mean")).round(2).to_string())
    print("\nsame, by year (ATM):")
    atmliq = atmliq.assign(yr=atmliq.quote_date.dt.year)
    print(atmliq.groupby("yr").agg(n=("mid", "size"), half_bp_spot=("half_bp_of_spot", "mean"),
                                   half_pct_mid=("half_pct_of_mid", "mean")).round(2).to_string())

    print("\n" + "=" * 78)
    print("2. IRON BUTTERFLY (short ATM straddle + wings), REAL quotes, hold to cash settlement")
    print("=" * 78)
    print("cr_pct_w = credit as % of wing width | ENTRY_pct_credit = 4 half-spreads as % of mid credit")
    print("RT_pct_credit = 8 half-spreads (open+close) as % of credit | returns are % of capital at risk\n")

    for t in TIMES:
        for w in [0.003, 0.005, 0.008, 0.010, 0.015, 0.020]:
            o = run_structure("fly", t, w)
            s = summarise(o)
            if s:
                rows.append(dict(t=t, wing=f"{w*100:.1f}%", **s))
    fly = pd.DataFrame(rows)

    print(fly.to_string(index=False))

    print("\n" + "=" * 78)
    print("3. IRON CONDOR by short-strike DELTA, REAL quotes, hold to cash settlement")
    print("=" * 78)

    for t in ["10:00:00", "10:30:00", "11:00:00", "12:00:00", "13:00:00"]:
        for sd in [0.10, 0.16, 0.30]:
            for w in [0.005, 0.010]:
                o = run_structure("condor", t, w, short_delta=sd)
                s = summarise(o)
                if s:
                    rows.append(dict(t=t, delta=sd, wing=f"{w*100:.1f}%", **s))
    cnd = pd.DataFrame(rows)
    print(cnd.to_string(index=False))

    # =============================================================================
    # 4. THE 0DTE ATM STRADDLE VRP ON REAL QUOTES
    # =============================================================================
    print("\n" + "=" * 78)
    print("4. 0DTE ATM STRADDLE: mid premium vs realised move (the raw VRP, real quotes)")
    print("=" * 78)

    for t in TIMES:
        m = idx.get_level_values("t") == t
        sub = np.where(m)[0]
        j = int(np.argmin(np.abs(GRID - 1.0)))
        prem = MID_C.values[sub, j] + MID_P.values[sub, j]
        half = 0.5 * (BAS_C.values[sub, j] + BAS_P.values[sub, j])
        sret = SRET.iloc[sub].values
        real = np.abs(sret - 1.0)
        ok = np.isfinite(prem) & np.isfinite(real) & (prem > 0)
        prem, real, half = prem[ok], real[ok], half[ok]
        edge = prem - real                       # short straddle P&L at mid
        edge_net = prem - half - real            # after crossing 2 legs on entry
        rows.append(dict(t=t, n=len(prem), straddle_bp=round(1e4 * prem.mean(), 1),
                         realised_bp=round(1e4 * real.mean(), 1),
                         ratio_real_over_imp=round(real.mean() / prem.mean(), 3),
                         short_mid_bp=round(1e4 * edge.mean(), 1),
                         t_mid=round(st.ttest_1samp(edge, 0).statistic, 2),
                         half_spread_bp=round(1e4 * half.mean(), 2),
                         short_net_bp=round(1e4 * edge_net.mean(), 1),
                         t_net=round(st.ttest_1samp(edge_net, 0).statistic, 2),
                         pct_of_prem_eaten=round(100 * half.mean() / prem.mean(), 1)))
    print(pd.DataFrame(rows).to_string(index=False))

    # save the 11:00 butterfly + condor trade tapes for the tail / regime section
    o1 = run_structure("fly", "11:00:00", 0.010)
    o2 = run_structure("condor", "11:00:00", 0.010, short_delta=0.16)
    # These tapes went to the /private/tmp scratchpad of the session that wrote this
    # file. That directory is long gone, so the script did twenty minutes of work and
    # then died on its last two lines. Keep them beside the data they came from.
    tape = paths.data("scratch")
    os.makedirs(tape, exist_ok=True)
    o1.to_parquet(os.path.join(tape, "fly1100.parquet"))
    o2.to_parquet(os.path.join(tape, "cnd1100.parquet"))
    print("\nsaved trade tapes.")


if __name__ == "__main__":
    main()
