"""Part D: program-level economics of a monthly short-vol sleeve, real quotes.

Adds: realistic bid-entry for the delta-hedged short, compounded equity, max
drawdown, annualised Sharpe from non-overlapping monthly returns, and a
conditional test (does entry IV level / IV-vs-trailing-RV predict the outcome?).
"""
import sys
import numpy as np
import pandas as pd

from idt import paths

SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
DTE = int(sys.argv[2]) if len(sys.argv) > 2 else 45
UND = f"opt_eod/{SYM}_underlying.parquet"  # path under DATA_ROOT, resolved at the read site


def prog(r, label, ann=12):
    """Fixed-size (additive) equity: 1 unit of margin per trade, profits not
    reinvested. Compounding is invalid here because single trades return < -100%
    of the posted margin, which drives a geometric equity curve negative."""
    r = pd.Series(r).dropna().values
    sh = r.mean() / r.std(ddof=1) * np.sqrt(ann)
    eq = np.cumsum(r)                      # additive, in units of one margin
    dd = eq - np.maximum.accumulate(eq)
    return {"program": label, "n": len(r), "mean_%": 100 * r.mean(),
            "t": r.mean() / (r.std(ddof=1) / np.sqrt(len(r))),
            "sd_%": 100 * r.std(ddof=1), "Sharpe_ann": sh,
            "tot_x_margin": eq[-1],
            "maxDD_x_margin": dd.min(), "skew": pd.Series(r).skew(),
            "kurt": pd.Series(r).kurt(), "worst_%": 100 * r.min(),
            "n_lt_-50%": int((r < -0.50).sum()), "n_lt_-100%": int((r < -1.0).sum())}


pd.set_option("display.width", 240)


def main():
    T = pd.read_parquet(paths.require_data("opt_eod", f"{SYM}_hedged_{DTE}.parquet"))

    und = pd.read_parquet(paths.require_data(UND))
    und["date"] = pd.to_datetime(und["date"])
    und = und.sort_values("date").set_index("date")
    und["ret"] = np.log(und["close"]).diff()
    und["rv20"] = und["ret"].rolling(20).std() * np.sqrt(252)

    T = T.sort_values("entry").reset_index(drop=True)
    # realistic entry: sell the straddle at the BID rather than the mid.
    # held to expiry there is no exit crossing, so the drag is ONE half-spread x 2 legs.
    T["entry_drag_pct_prem"] = (T["prem_mid"] - T["prem_bid"]) / T["prem_mid"]
    T["short_dh_bid"] = -T["dh_pct_prem"] - T["entry_drag_pct_prem"]
    T["long_dh_ask"] = T["dh_pct_prem"] - (T["prem_ask"] - T["prem_mid"]) / T["prem_mid"]

    # margin proxies
    T["margin_naked"] = 0.20 * T["S0"] * 100          # Reg-T-ish naked short straddle
    T["pnl_short_naked_$"] = (T["prem_bid"] - T["payoff"]) * 100
    T["pnl_short_dh_$"] = (-T["dh_gain_$"] - (T["prem_mid"] - T["prem_bid"])) * 100
    T["r_naked_margin"] = T["pnl_short_naked_$"] / T["margin_naked"]
    T["r_dh_margin"] = T["pnl_short_dh_$"] / T["margin_naked"]

    print(f"===== {SYM} monthly short-vol sleeve, entry ~{DTE} DTE, REAL EOD NBBO, "
          f"{T['entry'].min().date()} -> {T['entry'].max().date()} =====")
    print("Returns below are on a 20%-of-notional margin base (1 straddle per unit), "
          "i.e. FULLY collateralised at Reg-T naked margin, no leverage.\n")

    rows = [
        prog(T["r_naked_margin"], "SHORT NAKED straddle, sold at bid, held to expiry"),
        prog(T["r_dh_margin"], "SHORT DELTA-HEDGED straddle, sold at bid, daily rehedge"),
    ]
    # buy & hold underlying, monthly, same dates
    bh = []
    for d0, d1 in zip(T["entry"], T["exp"]):
        s = und[(und.index >= d0) & (und.index <= d1)]["close"]
        bh.append(s.iloc[-1] / s.iloc[0] - 1 if len(s) > 1 else np.nan)
    T["bh"] = bh
    rows.append(prog(T["bh"].dropna(), f"{SYM} buy & hold, same monthly windows"))
    print(pd.DataFrame(rows).round(2).to_string(index=False))

    print("\n--- cost accounting, as % of the straddle mid premium ---")
    print(f"one-way entry drag (sell at bid vs mid, both legs): "
          f"mean {100*T['entry_drag_pct_prem'].mean():.2f}%  median {100*T['entry_drag_pct_prem'].median():.2f}%")
    print(f"full round trip (cross both legs both ways):        "
          f"mean {100*2*T['entry_drag_pct_prem'].mean():.2f}%  median {100*2*T['entry_drag_pct_prem'].median():.2f}%")
    print(f"daily stock delta-hedging @1bp:                     "
          f"mean {100*(T['hedgecost_$']/T['prem_mid']).mean():.2f}%")
    print(f"per-contract commission $0.65 x 2 legs on a ${T['prem_mid'].median():.2f} premium: "
          f"{100*1.30/(T['prem_mid'].median()*100):.2f}%")

    print("\n--- effect of the entry cost on the headline ---")
    for a, b in [("SHORT delta-hedged at MID", -T["dh_pct_prem"]),
                 ("SHORT delta-hedged at BID (real)", T["short_dh_bid"]),
                 ("LONG delta-hedged at MID", T["dh_pct_prem"]),
                 ("LONG delta-hedged at ASK (real)", T["long_dh_ask"])]:
        x = b.dropna()
        print(f"{a:38s} mean {100*x.mean():+6.2f}% of premium   t={x.mean()/(x.std(ddof=1)/np.sqrt(len(x))):+.2f}")

    # --- conditional: does entry IV vs trailing RV predict the short-vol outcome? ---
    T["rv20_entry"] = [und["rv20"].asof(d) for d in T["entry"]]
    T["vrp_signal"] = T["iv0"] - T["rv20_entry"]
    T["ivrank"] = T["iv0"].rolling(24, min_periods=12).rank(pct=True)
    print("\n--- conditional tests on the SHORT delta-hedged straddle (at bid) ---")
    for sig, name in [("vrp_signal", "entry IV minus trailing 20d realized vol"),
                      ("iv0", "absolute entry IV level"),
                      ("ivrank", "2-yr IV percentile rank")]:
        d = T.dropna(subset=[sig, "short_dh_bid"])
        q = pd.qcut(d[sig], 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"])
        g = d.groupby(q, observed=True)["short_dh_bid"].agg(
            n="size", mean=lambda x: 100 * x.mean(),
            t=lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))
        print(f"\n  signal = {name}")
        print(g.round(2).to_string())

    # long-vol timing: does LOW iv rank make the long straddle pay?
    print("\n--- LONG delta-hedged straddle (at ask) by IV rank quartile ---")
    d = T.dropna(subset=["ivrank", "long_dh_ask"])
    q = pd.qcut(d["ivrank"], 4, labels=["Q1 lowest IV", "Q2", "Q3", "Q4 highest IV"])
    print(d.groupby(q, observed=True)["long_dh_ask"].agg(
        n="size", mean=lambda x: 100 * x.mean(),
        t=lambda x: x.mean() / (x.std(ddof=1) / np.sqrt(len(x))),
        win=lambda x: 100 * (x > 0).mean()).round(2).to_string())


if __name__ == "__main__":
    main()
