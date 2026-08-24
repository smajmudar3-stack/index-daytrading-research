"""Can SELECTION rescue far-OTM buying? The owner's actual thesis, tested.

The unconditional result is brutal: ultra-far-OTM SPY calls return -90% mean,
2-5 delta -48%, and the mean improves monotonically as you move CLOSER to the
money. So "buy the cheapest contracts" is exactly backwards on its own.

But that is not the owner's claim. His claim is that SELECTION fixes it — find
names about to make a big move that IV has not priced, and the tail pays.
That is a real, testable hypothesis and it deserves a real test rather than a
restatement of the unconditional number.

Conditions tested, all knowable at entry:
  IVRANK_LOW  — option IV in the bottom third of its own trailing year.
                "Cheap vol" — the owner's "without IV priced in".
  SQUEEZE     — realised vol compressed: 21d RV in the bottom quartile of its
                trailing year. Volatility clusters, so compression preceding
                expansion is the standard practitioner screen.
  IV_UNDER_RV — implied below trailing realised, i.e. the option market is
                asking LESS than recent actual movement. The purest form of
                "a move not priced in".
  BOTH        — IVRANK_LOW and SQUEEZE together.

For each, the comparison is against the SAME delta bucket unconditionally. A
condition only counts if it beats that baseline, not if it beats zero.
"""
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

warnings.filterwarnings("ignore")
OPT = paths.data("opt_eod", "SPY_options.parquet")
UND = paths.data("opt_eod", "SPY_underlying.parquet")

BUCKETS = [(0.02, 0.05, "2-5d"), (0.05, 0.10, "5-10d"), (0.10, 0.16, "10-16d")]


def main():
    und = pd.read_parquet(paths.require_data(UND))
    dc = [c for c in und.columns if "date" in c.lower()]
    uc = [c for c in und.columns if c.lower() in ("close", "adjclose")][0]
    und.index = pd.to_datetime(und[dc[0]]) if dc else und.index
    px = und[uc].sort_index()

    # Realised vol + its own percentile, past-only.
    r = px.pct_change(fill_method=None)
    rv = r.rolling(21).std() * np.sqrt(252) * 100
    rv_pct = rv.rolling(252, min_periods=126).apply(
        lambda w: (w[:-1] < w[-1]).mean(), raw=True)

    rows = []
    for y in range(2010, 2026):
        t = pq.read_table(paths.require_data(OPT), columns=["date", "expiration", "strike", "type",
                                                            "bid", "ask", "delta", "open_interest",
                                                            "implied_volatility"],
                                              filters=[("date", ">=", pd.Timestamp(f"{y}-01-01")),
                                                       ("date", "<=", pd.Timestamp(f"{y}-12-31"))]).to_pandas()
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t["date"])
        t["expiration"] = pd.to_datetime(t["expiration"])
        t["dte"] = (t["expiration"] - t["date"]).dt.days
        e = t[(t.dte.between(20, 60)) & (t.bid > 0.02) & (t.ask > t.bid)
              & (t.open_interest > 10) & (t.delta.abs().between(0.02, 0.16))
              & (t.implied_volatility.between(0.03, 3.0))]
        if e.empty:
            continue
        e = e.assign(ym=e.date.dt.to_period("M"))
        e = e.sort_values("date").groupby(
            ["ym", "expiration", "strike", "type"]).first().reset_index()

        for _, x in e.iterrows():
            hit = px[px.index >= x.expiration]
            if hit.empty:
                continue
            S = float(hit.iloc[0])
            intr = max(S - x.strike, 0.0) if x.type == "call" else max(x.strike - S, 0.0)
            cost = float(x.ask)
            if cost <= 0:
                continue
            rows.append({"date": x.date, "delta": abs(float(x.delta)),
                         "type": x.type, "ret": (intr - cost) / cost,
                         "iv": float(x.implied_volatility) * 100})
    d = pd.DataFrame(rows)

    # Attach the state variables as of entry.
    d["rv"] = d.date.map(rv)
    d["rv_pct"] = d.date.map(rv_pct)
    # IV rank of the option's own IV within its trailing year of same-bucket IVs.
    d = d.sort_values("date")
    d["iv_pct"] = (d.groupby(pd.cut(d.delta, [0.02, 0.05, 0.10, 0.16]))["iv"]
                     .transform(lambda s: s.rolling(2000, min_periods=400)
                                .apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)))
    d["iv_under_rv"] = d.iv < d.rv
    d = d.dropna(subset=["rv_pct", "iv_pct"])
    d.to_parquet(paths.data("blackswan_select.parquet"), index=False)

    conds = {
        "IVRANK_LOW": d.iv_pct < 0.33,
        "SQUEEZE": d.rv_pct < 0.25,
        "IV_UNDER_RV": d.iv_under_rv,
        "BOTH": (d.iv_pct < 0.33) & (d.rv_pct < 0.25),
    }

    print("=" * 100)
    print("DOES SELECTION RESCUE FAR-OTM BUYING?  (real SPY quotes, bought at ask,")
    print("held to expiry, worthless = -100%.  Baseline = same bucket, no condition)")
    print("=" * 100)
    print(f"  {'bucket':7s} {'kind':5s} {'condition':13s} {'n':>7s} {'win%':>6s} "
          f"{'MEAN':>9s} {'baseline':>9s} {'EDGE':>9s}")
    for kind in ("call", "put"):
        for lo, hi, lab in BUCKETS:
            base_m = d[(d.delta >= lo) & (d.delta < hi) & (d.type == kind)]
            if len(base_m) < 300:
                continue
            b = base_m.ret.mean()
            print(f"  {lab:7s} {kind:5s} {'(none)':13s} {len(base_m):7,d} "
                  f"{(base_m.ret>0).mean()*100:5.1f}% {b*100:+8.1f}% "
                  f"{'—':>9s} {'—':>9s}")
            for cname, cm in conds.items():
                s = base_m[cm.reindex(base_m.index).fillna(False)]
                if len(s) < 120:
                    continue
                m = s.ret.mean()
                print(f"  {'':7s} {'':5s} {cname:13s} {len(s):7,d} "
                      f"{(s.ret>0).mean()*100:5.1f}% {m*100:+8.1f}% {b*100:+8.1f}% "
                      f"{(m-b)*100:+8.1f}%")
            print()


if __name__ == "__main__":
    main()
