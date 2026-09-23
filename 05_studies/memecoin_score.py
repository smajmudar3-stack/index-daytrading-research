"""memecoin_score.py — what buying every new launch at the price a retail bot first sees
actually returns. Scores `04_live_system/memecoin_recorder.py`.

Per horizon after first sight (5 min, 30 min, 1 h, 6 h, 24 h): the median return, the mean,
the share down more than 50% and more than 90% (rugs and fades), the share that doubled,
the share whose pair vanished (no price), and the equal-weight "buy them all" return. Sizing
is the honest part: a $3,000 pool moves ~15% against a $500 order, so the table also shows
the median first-seen liquidity and what fraction of launches could absorb $100 at under 5%
impact (constant-product: impact ≈ order / (liquidity/2)).

Survivorship is the whole story of this market -- 68.7% of pump.fun tokens trade for the
last time on the day they launch, under 2% graduate (arXiv 2607.02823, CoinGecko 2025) --
so every token first seen is scored, including the ones that go to nothing.
"""
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

HORIZONS = {"5m": 300, "30m": 1800, "1h": 3600, "6h": 21600, "24h": 86400}


def main():
    c = sqlite3.connect(paths.state("memecoins.db"))
    t = pd.read_sql("SELECT * FROM tokens", c)
    m = pd.read_sql("SELECT * FROM marks", c)
    c.close()
    print(f"{len(t)} launches recorded, {t.chain.value_counts().to_dict()}, first {pd.to_datetime(t.first_seen.min(), unit='s')} UTC")
    liq = t.first_liq.replace(0, np.nan)
    print(f"first-seen liquidity: median ${liq.median():,.0f}; {(liq >= 4000).mean()*100:.0f}% could absorb $100 at <5% impact; "
          f"{(liq >= 20000).mean()*100:.0f}% could absorb $500")
    rows = []
    for lab, secs in HORIZONS.items():
        rets, gone = [], 0
        for r in t.itertuples():
            mk = m[(m.chain == r.chain) & (m.address == r.address) & (m.ts >= r.first_seen + secs * 0.8)]
            if mk.empty:
                continue                                      # horizon not reached yet
            mk = mk.iloc[(mk.ts - (r.first_seen + secs)).abs().argmin()]
            if pd.isna(mk.price) or not r.first_price:
                gone += 1; rets.append(-1.0)                  # pair gone = position worth nothing
                continue
            rets.append(mk.price / r.first_price - 1)
        if len(rets) < 5:
            continue
        v = np.array(rets)
        rows.append({"horizon": lab, "n": len(v), "median": np.median(v), "mean": v.mean(),
                     "down>50%": (v < -0.5).mean(), "down>90%": (v < -0.9).mean(), "doubled": (v >= 1).mean(),
                     "pair gone": gone / len(v), "buy-all equal-weight": v.mean()})
    if rows:
        print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:8.3f}"))
    else:
        print("no horizon reached yet; let the recorder run")


if __name__ == "__main__":
    main()
