"""
Tests the specific HEADLINE CLAIMS made about each exotic structure, on real SPY
end-of-day chains (month-start entries, ~35 DTE, 2018-2025).

Claims under test:
  BWB     : "opened for a credit -> risk completely eliminated on one side"
  JADE    : "no upside risk when credit > call-spread width"  (is it achievable?)
  ZEBRA   : "zero extrinsic value, zero theta, mimics stock"
  ALL     : round-trip spread cost as a share of MAX PROFIT, not just of credit
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

OPT = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_options.parquet"
UND = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_underlying.parquet"
COLS = ["date", "expiration", "strike", "type", "bid", "ask", "delta", "gamma",
        "theta", "vega", "implied_volatility", "open_interest"]


def payoff_curve(legs, grid):
    pay = np.zeros_like(grid)
    for q, r in legs:
        if r.type == "call":
            pay += q * np.maximum(grid - r.strike, 0)
        else:
            pay += q * np.maximum(r.strike - grid, 0)
    return pay


def bounds(legs, mid, S):
    grid = np.linspace(1.0, S * 2.5, 8000)
    pnl = (payoff_curve(legs, grid) - mid) * 100
    return -pnl.min(), pnl.max()


def stats(legs):
    return dict(
        mid=sum(q * r.mid for q, r in legs),
        rt=sum(abs(q) * r.spread for q, r in legs),
        delta=sum(q * r.delta for q, r in legs),
        gamma=sum(q * r.gamma for q, r in legs),
        theta=sum(q * r.theta for q, r in legs),
        vega=sum(q * r.vega for q, r in legs),
        ncon=sum(abs(q) for q, r in legs),
    )


def near(c, S, pct):
    return c.iloc[(c.strike - S * (1 + pct)).abs().argmin()] if len(c) else None


def bydelta(c, d):
    return c.iloc[(c.delta.abs() - d).abs().argmin()] if len(c) else None


def main():
    und = pd.read_parquet(UND)[["date", "close"]]
    und["date"] = pd.to_datetime(und.date)
    und = und.set_index("date")["close"]

    alld = pd.to_datetime(pd.Series(sorted(
        pq.read_table(OPT, columns=["date"]).column("date").to_pandas().unique())))
    alld = alld[alld >= "2018-01-01"]
    sample = alld.groupby([alld.dt.year, alld.dt.month]).min().to_list()

    df = pq.read_table(OPT, columns=COLS,
                       filters=[("date", "in", sample)]).to_pandas()
    df = df[(df.bid > 0) & (df.ask > df.bid) & (df.open_interest > 10)].copy()
    df["mid"] = (df.bid + df.ask) / 2
    df["spread"] = df.ask - df.bid
    df["dte"] = (df.expiration - df.date).dt.days

    rows, jade_rows, zeb_rows = [], [], []
    for dt, day in df.groupby("date"):
        S = und.get(dt, np.nan)
        if not np.isfinite(S):
            continue
        sub = day[(day.dte >= 25) & (day.dte <= 45)]
        if sub.empty:
            continue
        exp = sub.groupby("expiration").size().idxmax()
        ch = sub[sub.expiration == exp]
        calls, puts = ch[ch.type == "call"], ch[ch.type == "put"]
        if len(calls) < 20 or len(puts) < 20:
            continue

        def add(name, legs, extra=None):
            st = stats(legs)
            mr, mp = bounds(legs, st["mid"], S)
            rows.append(dict(date=dt, structure=name, S=S, **st,
                             max_risk=mr, max_profit=mp, **(extra or {})))

        # ---------- CREDIT broken-wing butterfly (put side, bullish) ----------
        # long 1 near-ATM put, short 2 mid puts, long 1 far OTM put
        h = near(puts, S, -0.01)
        m = near(puts, S, -0.04)
        lo = near(puts, S, -0.12)
        if h is not None and m is not None and lo is not None and lo.strike < m.strike < h.strike:
            add("BWB_credit_put", [(1, h), (-2, m), (1, lo)],
                dict(note=f"+{h.strike}/-2x{m.strike}/+{lo.strike}",
                     wide=m.strike - lo.strike, narrow=h.strike - m.strike))

        # ---------- DEBIT broken-wing butterfly (call side) ----------
        a = near(calls, S, 0.00); b = near(calls, S, 0.02); c3 = near(calls, S, 0.035)
        if a is not None and b is not None and c3 is not None and a.strike < b.strike < c3.strike:
            add("BWB_debit_call", [(1, a), (-2, b), (1, c3)],
                dict(note=f"{a.strike}/{b.strike}x2/{c3.strike}"))

        # ---------- Christmas tree 1-3-2 (calls) ----------
        t1 = near(calls, S, 0.00); t2 = near(calls, S, 0.03); t3 = near(calls, S, 0.045)
        if t1 is not None and t2 is not None and t3 is not None and t1.strike < t2.strike < t3.strike:
            add("XMAS_tree_132", [(1, t1), (-3, t2), (2, t3)],
                dict(note=f"{t1.strike}/{t2.strike}x3/{t3.strike}x2"))

        # ---------- Iron condor benchmark (16d/5-wide) ----------
        sc = bydelta(calls, 0.16); sp_ = bydelta(puts, 0.16)
        lc = calls[calls.strike > sc.strike]
        lp = puts[puts.strike < sp_.strike]
        if len(lc) and len(lp):
            lc = lc.iloc[(lc.strike - (sc.strike + 5)).abs().argmin()]
            lp = lp.iloc[(lp.strike - (sp_.strike - 5)).abs().argmin()]
            add("iron_condor_16d", [(-1, sc), (1, lc), (-1, sp_), (1, lp)])

        # ---------- JADE LIZARD: is "no upside risk" achievable? ----------
        jp = bydelta(puts, 0.20)
        jc = bydelta(calls, 0.25)
        if jp is not None and jc is not None:
            wider = calls[calls.strike > jc.strike].sort_values("strike")
            base_credit = jp.mid + jc.mid
            best = None
            for _, lc2 in wider.iterrows():
                w = lc2.strike - jc.strike
                credit = base_credit - lc2.mid
                credit_nat = jp.bid + jc.bid - lc2.ask     # what you actually get
                if credit >= w:
                    best = (lc2, w, credit, credit_nat)
            widest_ok = best
            # also: the narrowest available spread, as the realistic construction
            nrw = wider.iloc[0] if len(wider) else None
            if nrw is not None:
                w0 = nrw.strike - jc.strike
                cr0 = base_credit - nrw.mid
                cr0n = jp.bid + jc.bid - nrw.ask
                jade_rows.append(dict(
                    date=dt, S=S, put_K=jp.strike, call_K=jc.strike,
                    narrow_w=w0, narrow_credit=cr0, narrow_credit_nat=cr0n,
                    narrow_ok_mid=cr0 >= w0, narrow_ok_nat=cr0n >= w0,
                    any_ok=widest_ok is not None,
                    best_w=widest_ok[1] if widest_ok else np.nan,
                    best_credit=widest_ok[2] if widest_ok else np.nan,
                    best_ok_nat=(widest_ok[3] >= widest_ok[1]) if widest_ok else False,
                    naked_put_risk=jp.strike * 100 - cr0 * 100,
                    rt=(jp.spread + jc.spread + nrw.spread)))

        # ---------- ZEBRA: zero extrinsic? ----------
        z1 = bydelta(calls, 0.75); z2 = bydelta(calls, 0.50)
        d80 = bydelta(calls, 0.80)
        if z1 is not None and z2 is not None and z1.strike < z2.strike:
            legs = [(2, z1), (-1, z2)]
            st = stats(legs)
            ext_z = 2 * max(z1.mid - max(S - z1.strike, 0), 0) - max(z2.mid - max(S - z2.strike, 0), 0)
            add("ZEBRA", legs, dict(note=f"+2x{z1.strike} -1x{z2.strike}", extrinsic=ext_z))
            zeb_rows.append(dict(date=dt, S=S, ext=ext_z, cost=st["mid"],
                                 delta=st["delta"], theta=st["theta"],
                                 gamma=st["gamma"], vega=st["vega"], rt=st["rt"]))
        if d80 is not None:
            ext80 = d80.mid - max(S - d80.strike, 0)
            add("call_80delta", [(1, d80)], dict(extrinsic=ext80))
        if z2 is not None:
            add("call_ATM", [(1, z2)], dict(extrinsic=z2.mid - max(S - z2.strike, 0)))

    res = pd.DataFrame(rows)
    pd.set_option("display.width", 240)

    print(f"\n{'='*130}\nSTRUCTURE ECONOMICS — SPY, ~35 DTE, month-start 2018-2025 (n dates = {res.date.nunique()})\n{'='*130}")
    g = res.groupby("structure").agg(
        n=("mid", "size"), legs=("ncon", "median"),
        net_usd=("mid", lambda x: 100 * x.median()),
        rt_usd=("rt", lambda x: 100 * x.median()),
        maxrisk=("max_risk", "median"), maxprof=("max_profit", "median"),
        delta=("delta", "median"), gamma=("gamma", "median"),
        theta=("theta", "median"), vega=("vega", "median"))
    g["rt_%_of_maxprofit"] = 100 * g.rt_usd / g.maxprof
    g["rt_%_of_maxrisk"] = 100 * g.rt_usd / g.maxrisk
    g["risk_reward"] = g.maxrisk / g.maxprof
    print(g.round(2).to_string())

    # per-100-delta comparison
    print(f"\n{'='*130}\nDIRECTIONAL EXPRESSION: cost per 100 deltas of SPY exposure\n{'='*130}")
    dd = res[res.structure.isin(["ZEBRA", "call_80delta", "call_ATM"])].copy()
    dd["cost_per100d"] = 100 * dd.mid / dd.delta
    dd["rt_per100d"] = 100 * dd.rt / dd.delta
    dd["theta_per100d"] = 100 * dd.theta / dd.delta
    dd["vega_per100d"] = 100 * dd.vega / dd.delta
    dd["ext_per100d"] = 100 * dd.extrinsic / dd.delta
    print(dd.groupby("structure")[["cost_per100d", "rt_per100d", "theta_per100d",
                                   "vega_per100d", "ext_per100d"]].median().round(2).to_string())
    print("\nfor reference, 100 SPY shares: cost = 100*S (median $%.0f), "
          "round-trip spread = $1.00 (penny market), theta = 0, vega = 0, extrinsic = 0"
          % (100 * res.S.median()))

    # jade lizard claim
    j = pd.DataFrame(jade_rows)
    if not j.empty:
        print(f"\n{'='*130}\nJADE LIZARD — is 'credit > call-spread width' (no upside risk) actually achievable? n={len(j)}\n{'='*130}")
        print("narrowest available call spread, median width $%.1f" % j.narrow_w.median())
        print("  credit at MID >= width      : %.0f%% of dates" % (100 * j.narrow_ok_mid.mean()))
        print("  credit CROSSING >= width    : %.0f%% of dates" % (100 * j.narrow_ok_nat.mean()))
        print("  ANY width satisfies at mid  : %.0f%% of dates" % (100 * j.any_ok.mean()))
        print("  ...and still holds crossing : %.0f%% of dates" % (100 * j.best_ok_nat.mean()))
        print("median naked-put max risk     : $%.0f  (account-blowing in a $2-5k account)"
              % j.naked_put_risk.median())
        print("median credit collected       : $%.0f ; round-trip spread cost $%.0f (%.0f%% of credit)"
              % (100 * j.narrow_credit.median(), 100 * j.rt.median(),
                 100 * j.rt.median() / (100 * j.narrow_credit.median())))

    # zebra claim
    z = pd.DataFrame(zeb_rows)
    if not z.empty:
        print(f"\n{'='*130}\nZEBRA — 'zero extrinsic, zero theta' claim, n={len(z)}\n{'='*130}")
        print("median net extrinsic $ %.2f  (per 1 ZEBRA = 100 deltas); mean $%.2f; "
              "10-90 pct: $%.2f to $%.2f"
              % (100 * z.ext.median(), 100 * z.ext.mean(),
                 100 * z.ext.quantile(.1), 100 * z.ext.quantile(.9)))
        print("frac of dates with net extrinsic > $10 : %.0f%%" % (100 * (100 * z.ext > 10).mean()))
        print("median net theta  : %.3f/day  => $%.2f/day per ZEBRA" % (z.theta.median(), 100 * z.theta.median()))
        print("median net vega   : %.3f      => $%.2f per 1 vol point" % (z.vega.median(), 100 * z.vega.median()))
        print("median net gamma  : %.4f" % z.gamma.median())
        print("median net delta  : %.3f" % z.delta.median())
        print("median cost       : $%.0f ; round-trip spread $%.0f (%.1f%% of cost)"
              % (100 * z.cost.median(), 100 * z.rt.median(), 100 * z.rt.median() / z.cost.median()))

    res.to_parquet("/Users/sahilmajmudar/index-daytrading/data/exotic_claims.parquet")


if __name__ == "__main__":
    main()
