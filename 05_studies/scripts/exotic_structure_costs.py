"""
Empirical cost measurement for exotic / multi-leg option structures.

Uses real SPY end-of-day bid/ask chains (2008-2025, 24.7M rows) to answer one
question honestly: how much of the credit/debit does a retail trader hand to the
market maker just to get in and out of each structure?

Round-trip spread cost for a structure is exactly:
    RT = sum_i |qty_i| * (ask_i - bid_i)
because entry pays ask on longs / receives bid on shorts, and exit reverses.
This isolates pure friction from P&L (same quote snapshot both ways).

We report RT as a % of (a) the mid-price credit/debit and (b) max risk, which is
the number that actually matters for a small account.
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc

from idt import paths

OPT = "opt_eod/SPY_options.parquet"  # path under DATA_ROOT, resolved at the read site
UND = "opt_eod/SPY_underlying.parquet"

COLS = ["date", "expiration", "strike", "type", "bid", "ask",
        "delta", "gamma", "theta", "vega", "implied_volatility",
        "open_interest", "volume"]


def load(sample_dates):
    tbl = pq.read_table(paths.require_data(OPT), columns=COLS,
                        filters=[("date", "in", list(sample_dates))])
    df = tbl.to_pandas()
    df = df[(df.bid > 0) & (df.ask > df.bid) & (df.open_interest > 0)].copy()
    df["mid"] = (df.bid + df.ask) / 2
    df["spread"] = df.ask - df.bid
    df["dte"] = (df.expiration - df.date).dt.days
    return df


def pick_by_moneyness(chain, opt_type, S, pct):
    """Nearest strike to S*(1+pct)."""
    c = chain[chain.type == opt_type]
    if c.empty:
        return None
    tgt = S * (1 + pct)
    return c.iloc[(c.strike - tgt).abs().argmin()]


def pick_by_delta(chain, opt_type, target_delta):
    c = chain[chain.type == opt_type]
    if c.empty:
        return None
    return c.iloc[(c.delta.abs() - abs(target_delta)).abs().argmin()]


def leg_stats(legs):
    """legs = list of (qty, row). qty>0 long. Returns dict of aggregates."""
    mid = sum(q * r.mid for q, r in legs)          # >0 = net debit
    rt = sum(abs(q) * r.spread for q, r in legs)   # round-trip spread cost
    entry_half = sum(abs(q) * r.spread / 2 for q, r in legs)
    delta = sum(q * r.delta for q, r in legs)
    gamma = sum(q * r.gamma for q, r in legs)
    theta = sum(q * r.theta for q, r in legs)
    vega = sum(q * r.vega for q, r in legs)
    return dict(mid=mid, rt=rt, entry_half=entry_half,
                delta=delta, gamma=gamma, theta=theta, vega=vega,
                nlegs=len(legs), ncontracts=sum(abs(q) for q, r in legs))


def build_structures(chain, S):
    """Return {name: (legs, max_risk, note)} for one date/expiry chain."""
    out = {}

    # ---- 1. Broken-wing butterfly (call, upside), body 2%, near wing skipped,
    #         far wing pushed out so the structure is opened for a credit.
    b1 = pick_by_moneyness(chain, "call", S, 0.00)   # long lower
    b2 = pick_by_moneyness(chain, "call", S, 0.02)   # short body x2
    b3 = pick_by_moneyness(chain, "call", S, 0.035)  # long upper (narrower wing)
    if all(x is not None for x in (b1, b2, b3)) and b1.strike < b2.strike < b3.strike:
        legs = [(1, b1), (-2, b2), (1, b3)]
        st = leg_stats(legs)
        lower_w = b2.strike - b1.strike
        upper_w = b3.strike - b2.strike
        # max risk = wider-side width - credit (or + debit)
        max_risk = max(lower_w, upper_w) * 100 + st["mid"] * 100
        out["broken_wing_butterfly"] = (legs, max_risk,
                                        f"{b1.strike}/{b2.strike}x2/{b3.strike}")

    # ---- 2. Christmas tree (call 1-3-2)
    c1 = pick_by_moneyness(chain, "call", S, 0.00)
    c2 = pick_by_moneyness(chain, "call", S, 0.03)
    c3 = pick_by_moneyness(chain, "call", S, 0.045)
    if all(x is not None for x in (c1, c2, c3)) and c1.strike < c2.strike < c3.strike:
        legs = [(1, c1), (-3, c2), (2, c3)]
        st = leg_stats(legs)
        # payoff is capped above (2 longs vs 3 shorts nets +... ) -> compute grid
        max_risk = payoff_max_risk(legs, S, st["mid"])
        out["christmas_tree_132"] = (legs, max_risk,
                                     f"{c1.strike}/{c2.strike}x3/{c3.strike}x2")

    # ---- 3. Jade lizard: short put (-5%), short call spread (+2% / +4%)
    p1 = pick_by_delta(chain, "put", 0.20)
    k1 = pick_by_delta(chain, "call", 0.25)
    k2 = pick_by_moneyness(chain, "call", S, 0.04)
    if all(x is not None for x in (p1, k1, k2)) and k2.strike > k1.strike:
        legs = [(-1, p1), (-1, k1), (1, k2)]
        st = leg_stats(legs)
        credit = -st["mid"]
        max_risk = p1.strike * 100 - credit * 100  # naked put side, to zero
        out["jade_lizard"] = (legs, max_risk,
                              f"-{p1.strike}P / -{k1.strike}C +{k2.strike}C")

    # ---- 4. Twisted sister: short call, short put spread
    k3 = pick_by_delta(chain, "call", 0.20)
    p2 = pick_by_delta(chain, "put", 0.25)
    p3 = pick_by_moneyness(chain, "put", S, -0.04)
    if all(x is not None for x in (k3, p2, p3)) and p3.strike < p2.strike:
        legs = [(-1, k3), (-1, p2), (1, p3)]
        st = leg_stats(legs)
        max_risk = np.nan  # unbounded upside
        out["twisted_sister"] = (legs, max_risk,
                                 f"-{k3.strike}C / -{p2.strike}P +{p3.strike}P")

    # ---- 5. ZEBRA: long 2x ~0.75d ITM call, short 1x ATM call
    z1 = pick_by_delta(chain, "call", 0.75)
    z2 = pick_by_delta(chain, "call", 0.50)
    if z1 is not None and z2 is not None and z1.strike < z2.strike:
        legs = [(2, z1), (-1, z2)]
        st = leg_stats(legs)
        max_risk = st["mid"] * 100
        out["zebra"] = (legs, max_risk, f"+2x{z1.strike}C -1x{z2.strike}C")

    # ---- 5b. benchmark: single 0.80-delta call
    d80 = pick_by_delta(chain, "call", 0.80)
    if d80 is not None:
        legs = [(1, d80)]
        st = leg_stats(legs)
        out["single_80d_call"] = (legs, st["mid"] * 100, f"+{d80.strike}C")

    # ---- 5c. benchmark: ATM long call
    if z2 is not None:
        legs = [(1, z2)]
        out["single_atm_call"] = (legs, z2.mid * 100, f"+{z2.strike}C")

    # ---- 6. Gamma scalping: ATM straddle (option leg cost only)
    sp = pick_by_delta(chain, "put", 0.50)
    if z2 is not None and sp is not None:
        legs = [(1, z2), (1, sp)]
        st = leg_stats(legs)
        out["atm_straddle"] = (legs, st["mid"] * 100,
                               f"+{z2.strike}C +{sp.strike}P")

    # ---- 7. Box spread: long call spread + long put spread, same strikes
    bk1 = pick_by_moneyness(chain, "call", S, -0.02)
    bk2 = pick_by_moneyness(chain, "call", S, 0.02)
    bp1 = chain[(chain.type == "put") & (chain.strike == bk1.strike)] if bk1 is not None else None
    bp2 = chain[(chain.type == "put") & (chain.strike == bk2.strike)] if bk2 is not None else None
    if (bk1 is not None and bk2 is not None and bp1 is not None and bp2 is not None
            and len(bp1) and len(bp2) and bk1.strike < bk2.strike):
        bp1, bp2 = bp1.iloc[0], bp2.iloc[0]
        # long box: +C(K1) -C(K2) +P(K2) -P(K1)  -> pays (K2-K1) at expiry
        legs = [(1, bk1), (-1, bk2), (1, bp2), (-1, bp1)]
        out["box_spread"] = (legs, 0.0,
                             f"K1={bk1.strike} K2={bk2.strike} W={bk2.strike-bk1.strike}")
    return out


def payoff_max_risk(legs, S, mid):
    """Numeric max loss over a wide terminal price grid, per 1 spread ($)."""
    grid = np.linspace(S * 0.5, S * 1.8, 4000)
    pay = np.zeros_like(grid)
    for q, r in legs:
        if r.type == "call":
            pay += q * np.maximum(grid - r.strike, 0)
        else:
            pay += q * np.maximum(r.strike - grid, 0)
    pnl = (pay - mid) * 100
    return -pnl.min()


def main():
    und = pd.read_parquet(paths.require_data(UND))[["date", "close"]]
    und["date"] = pd.to_datetime(und.date)
    und = und.set_index("date")["close"]

    all_dates = pd.Series(pq.read_table(paths.require_data(OPT), columns=["date"]).column("date").to_pandas().unique())
    all_dates = pd.to_datetime(pd.Series(sorted(all_dates)))
    all_dates = all_dates[all_dates >= "2018-01-01"]
    # first trading day of each month
    sample = all_dates.groupby([all_dates.dt.year, all_dates.dt.month]).min().to_list()
    print(f"sampling {len(sample)} month-start dates {sample[0].date()} .. {sample[-1].date()}")

    df = load(sample)
    print(f"loaded {len(df):,} option rows")

    rows = []
    for dt, day in df.groupby("date"):
        S = und.get(dt, np.nan)
        if not np.isfinite(S):
            continue
        # short-dated book (~35 DTE) for premium structures & box
        for tag, lo, hi in [("35d", 25, 45), ("90d", 75, 110)]:
            sub = day[(day.dte >= lo) & (day.dte <= hi)]
            if sub.empty:
                continue
            # single expiration with most contracts
            exp = sub.groupby("expiration").size().idxmax()
            chain = sub[sub.expiration == exp]
            if len(chain) < 40:
                continue
            for name, (legs, max_risk, note) in build_structures(chain, S).items():
                st = leg_stats(legs)
                rows.append(dict(date=dt, dte_bucket=tag, S=S,
                                 expiration=exp, structure=name, note=note,
                                 max_risk=max_risk, **st))
    res = pd.DataFrame(rows)
    res.to_parquet(paths.data("exotic_structure_costs.parquet"))

    pd.set_option("display.width", 220)
    for tag in ["35d", "90d"]:
        r = res[res.dte_bucket == tag]
        if r.empty:
            continue
        print(f"\n{'='*110}\nDTE bucket: {tag}   (n dates = {r.date.nunique()})\n{'='*110}")
        g = r.groupby("structure").agg(
            n=("mid", "size"),
            contracts=("ncontracts", "median"),
            mid_usd=("mid", lambda x: 100 * x.median()),
            rt_cost_usd=("rt", lambda x: 100 * x.median()),
            max_risk_usd=("max_risk", "median"),
            delta=("delta", "median"),
            gamma=("gamma", "median"),
            theta=("theta", "median"),
            vega=("vega", "median"),
        )
        g["rt_pct_of_mid"] = 100 * g["rt_cost_usd"] / g["mid_usd"].abs()
        g["rt_pct_of_risk"] = 100 * g["rt_cost_usd"] / g["max_risk_usd"]
        print(g.round(2).to_string())

    # ---- Box spread implied financing rate: mid vs crossing the spread
    box = res[(res.structure == "box_spread")].copy()
    if not box.empty:
        # width from note
        box["W"] = box.note.str.extract(r"W=([\d.]+)").astype(float)
        box["T"] = (box.expiration - box.date).dt.days / 365.0
        # long box: pay `mid` now, receive W at expiry
        box["rate_mid"] = (box.W / box["mid"]) ** (1 / box["T"]) - 1
        box["cost_nat"] = box["mid"] + box["rt"] / 2   # pay half-spread each leg on entry
        box["rate_nat"] = (box.W / box["cost_nat"]) ** (1 / box["T"]) - 1
        print(f"\n{'='*110}\nBOX SPREAD implied lending rate (SPY, ~35 DTE, n={len(box)})\n{'='*110}")
        print(box[["rate_mid", "rate_nat"]].describe(percentiles=[.1, .5, .9]).round(4).to_string())
        print("\nmedian rate at MID      : %.2f%%" % (100 * box.rate_mid.median()))
        print("median rate CROSSING    : %.2f%%" % (100 * box.rate_nat.median()))
        print("median drag from spread : %.2f pct points" %
              (100 * (box.rate_mid.median() - box.rate_nat.median())))
        print("median round-trip spread cost $: %.2f on width $%.0f" %
              (100 * box.rt.median(), 100 * box.W.median()))


if __name__ == "__main__":
    main()
