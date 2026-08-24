"""
(a) Is a CREDIT broken-wing butterfly actually obtainable on SPY, and what does
    its risk look like when it is?
(b) Box spread: implied financing rate at mid vs after crossing the spread,
    across maturities, with the entry cost annualised (a box held to expiry pays
    no exit spread, so entry half-spreads are the right cost).
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

OPT = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_options.parquet"
UND = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_underlying.parquet"
COLS = ["date", "expiration", "strike", "type", "bid", "ask", "open_interest"]


def main():
    und = pd.read_parquet(UND)[["date", "close"]]
    und["date"] = pd.to_datetime(und.date)
    und = und.set_index("date")["close"]

    alld = pd.to_datetime(pd.Series(sorted(
        pq.read_table(OPT, columns=["date"]).column("date").to_pandas().unique())))
    alld = alld[alld >= "2018-01-01"]
    sample = alld.groupby([alld.dt.year, alld.dt.month]).min().to_list()

    df = pq.read_table(OPT, columns=COLS, filters=[("date", "in", sample)]).to_pandas()
    df = df[(df.bid > 0) & (df.ask > df.bid) & (df.open_interest > 10)].copy()
    df["mid"] = (df.bid + df.ask) / 2
    df["spread"] = df.ask - df.bid
    df["dte"] = (df.expiration - df.date).dt.days

    bwb, box = [], []
    for dt, day in df.groupby("date"):
        S = und.get(dt, np.nan)
        if not np.isfinite(S):
            continue

        # ---------------- (a) credit BWB search, ~35 DTE ----------------
        sub = day[(day.dte >= 25) & (day.dte <= 45)]
        if not sub.empty:
            exp = sub.groupby("expiration").size().idxmax()
            puts = sub[(sub.expiration == exp) & (sub.type == "put")].sort_values("strike")
            if len(puts) > 30:
                H = puts.iloc[(puts.strike - S * 0.99).abs().argmin()]
                cands = puts[puts.strike < H.strike]
                best = None
                safest = None
                for _, M in cands.iterrows():
                    narrow = H.strike - M.strike
                    if narrow < 1 or narrow > S * 0.05:
                        continue
                    lows = cands[cands.strike < M.strike]
                    for _, L in lows.iterrows():
                        wide = M.strike - L.strike
                        if wide <= narrow:
                            continue
                        net = H.mid - 2 * M.mid + L.mid          # >0 = debit
                        net_nat = H.ask - 2 * M.bid + L.ask      # crossing
                        if net_nat >= 0:      # not a credit after crossing
                            continue
                        credit = -net_nat
                        maxloss = (wide - narrow) * 100 - credit * 100
                        maxprof = (narrow - net) * 100
                        rt = (H.spread + 2 * M.spread + L.spread) * 100
                        cand = dict(date=dt, S=S, H=H.strike, M=M.strike, L=L.strike,
                                    narrow=narrow, wide=wide,
                                    credit_mid=-net * 100, credit_nat=credit * 100,
                                    maxloss=maxloss, maxprof=maxprof, rt=rt,
                                    prob_proxy=(S - M.strike) / S)
                        # prefer the largest credit
                        if best is None or cand["credit_nat"] > best["credit_nat"]:
                            best = cand
                        # also track the SAFEST credit BWB (smallest max loss)
                        if safest is None or cand["maxloss"] < safest["maxloss"]:
                            safest = cand
                if best:
                    best["variant"] = "max_credit"
                    bwb.append(best)
                if safest:
                    safest = dict(safest, variant="min_risk")
                    bwb.append(safest)

        # ---------------- (b) boxes across maturities ----------------
        for lo, hi, tag in [(25, 45, "~35d"), (80, 110, "~90d"),
                            (170, 220, "~6m"), (330, 420, "~1y")]:
            s2 = day[(day.dte >= lo) & (day.dte <= hi)]
            if s2.empty:
                continue
            exp = s2.groupby("expiration").size().idxmax()
            ch = s2[s2.expiration == exp]
            c = ch[ch.type == "call"].set_index("strike")
            p = ch[ch.type == "put"].set_index("strike")
            common = sorted(set(c.index) & set(p.index))
            if len(common) < 6:
                continue
            arr = np.array(common)
            K1 = arr[np.abs(arr - S * 0.97).argmin()]
            K2 = arr[np.abs(arr - S * 1.03).argmin()]
            if K2 <= K1:
                continue
            W = K2 - K1
            c1, c2, p1, p2 = c.loc[K1], c.loc[K2], p.loc[K1], p.loc[K2]
            for x in (c1, c2, p1, p2):
                if isinstance(x, pd.DataFrame):
                    break
            else:
                mid = c1.mid - c2.mid + p2.mid - p1.mid
                nat = c1.ask - c2.bid + p2.ask - p1.bid      # what a long box costs
                halfspread = (c1.spread + c2.spread + p1.spread + p2.spread) / 2
                T = (exp - dt).days / 365.0
                box.append(dict(date=dt, tag=tag, T=T, W=W, mid=mid, nat=nat,
                                half=halfspread,
                                rate_mid=(W / mid) ** (1 / T) - 1 if mid > 0 else np.nan,
                                rate_nat=(W / nat) ** (1 / T) - 1 if nat > 0 else np.nan,
                                mid_over_W=mid / W))

    b = pd.DataFrame(bwb)
    pd.set_option("display.width", 220)
    print("=" * 120)
    print("CREDIT BROKEN-WING BUTTERFLY (put, ~35 DTE SPY) — best available credit after crossing the spread")
    print("=" * 120)
    if b.empty:
        print("no credit BWB obtainable after crossing the spread on any sample date")
    else:
        print(f"obtainable on {b.date.nunique()} of 96 sample dates")
        print(b.groupby("variant")[["narrow","wide","credit_mid","credit_nat","maxloss","maxprof","rt"]].median().round(1).to_string())
        b = b[b.variant=="max_credit"]
        print("\nmedian credit at mid  : $%.0f ; credit after crossing: $%.0f  (%.0f%% given up to the spread)"
              % (b.credit_mid.median(), b.credit_nat.median(),
                 100 * (1 - b.credit_nat.median() / b.credit_mid.median())))
        print("median MAX LOSS       : $%.0f   (downside, i.e. the side that was NOT eliminated)"
              % b.maxloss.median())
        print("median max profit     : $%.0f   (only at a pin on the short strike)" % b.maxprof.median())
        print("round-trip spread     : $%.0f = %.0f%% of the credit actually received"
              % (b.rt.median(), 100 * b.rt.median() / b.credit_nat.median()))
        print("loss:credit ratio     : %.1f : 1" % (b.maxloss.median() / b.credit_nat.median()))

    bx = pd.DataFrame(box)
    print("\n" + "=" * 120)
    print("BOX SPREAD financing — SPY (AMERICAN style), long box = lending")
    print("=" * 120)
    g = bx.groupby("tag").agg(n=("mid", "size"), T=("T", "median"),
                              width=("W", "median"),
                              mid_over_W=("mid_over_W", "median"),
                              rate_mid=("rate_mid", "median"),
                              rate_nat=("rate_nat", "median"),
                              half_usd=("half", lambda x: 100 * x.median()))
    g["entry_cost_%_of_notional"] = 100 * g.half_usd / (100 * g.width)
    g["cost_annualised_%"] = g["entry_cost_%_of_notional"] / g["T"]
    g["rate_mid"] *= 100
    g["rate_nat"] *= 100
    print(g.round(3).to_string())
    print("\nReference: the ENTIRE documented edge in box financing (Treasury convenience yield,")
    print("van Binsbergen-Diamond-Grotteria JFE 2022) is ~0.40%/yr, ~0.65%/yr under 3 months.")

    b.to_parquet("/Users/sahilmajmudar/index-daytrading/data/bwb_credit.parquet")
    bx.to_parquet("/Users/sahilmajmudar/index-daytrading/data/box_rates.parquet")


if __name__ == "__main__":
    main()
