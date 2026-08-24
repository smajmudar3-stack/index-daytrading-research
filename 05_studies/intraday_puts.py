"""intraday_puts.py — which INTRADAY short/put triggers actually work, split by gamma regime.

Same-session put entries (not next-day). Tests three triggers on 2y SPY minute data, SHORT side only,
by prior-close gamma regime (short gamma = downside amplifies → shorts should work; long gamma/pin =
shorts fail). Enter once/day on the first trigger, hold to 15:55 or a reversal back through the level.

  A) BREAKDOWN: price breaks below the vol-band low AND below EMA100 (momentum down)
  B) LOW-BREAK: price breaks the session low after 10:30 (trend-day continuation down)
  C) VWAP-LOSS: price loses VWAP from above and stays below EMA100 (roll-over)
"""
import glob
import numpy as np
import pandas as pd
from scipy import stats

from idt import paths

COST = 0.0003

rowsA, rowsB, rowsC = [], [], []

def rpt(name, rows):
    D = pd.DataFrame(rows, columns=["gz", "neg", "pnl"])
    print(f"\n{name}: {len(D)} signals")
    for lab, mask in [("ALL", D.index >= 0), ("short/low gamma gz<-0.3", D.gz < -0.3),
                      ("NEG gamma (gex<0)", D.neg), ("high gamma gz>0.5 (should FAIL)", D.gz > 0.5)]:
        s = D[mask]["pnl"]
        if len(s) < 25:
            print(f"   {lab:<32} n={len(s)} too few"); continue
        t, p = stats.ttest_1samp(s, 0)
        print(f"   {lab:<32} n={len(s):>4}  avg {s.mean()*1e4:+6.1f}bps  win {(s>0).mean()*100:3.0f}%  t {t:+5.2f}")


def main():
    G = pd.read_csv(paths.require_data("squeeze_dix_gex.csv"), parse_dates=["date"]).sort_values("date")
    G["gz"] = ((G.gex - G.gex.rolling(252, min_periods=60).mean()) / G.gex.rolling(252, min_periods=60).std()).shift(1)
    G["neg"] = G["gex"].shift(1) < 0
    gz = G.set_index(G["date"].dt.date)[["gz", "neg"]]

    for f in sorted(glob.glob(paths.require_data("minute", "SPY") + "/*.parquet")):
        m = pd.read_parquet(f).between_time("09:30", "15:59")
        for day, g in m.groupby(m.index.date):
            if day not in gz.index or len(g) < 200:
                continue
            z = gz.loc[day, "gz"]; neg = bool(gz.loc[day, "neg"])
            if np.isnan(z):
                continue
            g = g.copy(); g["ema"] = g["close"].ewm(span=100, adjust=False).mean()
            o = g["close"].iloc[0]
            dev = (g["close"] - o) / o
            band = dev.abs().expanding().mean() * 1.0        # simple intraday vol band (proxy)
            px = g["close"].values; ema = g["ema"].values; vw = g["vwap"].values if "vwap" in g else px
            hi_run = np.maximum.accumulate(px); lo_run = np.minimum.accumulate(px)
            close = px[-1]
            def short_pnl(entry_i):
                return (px[entry_i] - close) / px[entry_i] - COST   # short: profit if close < entry
            # A) breakdown below vol-band + EMA
            for i in range(20, len(g) - 5):
                if dev.iloc[i] < -band.iloc[i] and px[i] < ema[i]:
                    rowsA.append((z, neg, short_pnl(i))); break
            # B) session-low break after 10:30 (min index ~60)
            for i in range(60, len(g) - 5):
                if px[i] <= lo_run[i - 1] and px[i] < ema[i]:
                    rowsB.append((z, neg, short_pnl(i))); break
            # C) VWAP loss from above + below EMA
            for i in range(20, len(g) - 5):
                if px[i - 1] >= vw[i - 1] and px[i] < vw[i] and px[i] < ema[i]:
                    rowsC.append((z, neg, short_pnl(i))); break

    rpt("A) BREAKDOWN (band+EMA)", rowsA)
    rpt("B) SESSION-LOW break", rowsB)
    rpt("C) VWAP-LOSS rollover", rowsC)
    print("\n=> a put trigger is real if short/neg-gamma rows are POSITIVE (t>2) and high-gamma is negative.")


if __name__ == "__main__":
    main()
