"""condor_backtest.py — when does a 0DTE iron condor actually survive? (entry time × width × gamma regime)

A condor keeps full credit if the underlying stays inside the short strikes to the close. This measures
that survival exactly from 2y SPY minute data: enter at time T with short strikes at ±W% of the price
at T, held to 15:55 — did the rest-of-day high/low stay inside? Split by entry time (morning vs power
hour) and prior-close gamma regime. This tells the live signal WHEN a condor is favorable and HOW WIDE.
"""
import glob
import numpy as np
import pandas as pd

from idt import paths


ENTRIES = ["09:45", "10:30", "11:30", "13:00", "14:00", "14:30"]
WIDTHS = [0.004, 0.005, 0.006, 0.0075, 0.010]


def regime(z):
    return "HIGH gamma (pin)" if z > 0.5 else "LOW gamma (trend)" if z < -0.5 else "MID"


def main():
    G = pd.read_csv(paths.require_data("squeeze_dix_gex.csv"), parse_dates=["date"]).sort_values("date")
    G["gz"] = ((G.gex - G.gex.rolling(252, min_periods=60).mean()) / G.gex.rolling(252, min_periods=60).std()).shift(1)
    gz = G.set_index(G["date"].dt.date)["gz"]

    rows = []
    for f in sorted(glob.glob(paths.require_data("minute", "SPY") + "/*.parquet")):
        m = pd.read_parquet(f).between_time("09:30", "15:59")
        for day, g in m.groupby(m.index.date):
            z = gz.get(day, np.nan)
            if np.isnan(z) or len(g) < 200:
                continue
            for et in ENTRIES:
                try:
                    sub = g.between_time(et, "15:55")
                    if len(sub) < 5:
                        continue
                    p0 = sub["close"].iloc[0]
                    hi = sub["high"].max(); lo = sub["low"].min()
                except Exception:
                    continue
                for w in WIDTHS:
                    surv = (hi < p0 * (1 + w)) and (lo > p0 * (1 - w))
                    rows.append((day, z, et, w, int(surv)))

    D = pd.DataFrame(rows, columns=["day", "gz", "entry", "w", "surv"])
    print(f"{D.day.nunique()} days\n")

    D["reg"] = D.gz.apply(regime)

    print("CONDOR survival-to-close %  (rows=entry time, cols=width ±%), HIGH-gamma pin days only:")
    hi = D[D.reg == "HIGH gamma (pin)"]
    piv = hi.pivot_table(index="entry", values="surv", columns="w", aggfunc="mean") * 100
    piv.columns = [f"±{c*100:.2f}%" for c in piv.columns]
    print(piv.round(0).to_string())

    print("\nSurvival by regime (±0.75% width, the common condor):")
    for et in ["10:30", "13:00", "14:00"]:
        sub = D[(D.entry == et) & (D.w == 0.0075)]
        line = f"  entry {et}: "
        for r in ["HIGH gamma (pin)", "MID", "LOW gamma (trend)"]:
            s = sub[sub.reg == r]["surv"]
            line += f"{r.split()[0]} {s.mean()*100:.0f}%  "
        print(line)

    print("\nEV note: a condor with wing width Wg and credit C wins +C on survival, loses -(Wg-C) on breach.")
    print("Breakeven survival = (Wg-C)/Wg. Ex: collect 25% of the wing → need >75% survival to profit.")
    print("=> Favor: HIGH-gamma days + afternoon entry + width where survival clears your credit breakeven.")


if __name__ == "__main__":
    main()
