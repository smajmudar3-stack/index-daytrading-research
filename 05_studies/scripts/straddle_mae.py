"""Part F: maximum ADVERSE EXCURSION of the short straddle during the life of
the trade. This is the number that actually determines whether a small account
survives: you are marked to market daily and margin-called on the worst mark,
not on the terminal outcome."""
import pandas as pd

from idt import paths

SYM = "SPY"

TARGET = 45
pd.set_option("display.width", 220)


def main():
    df = pd.read_parquet(paths.require_data("opt_eod", f"{SYM}_monthly_full.parquet"))
    df["mid"] = (df["bid"] + df["ask"]) / 2
    und = pd.read_parquet(paths.require_data("opt_eod", f"{SYM}_underlying.parquet"))
    und["date"] = pd.to_datetime(und["date"])
    spot = und.set_index("date")["close"]
    df["spot"] = df["date"].map(spot)
    df = df.dropna(subset=["spot"])
    df = df[df["ask"] > 0]
    # Named leg_paths, not paths: a local called `paths` shadows the idt.paths
    # module for the entire function, so the require_data() call at the top of
    # main() raised UnboundLocalError and the script could not run at all.
    leg_paths = {k: v for k, v in df.groupby(["expiration", "strike", "type"], observed=True)}

    rows = []
    for exp, g in df.groupby("expiration", observed=True):
        g2 = g[(g["dte"] - TARGET).abs() <= 5]
        if len(g2) == 0:
            continue
        d0 = g2.loc[(g2["dte"] - TARGET).abs().idxmin(), "date"]
        day = g[g["date"] == d0]
        s0 = day["spot"].iloc[0]
        cal = day[(day["type"] == "call") & (day["bid"] > 0)]
        if len(cal) == 0:
            continue
        k = cal.loc[(cal["strike"] - s0).abs().idxmin(), "strike"]
        try:
            pc = leg_paths[(exp, k, "call")].set_index("date")
            pp = leg_paths[(exp, k, "put")].set_index("date")
        except KeyError:
            continue
        idx = pc.index.intersection(pp.index)
        idx = idx[idx >= d0].sort_values()
        if len(idx) < 5:
            continue
        credit = (pc.loc[idx[0], "bid"] + pp.loc[idx[0], "bid"])
        # cost to close at any point = the ASK of both legs
        close_cost = (pc.loc[idx, "ask"] + pp.loc[idx, "ask"]).values
        mtm = (credit - close_cost) / credit          # % of credit, marked to market
        S_T = pc.loc[idx[-1], "spot"]
        payoff = max(S_T - k, 0) + max(k - S_T, 0)
        margin = 0.20 * s0 * 100
        rows.append({"entry": d0, "exp": exp, "credit": credit,
                     "terminal_%credit": 100 * (credit - payoff) / credit,
                     "MAE_%credit": 100 * mtm.min(),
                     "MAE_x_margin": 100 * (credit - close_cost.max()) * 100 / margin,
                     "terminal_x_margin": 100 * (credit - payoff) * 100 / margin})

    t = pd.DataFrame(rows)

    print("==== SPY ATM short straddle @45DTE: mark-to-market pain vs terminal outcome ====")
    print(f"n={len(t)}, {t['entry'].min().date()} -> {t['entry'].max().date()}\n")
    print("MAE_%credit = worst intra-trade mark, as % of credit collected (negative = loss)")
    print("terminal_%credit = the P&L you actually keep if you never get stopped or margin-called\n")
    print(t[["MAE_%credit", "terminal_%credit", "MAE_x_margin", "terminal_x_margin"]].describe(
        percentiles=[.05, .25, .5, .75, .95]).round(1).to_string())

    print("\n--- 10 worst intra-trade marks ---")
    print(t.nsmallest(10, "MAE_%credit")[["entry", "exp", "MAE_%credit", "terminal_%credit",
                                          "MAE_x_margin", "terminal_x_margin"]].round(1).to_string(index=False))

    print(f"\ntrades whose WORST MARK was below -100% of credit: {(t['MAE_%credit'] < -100).sum()} "
          f"({100*(t['MAE_%credit'] < -100).mean():.1f}%)")
    print(f"trades whose worst mark was below -300% of credit: {(t['MAE_%credit'] < -300).sum()}")
    print(f"trades that ENDED positive but were marked below -100% of credit at some point: "
          f"{((t['MAE_%credit'] < -100) & (t['terminal_%credit'] > 0)).sum()}")
    print(f"trades whose worst mark exceeded the posted 20%-notional margin: "
          f"{(t['MAE_x_margin'] < -100).sum()}")

    print("\n--- the Feb 2018 'Volmageddon' cycle, specifically ---")
    f18 = t[(t["exp"] >= "2018-01-25") & (t["exp"] <= "2018-03-01")]
    print(f18.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
