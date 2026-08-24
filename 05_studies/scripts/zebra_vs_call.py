"""
ZEBRA vs a plain 0.80-delta call vs ATM call vs 100 shares — head to head,
normalised to the SAME 100 deltas of SPY exposure, real fills.

Design notes that matter (these are the traps that contaminate this comparison):
  * Entry crosses the spread: longs pay ASK, shorts receive BID.
  * Held to EXPIRATION and settled at INTRINSIC. This deliberately removes any
    dependence on an exit chain, so no "worthless option missing from the exit
    snapshot" survivorship bug is possible. A contract that expires worthless
    settles at exactly $0 and is counted.
  * The early-exit variant marks every leg from the exit chain and treats a
    MISSING or ZERO-BID long leg as $0.00 proceeds rather than dropping the
    trade. Dropping them is what manufactures fake 100% win rates.
  * Everything is scaled to 100 deltas so the four expressions are compared on
    equal directional exposure. The difference between them is then pure
    cost / decay / convexity, and a paired t-test on the same dates is valid.
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

OPT = "opt_eod/SPY_options.parquet"  # path under DATA_ROOT, resolved at the read site
UND = "opt_eod/SPY_underlying.parquet"
COLS = ["date", "expiration", "strike", "type", "bid", "ask", "delta",
        "open_interest", "implied_volatility"]
SHARE_HALF = 0.005


def bydelta(c, d):
    return c.iloc[(c.delta.abs() - d).abs().argmin()] if len(c) else None


def main():
    und = pd.read_parquet(paths.require_data(UND))[["date", "close"]]
    und["date"] = pd.to_datetime(und.date)
    und = und.set_index("date")["close"].sort_index()

    df = pq.read_table(paths.require_data(OPT), columns=COLS).to_pandas()
    df = df[(df.bid > 0) & (df.ask > df.bid) & (df.open_interest > 10)].copy()
    df["dte"] = (df.expiration - df.date).dt.days
    print(f"usable rows: {len(df):,}")

    alld = pd.to_datetime(pd.Series(sorted(df.date.unique())))
    # weekly entries (every Monday-ish) for a larger sample than month-start
    weekly = alld.groupby([alld.dt.isocalendar().year, alld.dt.isocalendar().week]).min().to_list()

    rows = []
    for bucket, lo, hi in [("35d", 25, 45), ("90d", 75, 110)]:
        for t0 in weekly:
            day = df[(df.date == t0) & (df.dte >= lo) & (df.dte <= hi)]
            if day.empty:
                continue
            exp = day.groupby("expiration").size().idxmax()
            calls = day[(day.expiration == exp) & (day.type == "call")]
            if len(calls) < 20:
                continue
            S0 = und.get(t0, np.nan)
            ST = und.asof(exp)
            if not (np.isfinite(S0) and np.isfinite(ST)):
                continue

            z_in = bydelta(calls, 0.75)     # 2 long
            z_out = bydelta(calls, 0.50)    # 1 short (ATM)
            c80 = bydelta(calls, 0.80)
            catm = z_out
            if z_in is None or z_out is None or c80 is None:
                continue
            if not (z_in.strike < z_out.strike):
                continue

            def intr(K):
                return max(ST - K, 0.0)

            # ---- ZEBRA: +2 x 0.75d, -1 x ATM ----
            z_cost = (2 * z_in.ask - z_out.bid) * 100
            z_settle = (2 * intr(z_in.strike) - intr(z_out.strike)) * 100
            z_delta = 2 * z_in.delta - z_out.delta
            z_spread = (2 * (z_in.ask - z_in.bid) + (z_out.ask - z_out.bid)) * 100
            z_ext = (2 * (((z_in.bid + z_in.ask) / 2) - max(S0 - z_in.strike, 0))
                     - (((z_out.bid + z_out.ask) / 2) - max(S0 - z_out.strike, 0))) * 100

            # ---- plain 0.80-delta call ----
            c_cost = c80.ask * 100
            c_settle = intr(c80.strike) * 100
            c_delta = c80.delta
            c_spread = (c80.ask - c80.bid) * 100
            c_ext = (((c80.bid + c80.ask) / 2) - max(S0 - c80.strike, 0)) * 100

            # ---- ATM call ----
            a_cost = catm.ask * 100
            a_settle = intr(catm.strike) * 100
            a_delta = catm.delta
            a_spread = (catm.ask - catm.bid) * 100
            a_ext = (((catm.bid + catm.ask) / 2) - max(S0 - catm.strike, 0)) * 100

            # ---- normalise everything to 100 deltas ----
            def norm(cost, settle, dlt, spread, ext):
                k = 1.0 / dlt                      # contracts per 100 deltas
                return dict(cost=k * cost, pnl=k * (settle - cost),
                            spread=k * spread, ext=k * ext)

            sh_pnl = 100 * (ST - S0) - 1.00        # 100 shares, penny round trip

            for name, vals in [("ZEBRA", norm(z_cost, z_settle, z_delta, z_spread, z_ext)),
                               ("call_80d", norm(c_cost, c_settle, c_delta, c_spread, c_ext)),
                               ("call_ATM", norm(a_cost, a_settle, a_delta, a_spread, a_ext))]:
                rows.append(dict(bucket=bucket, date=t0, exp=exp, S0=S0, ST=ST,
                                 ret_und=ST / S0 - 1, structure=name,
                                 shares_pnl=sh_pnl, **vals))
            rows.append(dict(bucket=bucket, date=t0, exp=exp, S0=S0, ST=ST,
                             ret_und=ST / S0 - 1, structure="shares_100",
                             cost=100 * S0, pnl=sh_pnl, spread=1.00, ext=0.0,
                             shares_pnl=sh_pnl))

    res = pd.DataFrame(rows)
    res.to_parquet(paths.data("zebra_vs_call.parquet"))
    pd.set_option("display.width", 220)

    for bucket in ["35d", "90d"]:
        r = res[res.bucket == bucket]
        if r.empty:
            continue
        n = r.date.nunique()
        print(f"\n{'='*118}\nHELD TO EXPIRY, normalised to 100 SPY deltas — {bucket} (n = {n} weekly entries, "
              f"{r.date.min().date()} to {r.date.max().date()})\n{'='*118}")
        g = r.groupby("structure").agg(
            n=("pnl", "size"),
            capital=("cost", "median"),
            entry_spread=("spread", "median"),
            extrinsic=("ext", "median"),
            mean_pnl=("pnl", "mean"),
            median_pnl=("pnl", "median"),
            win=("pnl", lambda x: 100 * (x > 0).mean()),
            worst=("pnl", "min"),
        )
        g["spread_%_of_capital"] = 100 * g.entry_spread / g.capital
        print(g.round(2).to_string())

        # paired difference: ZEBRA minus 0.80-delta call, same dates
        piv = r.pivot_table(index="date", columns="structure", values="pnl")
        piv = piv.dropna()
        if {"ZEBRA", "call_80d"}.issubset(piv.columns):
            d = piv["ZEBRA"] - piv["call_80d"]
            t = d.mean() / (d.std() / np.sqrt(len(d)))
            print(f"\nPAIRED: ZEBRA − 0.80d call, per 100 deltas, n={len(d)}")
            print("  mean difference : $%+.2f per trade   t = %+.2f" % (d.mean(), t))
            print("  median          : $%+.2f" % d.median())
            print("  ZEBRA better on : %.0f%% of entries" % (100 * (d > 0).mean()))
            ds = piv["ZEBRA"] - piv["shares_100"]
            ts = ds.mean() / (ds.std() / np.sqrt(len(ds)))
            print("  ZEBRA − shares  : $%+.2f  t = %+.2f  (ZEBRA better %.0f%%)"
                  % (ds.mean(), ts, 100 * (ds > 0).mean()))
            dc = piv["call_80d"] - piv["shares_100"]
            print("  0.80d − shares  : $%+.2f  (call better %.0f%%)"
                  % (dc.mean(), 100 * (dc > 0).mean()))

        # conditional on direction: does ZEBRA's convexity help or hurt?
        r2 = r.pivot_table(index="date", columns="structure", values="pnl").dropna()
        ru = r.groupby("date").ret_und.first().reindex(r2.index)
        print("\n  by underlying outcome (mean $ per 100 deltas):")
        buckets = pd.cut(ru, [-1, -0.05, -0.02, 0.02, 0.05, 1],
                         labels=["<-5%", "-5..-2%", "-2..+2%", "+2..+5%", ">+5%"])
        tab = r2.groupby(buckets, observed=True).mean().round(0)
        tab["n"] = r2.groupby(buckets, observed=True).size()
        print(tab.to_string())


if __name__ == "__main__":
    main()
