import pandas as pd
import numpy as np

from idt import paths

# "scratch" under DATA_ROOT. This was a /private/tmp scratchpad belonging to the
# session that wrote the file; it is long gone, so the script died on this line.
SP = "scratch"  # path under DATA_ROOT, resolved at the read site


def load(n):
    d = pd.read_csv(paths.require_data(SP, f"{n}.csv"))
    d.columns = ["date", n]
    d["date"] = pd.to_datetime(d["date"])
    return d.set_index("date")[n].astype(float).sort_index()


def main():
    px = pd.concat([load(n) for n in ["CNDR", "BFLY", "PUT", "WPUT", "SPX"]], axis=1)
    r = np.log(px).diff()
    rf = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3")
    rf.columns = ["date", "rate"]
    rf["date"] = pd.to_datetime(rf["date"])
    rf = pd.to_numeric(rf.set_index("date")["rate"], errors="coerce").ffill()
    rfd = rf.reindex(r.index).ffill() / 100 / 252

    print("--- rolling 5-year annualised EXCESS return over T-bills (%) ---")
    ex = r.sub(rfd, axis=0)
    roll = ex.rolling(1260).mean() * 252 * 100
    print(roll.resample("YE").last().dropna(how="all").round(2).to_string())

    print("\n--- beta to SPX and residual alpha, by era (daily, excess returns) ---")
    for lbl, a, b in [("1986-2009", "1986-01-01", "2009-12-31"), ("2010-2026", "2010-01-01", "2030-01-01")]:
        seg = ex.loc[a:b].dropna(subset=["SPX"])
        for c in ["CNDR", "BFLY", "PUT", "WPUT"]:
            s = seg[[c, "SPX"]].dropna()
            if len(s) < 200:
                continue
            beta = np.cov(s[c], s["SPX"])[0, 1] / np.var(s["SPX"])
            alpha = (s[c].mean() - beta * s["SPX"].mean()) * 252 * 100
            print(f"{lbl} {c:5s} n={len(s):5d} beta={beta:5.2f} alpha_ann={alpha:6.2f}%")

    print("\n--- PUT vs WPUT annualised excess, 5y rolling gap (WPUT - PUT), pp ---")
    gap = (roll["WPUT"] - roll["PUT"]).resample("YE").last().dropna()
    print(gap.round(2).to_string())


if __name__ == "__main__":
    main()
