"""Measure the true hurdle for expressing a 90-minute directional view in a 0DTE option,
using real SPXW quotes only. Fixed strike (per FINDINGS.md lesson: mnes_rel follows a
DIFFERENT contract as spot moves, so it must be re-mapped each bar).

Buy 1 ATM 0DTE call at 11:00 at the ASK, sell at 12:30 at the BID. Report the return
distribution split by whether spot actually went up. That gives the break-even hit rate
for a long-option expression of a directional signal, with no pricing model anywhere.
"""
import numpy as np
import pandas as pd

cols = ["quote_date", "quote_time", "option_type", "mnes_rel", "mid", "bas",
        "active_underlying_price"]
d = pd.read_parquet("data/spxw/data_opt.parquet", columns=cols)
d["quote_time"] = d["quote_time"].astype(str)
d = d[d.quote_time.isin(["11:00:00", "12:30:00"])]
d["bid"] = d.mid - d.bas / 2.0
d["ask"] = d.mid + d.bas / 2.0

out = []
for (day, otype), g in d.groupby(["quote_date", "option_type"]):
    e = g[g.quote_time == "11:00:00"]
    x = g[g.quote_time == "12:30:00"]
    if e.empty or x.empty:
        continue
    s0 = e.active_underlying_price.iloc[0]
    s1 = x.active_underlying_price.iloc[0]
    # entry: closest bucket to ATM
    e = e.assign(dist=(e.mnes_rel - 1.0).abs()).sort_values("dist")
    row0 = e.iloc[0]
    K = row0.mnes_rel * s0                      # the actual strike we bought
    entry_ask = row0.ask * s0                   # premium in SPX points
    if entry_ask <= 0.5:
        continue
    # exit: same STRIKE -> required moneyness on the 12:30 grid
    need = K / s1
    x = x.assign(dist=(x.mnes_rel - need).abs()).sort_values("dist")
    if x.iloc[0].dist > 0.0015:                 # grid too coarse to represent this strike
        continue
    exit_bid = x.iloc[0].bid * s1
    out.append({"date": day, "type": otype, "ret": exit_bid / entry_ask - 1.0,
                "spot_ret": s1 / s0 - 1.0, "prem_pts": entry_ask,
                "spread_pct": row0.bas / row0.mid * 100})

r = pd.DataFrame(out)
print(f"n = {len(r)} option-days ({r.date.nunique()} sessions), 11:00 -> 12:30, real quotes\n")

for otype, lbl in [("C", "long ATM call"), ("P", "long ATM put")]:
    s = r[r.type == otype]
    right = s[(s.spot_ret > 0) if otype == "C" else (s.spot_ret < 0)]
    wrong = s[(s.spot_ret <= 0) if otype == "C" else (s.spot_ret >= 0)]
    print(f"{lbl}: n={len(s)}  median premium {s.prem_pts.median():.1f} pts, "
          f"quoted spread {s.spread_pct.median():.1f}% of mid")
    print(f"   unconditional        avg ret {s.ret.mean()*100:+7.2f}%  "
          f"median {s.ret.median()*100:+7.2f}%  win {np.mean(s.ret>0)*100:.1f}%")
    print(f"   direction RIGHT n={len(right):4d} avg ret {right.ret.mean()*100:+7.2f}%")
    print(f"   direction WRONG n={len(wrong):4d} avg ret {wrong.ret.mean()*100:+7.2f}%")
    w, l = right.ret.mean(), wrong.ret.mean()
    if w > 0 > l:
        print(f"   -> BREAK-EVEN DIRECTIONAL HIT RATE = {(-l)/(w-l)*100:.1f}%")
    print()

print("Compare: delta-1 (ES/MES) break-even for the same 90-min view is ~51.0-51.5%.")
