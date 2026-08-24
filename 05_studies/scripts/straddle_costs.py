"""Part A: REAL bid/ask spread census for straddles and strangles on SPY/QQQ.

Answers: what does crossing the spread on 2 legs cost, as a % of the premium?
All numbers come from real EOD NBBO quotes (no model anywhere).
"""
import sys
import numpy as np
import pandas as pd

from idt import paths

SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
SLICE = f"opt_eod/{SYM}_monthly_slice.parquet"  # path under DATA_ROOT, resolved at the read site
UND = f"opt_eod/{SYM}_underlying.parquet"



def pick(g, target):
    """row whose |delta| is closest to target"""
    i = (g["adelta"] - target).abs().idxmin()
    return g.loc[i]


def build(target_c, target_p, label):
    """for each (date, expiration) pick the call at target_c delta and put at target_p delta"""
    ck = calls.loc[calls.groupby(["date", "expiration"])["adelta"]
                   .transform(lambda s: (s - target_c).abs()) ==
                   calls.groupby(["date", "expiration"])["adelta"]
                   .transform(lambda s: (s - target_c).abs().min())]
    pk = puts.loc[puts.groupby(["date", "expiration"])["adelta"]
                  .transform(lambda s: (s - target_p).abs()) ==
                  puts.groupby(["date", "expiration"])["adelta"]
                  .transform(lambda s: (s - target_p).abs().min())]
    ck = ck.drop_duplicates(["date", "expiration"])
    pk = pk.drop_duplicates(["date", "expiration"])
    m = ck.merge(pk, on=["date", "expiration", "dte", "spot"], suffixes=("_c", "_p"))
    m["bid_t"] = m["bid_c"] + m["bid_p"]
    m["ask_t"] = m["ask_c"] + m["ask_p"]
    m["mid_t"] = m["mid_c"] + m["mid_p"]
    m["spr_pct"] = (m["ask_t"] - m["bid_t"]) / m["mid_t"] * 100
    m["half_pct"] = m["spr_pct"] / 2
    m["struct"] = label
    m["prem_pct_spot"] = m["mid_t"] / m["spot"] * 100
    return m


def dtebucket(d):
    if d <= 7:
        return "0-7"
    if d <= 20:
        return "8-20"
    if d <= 35:
        return "21-35"
    if d <= 50:
        return "36-50"
    return "51-75"



pd.set_option("display.width", 200)


def main():
    # these were module-level before the guard; the functions above
    # still read them, so they stay global — only the work moved.
    global calls
    global puts

    df = pd.read_parquet(paths.require_data(SLICE))
    df = df[(df["bid"] > 0) & (df["ask"] >= df["bid"])].copy()
    df["mid"] = (df["bid"] + df["ask"]) / 2

    und = pd.read_parquet(paths.require_data(UND))
    und["date"] = pd.to_datetime(und["date"])
    spot = und.set_index("date")["close"]
    df["spot"] = df["date"].map(spot)
    df = df.dropna(subset=["spot"])
    df["adelta"] = df["delta"].abs()

    calls = df[df["type"] == "call"]
    puts = df[df["type"] == "put"]

    structs = {
        "ATM straddle (50d)": build(0.50, 0.50, "ATM straddle (50d)"),
        "30-delta strangle": build(0.30, 0.30, "30-delta strangle"),
        "16-delta strangle": build(0.16, 0.16, "16-delta strangle"),
    }

    print(f"===== {SYM}: REAL NBBO SPREAD CENSUS (monthly expirations, EOD quotes) =====")
    print("spr_pct = (ask_total - bid_total)/mid_total, i.e. the FULL round-trip cost")
    print("of entering at the far touch and exiting at the far touch, as % of mid premium.")
    print("Half of it = one-way cost of crossing both legs.\n")

    for name, m in structs.items():
        m["bkt"] = m["dte"].apply(dtebucket)
        m["yr"] = m["date"].dt.year
        print(f"--- {name} --- n={len(m):,}")
        t = m.groupby("bkt").agg(n=("spr_pct", "size"),
                                 med_spr=("spr_pct", "median"),
                                 mean_spr=("spr_pct", "mean"),
                                 p90_spr=("spr_pct", lambda s: s.quantile(0.90)),
                                 med_prem_pct_spot=("prem_pct_spot", "median"),
                                 med_mid=("mid_t", "median")).round(2)
        print(t.to_string())
        print()

    # time series of spread for the 30-45 DTE ATM straddle
    print("===== TIME TREND: ATM straddle round-trip spread as % of premium, 21-50 DTE =====")
    m = structs["ATM straddle (50d)"]
    sub = m[(m["dte"] >= 21) & (m["dte"] <= 50)].copy()
    sub["yr"] = sub["date"].dt.year
    print(sub.groupby("yr").apply(lambda g: pd.Series({
        "n": len(g),
        "med_spr_pct": g["spr_pct"].median(),
        "med_dollar_spread": (g["ask_t"] - g["bid_t"]).median(),
        "med_mid_premium": g["mid_t"].median(),
        "med_spot": g["spot"].median()}), include_groups=False).round(3).to_string())

    print()
    print("===== SAME FOR 16-DELTA STRANGLE, 21-50 DTE =====")
    m2 = structs["16-delta strangle"]
    sub2 = m2[(m2["dte"] >= 21) & (m2["dte"] <= 50)].copy()
    sub2["yr"] = sub2["date"].dt.year
    print(sub2.groupby("yr").apply(lambda g: pd.Series({
        "n": len(g),
        "med_spr_pct": g["spr_pct"].median(),
        "med_dollar_spread": (g["ask_t"] - g["bid_t"]).median(),
        "med_mid_premium": g["mid_t"].median()}), include_groups=False).round(3).to_string())


if __name__ == "__main__":
    main()
